package br.local.cicloderadio;

import android.Manifest;
import android.accessibilityservice.AccessibilityService;
import android.accessibilityservice.AccessibilityServiceInfo;
import android.app.KeyguardManager;
import android.content.Intent;
import android.content.SharedPreferences;
import android.content.pm.PackageManager;
import android.graphics.Rect;
import android.os.Handler;
import android.os.Looper;
import android.os.PowerManager;
import android.os.SystemClock;
import android.provider.Settings;
import android.telecom.TelecomManager;
import android.util.Log;
import android.view.accessibility.AccessibilityEvent;
import android.view.accessibility.AccessibilityNodeInfo;

import java.util.ArrayList;
import java.util.List;

/**
 * Operates only the visible radio-power switch, never hidden telephony APIs.
 * pending_restore is deliberately durable: stopping the timer must not abandon
 * a radio that this service might have switched off. Force-stop is not recoverable
 * until Android allows this service to run again.
 */
public final class RadioAccessibilityService extends AccessibilityService
        implements SharedPreferences.OnSharedPreferenceChangeListener {
    private static final String TAG = "RadioCycle";
    private static final String PREFS = "radio_cycle";
    private static final String[] PACKAGES = {"com.android.phone", "com.android.settings"};
    private static final String[] IDS = {"radio_power", "mobile_radio_power"};
    private static final long STAGE_TIMEOUT = 15_000L;
    private static final long OPEN_RETRY = 30_000L;
    private static final int IDLE = 0;
    private static final int WAIT_OFF = 1;
    private static final int PAUSE_OFF = 2;
    private static final int RESTORE = 3;
    private static final int WAIT_ON = 4;
    private static final int MANUAL_RESTORE = 5;

    private final Handler handler = new Handler(Looper.getMainLooper());
    private SharedPreferences prefs;
    private boolean connected;
    private boolean tickQueued;
    private long tickAt;
    private int stage = IDLE;
    private long deadline;
    private long offIssuedAt;
    private long screenBlockedAt;
    private long lastOpenAttempt = -OPEN_RETRY;
    private long targetSearchDeadline;
    private long recoverySearchDeadline;
    private long observedOnAt;
    private boolean openedSettings;
    private boolean exitRestoreAttempted;
    private String finishReason = "";
    private final Runnable tick = new Runnable() {
        @Override public void run() {
            tickQueued = false;
            if (!connected) return;
            try {
                step();
            } catch (RuntimeException e) {
                // No node text, phone identifiers, or other screen content in logs.
                Log.w(TAG, "Radio automation interrupted: " + e.getClass().getSimpleName());
                if (prefs.getBoolean("pending_restore", false)) {
                    stopForRecovery("Falha na automação. Religamento pendente.");
                } else {
                    prefs.edit().putBoolean("enabled", false)
                            .putBoolean("request_now", false).apply();
                    setStatus("Falha na automação. Rotina parada.");
                }
            }
            queueTick(1_000L);
        }
    };

    @Override public void onCreate() {
        super.onCreate();
        prefs = getSharedPreferences(PREFS, MODE_PRIVATE);
        prefs.registerOnSharedPreferenceChangeListener(this);
    }

    @Override protected void onServiceConnected() {
        super.onServiceConnected();
        AccessibilityServiceInfo info = getServiceInfo();
        if (info == null) info = new AccessibilityServiceInfo();
        info.flags |= AccessibilityServiceInfo.FLAG_REPORT_VIEW_IDS;
        info.eventTypes = AccessibilityEvent.TYPE_WINDOW_STATE_CHANGED
                | AccessibilityEvent.TYPE_WINDOW_CONTENT_CHANGED
                | AccessibilityEvent.TYPE_VIEW_CLICKED
                | AccessibilityEvent.TYPE_VIEW_SCROLLED;
        info.feedbackType = AccessibilityServiceInfo.FEEDBACK_GENERIC;
        info.packageNames = PACKAGES.clone();
        info.notificationTimeout = 100L;
        setServiceInfo(info);
        connected = true;
        exitRestoreAttempted = false;
        stage = prefs.getBoolean("pending_restore", false) ? RESTORE : IDLE;
        if (stage == RESTORE) {
            finishReason = "Rádio religado após retomada do serviço.";
            setPhase("restore");
            setStatus("Religamento pendente. Mantenha a tela ligada e desbloqueada.");
        }
        queueTick(0L);
    }

    @Override public void onAccessibilityEvent(AccessibilityEvent event) {
        if (connected && (prefs.getBoolean("pending_restore", false)
                || prefs.getBoolean("enabled", false)
                || prefs.getBoolean("request_now", false))) queueTick(150L);
    }

    @Override public void onInterrupt() {
        // This callback interrupts accessibility feedback, not our timer.
        if (connected) queueTick(0L);
    }

    @Override public void onSharedPreferenceChanged(SharedPreferences p, String key) {
        if ("enabled".equals(key) || "request_now".equals(key)
                || "next_run".equals(key) || "interval_ms".equals(key)
                || "off_ms".equals(key) || "phase".equals(key)) queueTick(0L);
    }

    private void queueTick(long delay) {
        if (!connected) return;
        long when = SystemClock.elapsedRealtime() + delay;
        if (tickQueued && tickAt <= when) return;
        handler.removeCallbacks(tick);
        tickQueued = true;
        tickAt = when;
        handler.postDelayed(tick, delay);
    }

    private void step() {
        long now = SystemClock.elapsedRealtime();
        boolean pending = prefs.getBoolean("pending_restore", false);
        boolean enabled = prefs.getBoolean("enabled", false);
        boolean requested = prefs.getBoolean("request_now", false);

        if (pending) {
            if (stage == IDLE) stage = RESTORE;
            if ("stop_requested".equals(prefs.getString("phase", "idle"))) {
                finishReason = "Rádio ligado. Rotina parada.";
                if (stage != WAIT_ON && stage != MANUAL_RESTORE) stage = RESTORE;
                setPhase(stage == WAIT_ON ? "wait_on"
                        : (stage == MANUAL_RESTORE ? "manual_restore" : "restore"));
            }
            if (!screenReady()) {
                if (screenBlockedAt == 0L) screenBlockedAt = now;
                setStatus("Religamento pendente: ligue e desbloqueie a tela.");
                return;
            }
            if (screenBlockedAt != 0L) {
                // UI cannot be observed while locked. Do not expire a confirmation
                // deadline solely because the screen was unavailable.
                if (stage == WAIT_OFF || stage == WAIT_ON) deadline += now - screenBlockedAt;
                screenBlockedAt = 0L;
            }
            recoveryStep(now);
            return;
        }

        stage = IDLE;
        screenBlockedAt = 0L;
        if ("stop_requested".equals(prefs.getString("phase", "idle"))) {
            setPhase("idle");
            targetSearchDeadline = 0L;
            setStatus("Rotina parada.");
            return;
        }
        if (!enabled && !requested) {
            targetSearchDeadline = 0L;
            return;
        }
        long next = prefs.getLong("next_run", 0L);
        if (enabled && next == 0L && !requested) {
            prefs.edit().putLong("next_run", now + interval()).apply();
            setStatus("Aguardando o próximo ciclo.");
            return;
        }
        if (!requested && now < next) {
            targetSearchDeadline = 0L;
            setStatus("Aguardando o próximo ciclo.");
            return;
        }
        if (!screenReady()) {
            setStatus("Ciclo aguardando tela ligada e desbloqueada.");
            return;
        }
        if (checkSelfPermission(Manifest.permission.READ_PHONE_STATE)
                != PackageManager.PERMISSION_GRANTED) {
            setStatus("Conceda a permissão Telefone para verificar chamadas antes do ciclo.");
            return;
        }
        TelecomManager telecom = (TelecomManager) getSystemService(TELECOM_SERVICE);
        if (telecom == null) {
            setStatus("Não foi possível verificar chamadas. Ciclo adiado.");
            return;
        }
        try {
            if (telecom.isInCall()) {
                setStatus("Chamada em andamento: ciclo adiado.");
                return;
            }
        } catch (SecurityException e) {
            setStatus("Sem permissão para verificar chamadas. Ciclo adiado.");
            return;
        }
        if (Settings.Global.getInt(getContentResolver(), Settings.Global.AIRPLANE_MODE_ON, 0) != 0) {
            setStatus("Modo avião ativo: ciclo adiado.");
            return;
        }

        if (targetSearchDeadline == 0L) {
            targetSearchDeadline = now + STAGE_TIMEOUT;
            lastOpenAttempt = -OPEN_RETRY;
        }
        if (now >= targetSearchDeadline) {
            prefs.edit().putBoolean("enabled", false).putBoolean("request_now", false)
                    .putString("phase", "idle").apply();
            targetSearchDeadline = 0L;
            setStatus("Chave não localizada. Abra Informações do telefone e tente novamente.");
            return;
        }
        Search found = findRadioSwitch();
        if (found.ambiguous) {
            prefs.edit().putBoolean("enabled", false).putBoolean("request_now", false).apply();
            targetSearchDeadline = 0L;
            setStatus("Controle de rádio ambíguo. Abra a tela Informações do telefone.");
            return;
        }
        if (found.node == null) {
            openInfoIfNeeded(now, false);
            return;
        }
        if (!prepareVisible(found.node)) return;
        if (!found.node.isChecked()) {
            // We never assume responsibility for a radio that was already off.
            targetSearchDeadline = 0L;
            consumeRequestAndSchedule(now);
            setStatus("O rádio já estava desligado. Nenhuma alteração foi feita.");
            returnToAppIfAppropriate();
            return;
        }
        if (!found.node.isEnabled() || !found.node.isClickable()) {
            setStatus("A chave de rádio não está disponível para acionamento.");
            return;
        }
        targetSearchDeadline = 0L;

        // commit() must succeed before the first potentially destructive action.
        // A synchronous durable recovery marker is more important than this tiny
        // preferences write on the main thread.
        if (!prefs.edit().putBoolean("pending_restore", true)
                .putString("phase", "wait_off").putBoolean("request_now", false)
                .putLong("next_run", enabled ? now + interval() : 0L).commit()) {
            setStatus("Não foi possível salvar o estado. Rádio mantido ligado.");
            return;
        }
        stage = WAIT_OFF;
        offIssuedAt = now;
        observedOnAt = 0L;
        deadline = now + STAGE_TIMEOUT;
        finishReason = "";
        setStatus("Desativando rádio; aguardando confirmação na interface.");
        if (!found.node.performAction(AccessibilityNodeInfo.ACTION_CLICK)) {
            stage = RESTORE;
            setPhase("restore");
            finishReason = "Ciclo não concluído. Rádio ligado.";
            setStatus("Não confirmei o comando. Verificando religamento.");
        }
    }

    private void recoveryStep(long now) {
        Search found = findRadioSwitch();
        if (found.ambiguous) {
            stopForRecovery("Religamento pendente: controle ambíguo. Ative a chave manualmente.");
            return;
        }
        if (found.node == null) {
            if (stage == MANUAL_RESTORE) {
                openInfoIfNeeded(now, true);
                return;
            }
            if (recoverySearchDeadline == 0L) {
                recoverySearchDeadline = now + STAGE_TIMEOUT;
                lastOpenAttempt = -OPEN_RETRY;
            }
            if (now >= recoverySearchDeadline
                    || ((stage == WAIT_OFF || stage == WAIT_ON) && now >= deadline)) {
                stopForRecovery("Não confirmei o rádio ligado. Abra a tela e ative a chave manualmente.");
            }
            openInfoIfNeeded(now, true);
            return;
        }
        recoverySearchDeadline = 0L;
        if (!found.node.isVisibleToUser() && (stage == WAIT_OFF || stage == WAIT_ON)
                && now >= deadline) {
            stopForRecovery("Não confirmei o rádio ligado. Mostre a chave e ative-a manualmente.");
            return;
        }
        if (!prepareVisible(found.node)) return;

        if (stage == WAIT_OFF) {
            if (!found.node.isChecked()) {
                stage = PAUSE_OFF;
                deadline = now + Math.max(500L, Math.min(10_000L,
                        prefs.getLong("off_ms", 2_000L)));
                setPhase("pause_off");
                setStatus("Chave desligada. Aguardando breve pausa para religar.");
            } else if (now >= deadline) {
                prefs.edit().putBoolean("enabled", false).apply();
                stage = RESTORE;
                setPhase("restore");
                finishReason = "Desligamento não confirmado. Rádio ligado e rotina parada.";
            }
            return;
        }
        if (stage == PAUSE_OFF) {
            if (found.node.isChecked()) {
                stage = RESTORE;
                setPhase("restore");
                return;
            }
            if (now < deadline) return;
            stage = RESTORE;
            setPhase("restore");
        }
        if (stage == RESTORE) {
            if (found.node.isChecked()) {
                // Let a just-issued OFF click settle before deciding that no
                // recovery is needed (for example after pressing Stop).
                if (offIssuedAt != 0L && now - offIssuedAt < 1_500L) return;
                if (onObservedStable(now)) finishRestore();
                return;
            }
            if (!found.node.isEnabled() || !found.node.isClickable()) {
                setStatus("Religamento pendente: ative manualmente a chave de rádio.");
                return;
            }
            stage = WAIT_ON;
            observedOnAt = 0L;
            deadline = now + STAGE_TIMEOUT;
            setPhase("wait_on");
            setStatus("Reativando rádio; aguardando confirmação na interface.");
            // Exactly one ON attempt in this recovery phase. A failed/uncertain
            // click is observed until timeout rather than clicked repeatedly.
            found.node.performAction(AccessibilityNodeInfo.ACTION_CLICK);
            return;
        }
        if (stage == WAIT_ON) {
            if (found.node.isChecked()) {
                if (onObservedStable(now)) finishRestore();
            } else if (now >= deadline) {
                stopForRecovery("Não confirmei o rádio ligado. Ative a chave manualmente.");
            } else {
                observedOnAt = 0L;
            }
            return;
        }
        if (stage == MANUAL_RESTORE) {
            if (found.node.isChecked()) {
                if (onObservedStable(now)) finishRestore();
            } else observedOnAt = 0L;
        }
    }

    private boolean onObservedStable(long now) {
        if (observedOnAt == 0L) observedOnAt = now;
        return now - observedOnAt >= 1_000L;
    }

    private void finishRestore() {
        boolean running = prefs.getBoolean("enabled", false);
        String message = finishReason.length() > 0 ? finishReason
                : (running ? "Rádio ligado. Aguardando o próximo ciclo."
                : "Rádio ligado. Rotina parada.");
        if (!prefs.edit().putBoolean("pending_restore", false)
                .putString("phase", "idle").putBoolean("request_now", false).commit()) {
            stopForRecovery("Rádio ligado, mas não foi possível salvar a confirmação. Rotina parada.");
            return;
        }
        stage = IDLE;
        offIssuedAt = 0L;
        recoverySearchDeadline = 0L;
        observedOnAt = 0L;
        finishReason = "";
        setStatus(message);
        returnToAppIfAppropriate();
    }

    private void stopForRecovery(String message) {
        stage = MANUAL_RESTORE;
        finishReason = "Rádio ligado. Rotina parada.";
        prefs.edit().putBoolean("enabled", false).putBoolean("request_now", false)
                .putString("phase", "manual_restore").apply();
        setStatus(message);
    }

    private void consumeRequestAndSchedule(long now) {
        prefs.edit().putBoolean("request_now", false).putString("phase", "idle")
                .putLong("next_run", prefs.getBoolean("enabled", false)
                        ? now + interval() : 0L).apply();
    }

    private long interval() {
        return Math.max(10_000L, Math.min(86_400_000L,
                prefs.getLong("interval_ms", 300_000L)));
    }

    private boolean screenReady() {
        PowerManager power = (PowerManager) getSystemService(POWER_SERVICE);
        KeyguardManager keyguard = (KeyguardManager) getSystemService(KEYGUARD_SERVICE);
        return power != null && power.isInteractive() && keyguard != null
                && !keyguard.isKeyguardLocked();
    }

    private void openInfoIfNeeded(long now, boolean recovery) {
        if (stage == MANUAL_RESTORE) {
            setStatus("Religamento pendente. Abra Informações do telefone e ative a chave de rádio.");
            return;
        }
        if (now - lastOpenAttempt >= OPEN_RETRY) {
            lastOpenAttempt = now;
            try {
                if (RadioSupport.openRadioInfo(this)) openedSettings = true;
            } catch (RuntimeException e) {
                Log.w(TAG, "Radio information activity unavailable");
            }
        }
        setStatus(recovery
                ? "Religamento pendente. Abra Informações do telefone e mostre a chave de rádio."
                : "Abra Informações do telefone e mostre a chave Potência de rádio móvel.");
    }

    private boolean prepareVisible(AccessibilityNodeInfo node) {
        if (node.isVisibleToUser()) return true;
        node.performAction(AccessibilityNodeInfo.AccessibilityAction.ACTION_SHOW_ON_SCREEN.getId());
        setStatus(prefs.getBoolean("pending_restore", false)
                ? "Religamento pendente. Deixe a chave de rádio visível na tela."
                : "Localizando a chave de rádio na tela.");
        return false;
    }

    private void returnToAppIfAppropriate() {
        if (!openedSettings) return;
        AccessibilityNodeInfo root = getRootInActiveWindow();
        if (root != null && allowedPackage(root.getPackageName())) {
            openedSettings = false;
            RadioSupport.returnToApp(this);
        }
    }

    private void setPhase(String phase) {
        if (!phase.equals(prefs.getString("phase", "idle"))) {
            prefs.edit().putString("phase", phase).apply();
        }
    }

    private void setStatus(String status) {
        if (!status.equals(prefs.getString("status", ""))) {
            prefs.edit().putString("status", status).apply();
            RadioSupport.updateNotification(this);
        }
    }

    private static boolean allowedPackage(CharSequence name) {
        return name != null && (PACKAGES[0].contentEquals(name) || PACKAGES[1].contentEquals(name));
    }

    private static final class Search {
        AccessibilityNodeInfo node;
        boolean ambiguous;
    }

    private Search findRadioSwitch() {
        Search result = new Search();
        AccessibilityNodeInfo root = getRootInActiveWindow();
        if (root == null || !allowedPackage(root.getPackageName())) return result;
        List<AccessibilityNodeInfo> exact = new ArrayList<>();
        for (String pkg : PACKAGES) {
            for (String id : IDS) {
                List<AccessibilityNodeInfo> matches = root.findAccessibilityNodeInfosByViewId(pkg + ":id/" + id);
                for (AccessibilityNodeInfo node : matches) {
                    if (node.isCheckable() && allowedPackage(node.getPackageName())) addUnique(exact, node);
                }
            }
        }
        if (!exact.isEmpty()) {
            result.ambiguous = exact.size() != 1;
            if (!result.ambiguous) result.node = exact.get(0);
            return result;
        }

        // A localized exact label may identify a row, but never select a switch
        // merely because it happens to be the only switch on an arbitrary screen.
        List<AccessibilityNodeInfo> labels = new ArrayList<>();
        collectExactLabels(root, labels, new int[]{0}, 0);
        List<AccessibilityNodeInfo> candidates = new ArrayList<>();
        for (AccessibilityNodeInfo label : labels) {
            AccessibilityNodeInfo candidate = nearestLabeledSwitch(label);
            if (candidate != null) addUnique(candidates, candidate);
            else result.ambiguous = true;
        }
        if (candidates.size() == 1 && !result.ambiguous) result.node = candidates.get(0);
        else if (candidates.size() > 1) result.ambiguous = true;
        return result;
    }

    private static void collectExactLabels(AccessibilityNodeInfo node,
            List<AccessibilityNodeInfo> labels, int[] budget, int depth) {
        if (node == null || depth > 24 || ++budget[0] > 600) return;
        if (exactLabel(node.getText()) || exactLabel(node.getContentDescription())) labels.add(node);
        for (int i = 0; i < node.getChildCount(); i++) {
            collectExactLabels(node.getChild(i), labels, budget, depth + 1);
        }
    }

    private static boolean exactLabel(CharSequence text) {
        if (text == null) return false;
        String value = text.toString().trim();
        return "Potência de rádio móvel".equals(value) || "Mobile radio power".equals(value);
    }

    private static AccessibilityNodeInfo nearestLabeledSwitch(AccessibilityNodeInfo label) {
        if (label.isCheckable() && allowedPackage(label.getPackageName())) return label;
        AccessibilityNodeInfo area = label.getParent();
        Rect labelBounds = new Rect();
        label.getBoundsInScreen(labelBounds);
        if (labelBounds.isEmpty()) return null;
        for (int level = 0; area != null && level < 3; level++, area = area.getParent()) {
            List<AccessibilityNodeInfo> matches = new ArrayList<>();
            collectCheckable(area, matches, 0, new int[]{0});
            if (matches.size() > 1) return null;
            if (matches.size() == 1) {
                AccessibilityNodeInfo candidate = matches.get(0);
                Rect bounds = new Rect();
                candidate.getBoundsInScreen(bounds);
                // Require the label and switch to occupy the same visual row.
                if (!bounds.isEmpty() && bounds.top < labelBounds.bottom
                        && labelBounds.top < bounds.bottom) return candidate;
                return null;
            }
        }
        return null;
    }

    private static void collectCheckable(AccessibilityNodeInfo node,
            List<AccessibilityNodeInfo> matches, int depth, int[] budget) {
        if (node == null || depth > 4 || ++budget[0] > 100 || matches.size() > 1) return;
        if (node.isCheckable() && allowedPackage(node.getPackageName())) addUnique(matches, node);
        for (int i = 0; i < node.getChildCount(); i++) {
            collectCheckable(node.getChild(i), matches, depth + 1, budget);
        }
    }

    private static void addUnique(List<AccessibilityNodeInfo> nodes, AccessibilityNodeInfo node) {
        for (AccessibilityNodeInfo present : nodes) if (present.equals(node)) return;
        nodes.add(node);
    }

    @Override public boolean onUnbind(Intent intent) {
        bestEffortRestoreOnExit();
        connected = false;
        handler.removeCallbacks(tick);
        tickQueued = false;
        return super.onUnbind(intent);
    }

    @Override public void onDestroy() {
        bestEffortRestoreOnExit();
        connected = false;
        handler.removeCallbacks(tick);
        tickQueued = false;
        if (prefs != null) prefs.unregisterOnSharedPreferenceChangeListener(this);
        super.onDestroy();
    }

    private void bestEffortRestoreOnExit() {
        if (exitRestoreAttempted || prefs == null || !prefs.getBoolean("pending_restore", false)) return;
        exitRestoreAttempted = true;
        // Do not clear the durable flag without observing a later ON state.
        // There is deliberately no claim that this runs on Android force-stop.
        try {
            if (screenReady()) {
                Search found = findRadioSwitch();
                if (!found.ambiguous && found.node != null && found.node.isVisibleToUser()
                        && found.node.isEnabled() && found.node.isClickable()
                        && !found.node.isChecked()) {
                    found.node.performAction(AccessibilityNodeInfo.ACTION_CLICK);
                }
            }
            setStatus("Serviço encerrado com religamento pendente. Verifique a chave de rádio.");
        } catch (RuntimeException e) {
            Log.w(TAG, "Recovery requires service restart or manual action");
        }
    }
}
