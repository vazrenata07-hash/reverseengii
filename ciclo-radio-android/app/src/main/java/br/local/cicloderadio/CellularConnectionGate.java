package br.local.cicloderadio;

import android.content.Context;
import android.net.ConnectivityManager;
import android.net.Network;
import android.net.NetworkCapabilities;
import android.net.NetworkRequest;
import android.os.Handler;
import android.os.Looper;
import android.system.Os;
import android.system.OsConstants;

import java.io.IOException;
import java.io.InputStream;
import java.net.InetAddress;
import java.net.URL;
import java.net.URLConnection;
import java.nio.charset.StandardCharsets;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;
import java.util.concurrent.RejectedExecutionException;
import java.util.concurrent.atomic.AtomicLong;

import javax.net.ssl.HttpsURLConnection;

/** Observes cellular connectivity and confirms a public IP over that exact network. */
public final class CellularConnectionGate {
    private static final long RETRY_MS = 2_000L;
    private static final String WAITING = "Aguardando internet móvel...";
    private final ConnectivityManager connectivity;
    private final Handler handler;
    private final Runnable onChanged;
    private final AtomicLong epoch = new AtomicLong();
    private final ExecutorService executor = Executors.newSingleThreadExecutor(runnable -> {
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
    private long probeEpoch;
    private Future<?> probe;

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
        } else if (snapshot == null && probeNetwork == null) {
            scheduleCheck(lost ? RETRY_MS : 0L);
        }
    }

    private void restartAfterNetworkChange() {
        if (!active || closed) return;
        epoch.incrementAndGet();
        snapshot = null;
        discardProbe();
        setStatus(WAITING);
        changed();
        scheduleCheck(RETRY_MS);
    }

    private NetworkCapabilities capabilities(Network network) {
        if (network == null || connectivity == null) return null;
        try { return connectivity.getNetworkCapabilities(network); }
        catch (RuntimeException ignored) { return null; }
    }

    private static boolean eligible(NetworkCapabilities caps) {
        return caps != null && caps.hasTransport(NetworkCapabilities.TRANSPORT_CELLULAR)
                && caps.hasCapability(NetworkCapabilities.NET_CAPABILITY_INTERNET)
                && caps.hasCapability(NetworkCapabilities.NET_CAPABILITY_VALIDATED)
                && caps.hasCapability(NetworkCapabilities.NET_CAPABILITY_NOT_VPN);
    }

    private void checkConnection() {
        if (!active || closed || probeNetwork != null) return;
        if (isReady()) return;
        Network candidate = null;
        if (connectivity != null) {
            try {
                for (Network network : connectivity.getAllNetworks()) {
                    if (eligible(capabilities(network))) { candidate = network; break; }
                }
            } catch (RuntimeException ignored) { }
        }
        if (candidate == null) {
            setStatus(WAITING);
            scheduleCheck(RETRY_MS);
            return;
        }
        final Network selected = candidate;
        final long generation = epoch.get();
        probeNetwork = selected;
        probeEpoch = generation;
        setStatus("Confirmando IP público...");
        try {
            probe = executor.submit(() -> {
                String confirmed = "";
                try { confirmed = probePublicIp(selected); }
                catch (IOException | RuntimeException ignored) { }
                final String result = confirmed;
                handler.post(() -> acceptProbe(generation, selected, result));
            });
        } catch (RejectedExecutionException ignored) {
            probeNetwork = null;
            probe = null;
            if (!closed) scheduleCheck(RETRY_MS);
        }
    }

    private void acceptProbe(long generation, Network network, String ip) {
        if (!current(generation) || probeEpoch != generation
                || !network.equals(probeNetwork)) return;
        probe = null;
        probeNetwork = null;
        if (!eligible(capabilities(network))) {
            restartAfterNetworkChange();
            return;
        }
        if (ip.length() == 0) {
            setStatus("Aguardando confirmação do IP público...");
            scheduleCheck(RETRY_MS);
            return;
        }
        snapshot = new Snapshot(generation, network, ip);
        setStatus("Internet móvel conectada. IP confirmado.");
        changed();
    }

    private void scheduleCheck(long delay) {
        handler.removeCallbacks(check);
        if (active && !closed) handler.postDelayed(check, delay);
    }

    private void discardProbe() {
        handler.removeCallbacks(check);
        if (probe != null) probe.cancel(true);
        probe = null;
        probeNetwork = null;
        probeEpoch = 0L;
    }

    private void setStatus(String value) {
        if (!value.equals(status)) { status = value; changed(); }
    }

    private void changed() {
        if (closed || notificationQueued) return;
        notificationQueued = true;
        handler.post(notification);
    }

    private static String probePublicIp(Network network) throws IOException {
        // Binding to this Network prevents a Wi-Fi/default-network IP from being accepted.
        URLConnection opened = network.openConnection(new URL("https://api64.ipify.org"));
        if (!(opened instanceof HttpsURLConnection)) throw new IOException();
        HttpsURLConnection connection = (HttpsURLConnection) opened;
        try {
            connection.setConnectTimeout(3_000);
            connection.setReadTimeout(3_000);
            connection.setInstanceFollowRedirects(false);
            connection.setUseCaches(false);
            connection.setRequestMethod("GET");
            connection.setRequestProperty("Accept", "text/plain");
            if (connection.getResponseCode() != 200) throw new IOException();
            byte[] bytes = new byte[129];
            int size = 0;
            try (InputStream input = connection.getInputStream()) {
                while (size < bytes.length) {
                    int count = input.read(bytes, size, bytes.length - size);
                    if (count < 0) break;
                    size += count;
                }
            }
            if (size == 0 || size > 128) throw new IOException();
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
