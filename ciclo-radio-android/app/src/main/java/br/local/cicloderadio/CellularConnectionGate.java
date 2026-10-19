package br.local.cicloderadio;

import android.content.Context;
import android.net.ConnectivityManager;
import android.net.Network;
import android.net.NetworkCapabilities;
import android.net.NetworkRequest;
import android.os.Handler;
import android.os.Looper;
import android.os.SystemClock;
import android.system.Os;
import android.system.OsConstants;

import java.io.IOException;
import java.io.InputStream;
import java.net.InetAddress;
import java.net.URL;
import java.net.URLConnection;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.SynchronousQueue;
import java.util.concurrent.ThreadPoolExecutor;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.Future;
import java.util.concurrent.RejectedExecutionException;
import java.util.concurrent.atomic.AtomicLong;

import javax.net.ssl.HttpsURLConnection;

/** Observes cellular connectivity and confirms a public IP over that exact network. */
public final class CellularConnectionGate {
    private static final long RETRY_MS = 1_000L;
    private static final int MAX_IN_FLIGHT = 2;
    private static final String WAITING = "Aguardando internet móvel...";
    private final ConnectivityManager connectivity;
    private final Handler handler;
    private final Runnable onChanged;
    private final AtomicLong epoch = new AtomicLong();
    // No task queue: slow DNS/HTTPS cannot accumulate a backlog. The third worker
    // leaves room for a new cycle while two canceled checks finish their I/O.
    private final ExecutorService executor = new ThreadPoolExecutor(
            0, 3, 30L, TimeUnit.SECONDS, new SynchronousQueue<>(), runnable -> {
        Thread thread = new Thread(runnable, "cellular-ip-check");
        thread.setDaemon(true);
        return thread;
    });

    // Public observations are volatile; mutable scheduling state belongs to handler.
    private volatile boolean active;
    private volatile boolean closed;
    private volatile Snapshot snapshot;
    private volatile String status = "Aguardando verificação de conexão.";
    private boolean registered;
    private boolean notificationQueued;
    private Network probeNetwork;
    private final ArrayList<Probe> probes = new ArrayList<>();
    private long nextAttemptAt;
    private int probeSequence;

    private static final class Probe {
        final long epoch;
        final Network network;
        final String endpoint;
        volatile boolean canceled;
        Future<?> future;
        Probe(long epoch, Network network, String endpoint) {
            this.epoch = epoch;
            this.network = network;
            this.endpoint = endpoint;
        }
        boolean interrupted() { return canceled || Thread.currentThread().isInterrupted(); }
    }

    private static final class Snapshot {
        final long epoch;
        final Network network;
        final String ip;
        Snapshot(long epoch, Network network, String ip) {
            this.epoch = epoch;
            this.network = network;
            this.ip = ip;
        }
    }

    private final Runnable check = new Runnable() {
        @Override public void run() { checkConnection(); }
    };
    private final Runnable notification = new Runnable() {
        @Override public void run() {
            notificationQueued = false;
            if (!closed && onChanged != null) onChanged.run();
        }
    };
    private final ConnectivityManager.NetworkCallback callback =
            new ConnectivityManager.NetworkCallback() {
        @Override public void onAvailable(Network network) {
            networkChanged(network, capabilities(network), false);
        }
        @Override public void onCapabilitiesChanged(Network network, NetworkCapabilities caps) {
            networkChanged(network, caps, false);
        }
        @Override public void onLost(Network network) {
            networkChanged(network, null, true);
        }
    };

    public CellularConnectionGate(Context context, Handler handler, Runnable onChanged) {
        if (context == null || handler == null) throw new IllegalArgumentException();
        Context application = context.getApplicationContext();
        connectivity = (ConnectivityManager) (application != null ? application : context)
                .getSystemService(Context.CONNECTIVITY_SERVICE);
        this.handler = handler;
        this.onChanged = onChanged;
    }

    /** Registers observation only: never requests or keeps a cellular network alive. */
    public void start() {
        dispatch(() -> {
            if (closed) return;
            registerObserver();
            if (active) scheduleCheck(0L);
        });
    }

    /** A new radio cycle must obtain its own IP confirmation, including on the same IP. */
    public void begin() {
        if (closed) return;
        final long generation = epoch.incrementAndGet();
        active = true;
        snapshot = null;
        status = WAITING;
        dispatch(() -> {
            if (!current(generation)) return;
            discardProbe();
            registerObserver();
            changed();
            scheduleCheck(0L);
        });
    }

    public void cancel() {
        final long generation = epoch.incrementAndGet();
        active = false;
        snapshot = null;
        status = "Verificação de conexão parada.";
        dispatch(() -> {
            if (generation != epoch.get()) return;
            discardProbe();
            changed();
        });
    }

    public boolean isReady() {
        final Snapshot found = snapshot;
        if (closed || !active || found == null || found.epoch != epoch.get()) return false;
        if (eligible(capabilities(found.network))) {
            // Recheck the epoch after the capability query, which may overlap cancel/begin.
            return !closed && active && snapshot == found && found.epoch == epoch.get();
        }
        dispatch(() -> {
            if (snapshot == found && current(found.epoch)) restartAfterNetworkChange();
        });
        return false;
    }

    public String getPublicIp() {
        Snapshot found = snapshot;
        return found != null && isReady() && snapshot == found ? found.ip : "";
    }

    public String getStatus() { return status; }

    public void close() {
        if (closed) return;
        closed = true;
        active = false;
        epoch.incrementAndGet();
        snapshot = null;
        status = "Verificação de conexão encerrada.";
        // Interrupts queued work immediately; any running HTTPS operation also has timeouts.
        executor.shutdownNow();
        dispatch(() -> {
            discardProbe();
            handler.removeCallbacks(notification);
            notificationQueued = false;
            if (registered && connectivity != null) {
                try { connectivity.unregisterNetworkCallback(callback); }
                catch (RuntimeException ignored) { }
                registered = false;
            }
        });
    }

    private void dispatch(Runnable task) {
        if (Looper.myLooper() == handler.getLooper()) task.run();
        else handler.post(task);
    }

    private boolean current(long generation) {
        return !closed && active && generation == epoch.get();
    }

    private void registerObserver() {
        if (registered || connectivity == null || closed) return;
        NetworkRequest request = new NetworkRequest.Builder()
                .addTransportType(NetworkCapabilities.TRANSPORT_CELLULAR)
                .addCapability(NetworkCapabilities.NET_CAPABILITY_INTERNET)
                .addCapability(NetworkCapabilities.NET_CAPABILITY_NOT_VPN)
                .build();
        try {
            connectivity.registerNetworkCallback(request, callback, handler);
            registered = true;
        } catch (RuntimeException ignored) {
            // Polling still checks the capabilities; no unobserved result is accepted.
        }
    }

    private void networkChanged(Network network, NetworkCapabilities caps, boolean lost) {
        if (closed || !active) return;
        Snapshot found = snapshot;
        boolean selected = network.equals(probeNetwork)
                || (found != null && network.equals(found.network));
        if (selected && (lost || !eligible(caps))) {
            restartAfterNetworkChange();
        } else if (snapshot == null && !lost) {
            // Capability callbacks need not wait for the next polling tick.
            scheduleCheck(0L);
        }
    }

    private void restartAfterNetworkChange() {
        if (!active || closed) return;
        epoch.incrementAndGet();
        snapshot = null;
        discardProbe();
        setStatus(WAITING);
        changed();
        scheduleCheck(0L);
    }

    private NetworkCapabilities capabilities(Network network) {
        if (network == null || connectivity == null) return null;
        try { return connectivity.getNetworkCapabilities(network); }
        catch (RuntimeException ignored) { return null; }
    }

    private static boolean eligible(NetworkCapabilities caps) {
        return caps != null && caps.hasTransport(NetworkCapabilities.TRANSPORT_CELLULAR)
                && caps.hasCapability(NetworkCapabilities.NET_CAPABILITY_INTERNET)
                && caps.hasCapability(NetworkCapabilities.NET_CAPABILITY_NOT_VPN);
    }

    private void checkConnection() {
        if (!active || closed || isReady()) return;
        if (probeNetwork != null && !eligible(capabilities(probeNetwork))) {
            restartAfterNetworkChange();
            return;
        }
        if (probeNetwork == null && connectivity != null) {
            try {
                for (Network network : connectivity.getAllNetworks()) {
                    if (eligible(capabilities(network))) { probeNetwork = network; break; }
                }
            } catch (RuntimeException ignored) { }
        }
        if (probeNetwork == null) {
            setStatus(WAITING);
            scheduleCheck(RETRY_MS);
            return;
        }
        final long now = SystemClock.elapsedRealtime();
        if (now < nextAttemptAt) {
            scheduleCheck(nextAttemptAt - now);
            return;
        }
        // Cadence is measured from the start, not from the previous response/timeout.
        nextAttemptAt = now + RETRY_MS;
        scheduleCheck(RETRY_MS);
        if (probes.size() >= MAX_IN_FLIGHT) return;
        final Probe attempt = new Probe(epoch.get(), probeNetwork,
                (probeSequence++ & 1) == 0
                        ? "https://api.ipify.org" : "https://api64.ipify.org");
        probes.add(attempt);
        setStatus("Confirmando IP público...");
        try {
            attempt.future = executor.submit(() -> {
                String confirmed = "";
                try {
                    if (!attempt.interrupted()) confirmed = probePublicIp(attempt);
                } catch (IOException | RuntimeException ignored) { }
                final String result = confirmed;
                handler.post(() -> acceptProbe(attempt, result));
            });
        } catch (RejectedExecutionException ignored) {
            // All workers can briefly be occupied by old network I/O. Never queue it.
            probes.remove(attempt);
        }
    }

    private void acceptProbe(Probe attempt, String ip) {
        probes.remove(attempt);
        if (!current(attempt.epoch) || attempt.canceled || snapshot != null
                || !attempt.network.equals(probeNetwork)) return;
        if (!eligible(capabilities(attempt.network))) {
            restartAfterNetworkChange();
            return;
        }
        if (ip.length() == 0) {
            setStatus("Aguardando confirmação do IP público...");
            return; // The independent one-second cadence is already scheduled.
        }
        snapshot = new Snapshot(attempt.epoch, attempt.network, ip);
        handler.removeCallbacks(check);
        cancelInFlight();
        setStatus("Internet móvel conectada. IP confirmado.");
        changed();
    }

    private void scheduleCheck(long delay) {
        handler.removeCallbacks(check);
        if (active && !closed) handler.postDelayed(check, delay);
    }

    private void discardProbe() {
        handler.removeCallbacks(check);
        cancelInFlight();
        probeNetwork = null;
        nextAttemptAt = 0L;
        probeSequence = 0;
    }

    private void cancelInFlight() {
        for (Probe attempt : probes) {
            attempt.canceled = true;
            if (attempt.future != null) attempt.future.cancel(true);
        }
        probes.clear();
    }

    private void setStatus(String value) {
        if (!value.equals(status)) { status = value; changed(); }
    }

    private void changed() {
        if (closed || notificationQueued) return;
        notificationQueued = true;
        handler.post(notification);
    }

    private static String probePublicIp(Probe attempt) throws IOException {
        // A successful HTTPS response proves Internet access without Android validation.
        // Binding to this Network excludes Wi-Fi/default-network IPs.
        if (attempt.interrupted()) throw new IOException();
        URLConnection opened = attempt.network.openConnection(new URL(attempt.endpoint));
        if (!(opened instanceof HttpsURLConnection)) throw new IOException();
        HttpsURLConnection connection = (HttpsURLConnection) opened;
        try {
            if (attempt.interrupted()) throw new IOException();
            connection.setConnectTimeout(1_000);
            connection.setReadTimeout(1_000);
            connection.setInstanceFollowRedirects(false);
            connection.setUseCaches(false);
            connection.setRequestMethod("GET");
            connection.setRequestProperty("Accept", "text/plain");
            if (connection.getResponseCode() != 200) throw new IOException();
            byte[] bytes = new byte[129];
            int size = 0;
            try (InputStream input = connection.getInputStream()) {
                while (size < bytes.length) {
                    if (attempt.interrupted()) throw new IOException();
                    int count = input.read(bytes, size, bytes.length - size);
                    if (count < 0) break;
                    size += count;
                }
            }
            if (attempt.interrupted() || size == 0 || size > 128) throw new IOException();
            String ip = new String(bytes, 0, size, StandardCharsets.US_ASCII).trim();
            if (!publicLiteral(ip)) throw new IOException();
            return ip;
        } finally {
            connection.disconnect();
        }
    }

    private static boolean publicLiteral(String value) {
        if (value.length() == 0 || value.length() > 45 || !value.matches("[0-9A-Fa-f:.]+"))
            return false;
        // inet_pton parses numeric literals only; it never resolves a supplied hostname.
        InetAddress address = Os.inet_pton(OsConstants.AF_INET, value);
        if (address == null) address = Os.inet_pton(OsConstants.AF_INET6, value);
        if (address == null) return false;
        byte[] bytes = address.getAddress();
        if (bytes.length == 4) {
            int a = bytes[0] & 255, b = bytes[1] & 255, c = bytes[2] & 255;
            return !(a == 0 || a == 10 || a == 127 || a >= 224
                    || (a == 100 && b >= 64 && b <= 127)
                    || (a == 169 && b == 254)
                    || (a == 172 && b >= 16 && b <= 31)
                    || (a == 192 && (b == 168 || (b == 0 && (c == 0 || c == 2))
                            || (b == 88 && c == 99)))
                    || (a == 198 && (b == 18 || b == 19 || (b == 51 && c == 100)))
                    || (a == 203 && b == 0 && c == 113));
        }
        if (bytes.length != 16 || (bytes[0] & 0xe0) != 0x20) return false;
        int a = bytes[0] & 255, b = bytes[1] & 255, c = bytes[2] & 255, d = bytes[3] & 255;
        if (a == 0x20 && b == 0x01) {
            if (c == 0x0d && d == 0xb8) return false; // Documentation.
            if (c == 0 && (d == 0x02 || (d & 0xf0) == 0x10
                    || (d & 0xf0) == 0x20)) return false; // Benchmark/ORCHID.
        }
        return !(a == 0x3f && b == 0xff && (c & 0xf0) == 0); // Documentation.
    }
}
