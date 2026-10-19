package br.local.cicloderadio;

import android.Manifest;
import android.accessibilityservice.AccessibilityServiceInfo;
import android.app.Activity;
import android.app.AlertDialog;
import android.content.ComponentName;
import android.content.Intent;
import android.content.SharedPreferences;
import android.content.pm.PackageManager;
import android.graphics.Color;
import android.graphics.Typeface;
import android.graphics.drawable.GradientDrawable;
import android.os.Build;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.os.SystemClock;
import android.provider.Settings;
import android.text.InputType;
import android.view.View;
import android.view.Window;
import android.view.WindowInsets;
import android.view.WindowManager;
import android.view.accessibility.AccessibilityManager;
import android.widget.ArrayAdapter;
import android.widget.Button;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.Spinner;
import android.widget.TextView;

public final class MainActivity extends Activity {
    private static final int BACKGROUND = Color.rgb(13, 24, 31);
    private static final int CARD = Color.rgb(24, 40, 49);
    private static final int TEXT = Color.rgb(239, 246, 247);
    private static final int MUTED = Color.rgb(167, 190, 199);
    private static final int ACCENT = Color.rgb(92, 225, 189);
    private final Handler handler = new Handler(Looper.getMainLooper());
    private EditText interval, pause;
    private Spinner unit;
    private TextView status, countdown, permissions, publicIp;
    private Button start;
    private SharedPreferences prefs;
    private final Runnable refresh = new Runnable() {
        @Override public void run() {
            update();
            handler.postDelayed(this, 800);
        }
    };

    @Override public void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        prefs = RadioSupport.prefs(this);
        getWindow().setStatusBarColor(BACKGROUND);
        getWindow().setNavigationBarColor(BACKGROUND);
        buildUi();
    }

    private int dp(float value) { return Math.round(value * getResources().getDisplayMetrics().density); }
    private TextView text(String value, int size, int color) {
        TextView view = new TextView(this);
        view.setText(value); view.setTextSize(size); view.setTextColor(color);
        view.setLineSpacing(dp(3), 1.0f);
        return view;
    }
    private GradientDrawable box(int color) {
        GradientDrawable d = new GradientDrawable();
        d.setColor(color); d.setCornerRadius(dp(16)); return d;
    }
    private void gap(LinearLayout parent, int height) {
        View v = new View(this); parent.addView(v, new LinearLayout.LayoutParams(1, dp(height)));
    }
    private void add(LinearLayout parent, View view) {
        parent.addView(view, new LinearLayout.LayoutParams(-1, -2));
    }
    private Button button(String label, boolean primary, View.OnClickListener click) {
        Button b = new Button(this);
        b.setText(label); b.setAllCaps(false); b.setTextSize(16);
        b.setTextColor(primary ? BACKGROUND : TEXT);
        b.setBackground(box(primary ? ACCENT : Color.rgb(42, 61, 71)));
        b.setMinHeight(dp(52)); b.setOnClickListener(click);
        return b;
    }
    private EditText number(String value, String hint) {
        EditText e = new EditText(this);
        e.setText(value); e.setHint(hint); e.setTextColor(TEXT); e.setHintTextColor(MUTED);
        e.setInputType(InputType.TYPE_CLASS_NUMBER);
        e.setTextSize(23); e.setSingleLine(true);
        e.setSelectAllOnFocus(true);
        return e;
    }

    private void buildUi() {
        ScrollView scroll = new ScrollView(this);
        scroll.setFillViewport(true); scroll.setBackgroundColor(BACKGROUND);
        LinearLayout body = new LinearLayout(this);
        body.setOrientation(LinearLayout.VERTICAL);
        body.setPadding(dp(22), dp(28), dp(22), dp(32));
        scroll.addView(body);
        scroll.setOnApplyWindowInsetsListener((view, insets) -> {
            if (Build.VERSION.SDK_INT >= 30) {
                android.graphics.Insets system = insets.getInsets(WindowInsets.Type.systemBars());
                view.setPadding(system.left, system.top, system.right, system.bottom);
            } else view.setPadding(insets.getSystemWindowInsetLeft(), insets.getSystemWindowInsetTop(),
                    insets.getSystemWindowInsetRight(), insets.getSystemWindowInsetBottom());
            return insets;
        });
        TextView eyebrow = text("CONTROLE LOCAL · SEM ROOT", 12, ACCENT);
        eyebrow.setLetterSpacing(0.13f); add(body, eyebrow); gap(body, 8);
        TextView title = text("Ciclo de rádio", 34, TEXT);
        title.setTypeface(Typeface.DEFAULT, Typeface.BOLD); add(body, title); gap(body, 10);
        add(body, text("Desliga e religa a chave “Potência de rádio móvel” no intervalo que você escolher.", 16, MUTED));
        gap(body, 22);

        LinearLayout controls = new LinearLayout(this);
        controls.setOrientation(LinearLayout.VERTICAL); controls.setPadding(dp(18), dp(18), dp(18), dp(18));
        controls.setBackground(box(CARD)); add(body, controls);
        add(controls, text("Repetir a cada", 15, MUTED));
        LinearLayout row = new LinearLayout(this);
        long stored = prefs.getLong("interval_ms", 300000);
        boolean minute = stored % 60000 == 0;
        interval = number(Long.toString(stored / (minute ? 60000 : 1000)), "Intervalo");
        row.addView(interval, new LinearLayout.LayoutParams(0, -2, 1));
        unit = new Spinner(this);
        ArrayAdapter<String> adapter = new ArrayAdapter<>(this, android.R.layout.simple_spinner_dropdown_item,
                new String[]{"segundos", "minutos"});
        unit.setAdapter(adapter); unit.setSelection(minute ? 1 : 0);
        row.addView(unit, new LinearLayout.LayoutParams(dp(145), dp(56)));
        add(controls, row); gap(controls, 15);
        add(controls, text("Pausa com o rádio desligado (segundos)", 15, MUTED));
        pause = number(Long.toString(prefs.getLong("off_ms", 2000) / 1000), "2");
        add(controls, pause); gap(controls, 6);
        add(controls, text("O intervalo só começa depois que a internet móvel volta e o IP público é confirmado. O tempo de reconexão não é descontado.", 13, MUTED));
        gap(body, 18);
        permissions = text("", 14, MUTED); add(body, permissions); gap(body, 12);
        add(body, button("1. Permitir verificar chamadas", false, v -> phonePermission()));
        gap(body, 9);
        add(body, button("2. Ativar acessibilidade", false, v -> accessibilitySettings()));
        gap(body, 9);
        add(body, button("Abrir informação do telefone", false, v -> {
            if (!RadioSupport.openRadioInfo(this)) message("Abra manualmente a tela do vídeo",
                    "O fabricante bloqueou os atalhos conhecidos. Abra a tela Informação do telefone pelo mesmo caminho usado no vídeo. O app não faz chamadas nem disca códigos.");
        }));
        gap(body, 18);
        start = button("Iniciar ciclos", true, v -> begin(false)); add(body, start);
        gap(body, 9);
        add(body, button("Testar um ciclo agora", false, v -> begin(true)));
        gap(body, 9);
        add(body, button("Parar e religar", false, v -> {
            prefs.edit().putBoolean("enabled", false).putBoolean("request_now", false)
                    .putBoolean("awaiting_network", false).putLong("next_run", 0L)
                    .putString("phase", "stop_requested").commit();
            if (!prefs.getBoolean("pending_restore", false)) prefs.edit().putString("status", "Parado.").apply();
            RadioSupport.updateNotification(this); update();
        }));
        gap(body, 22);
        countdown = text("", 20, ACCENT); add(body, countdown); gap(body, 6);
        status = text("", 15, TEXT); add(body, status); gap(body, 6);
        publicIp = text("", 14, MUTED); add(body, publicIp); gap(body, 22);
        add(body, text("Como usar", 17, TEXT)); gap(body, 6);
        add(body, text("Deixe este app aberto, com a tela ligada e desbloqueada. Ele abre a tela do rádio em cada ciclo e retorna quando termina. Se a tela bloquear, o início do ciclo é adiado.", 14, MUTED));
        gap(body, 12);
        add(body, text("Durante o ciclo, dados móveis, hotspot, chamadas e SMS podem ficar indisponíveis. Em aparelhos de dois chips, a chave pode afetar os dois. A reconexão pode levar mais tempo que a pausa escolhida e não garante um novo IP.", 14, MUTED));
        gap(body, 12);
        add(body, text("Use “Parar e religar” antes de desativar a acessibilidade. Se o Android encerrar o app, o rádio pode permanecer desligado até você reabri-lo ou religar manualmente. O app só recupera rádios que ele próprio tentou desligar.", 14, MUTED));
        gap(body, 12);
        add(body, text("Android 13 ou posterior: se a acessibilidade aparecer como restrita, abra Informações do app → menu ⋮ → Permitir configurações restritas. A compatibilidade com a tela do fabricante precisa ser testada no aparelho.", 13, MUTED));
        gap(body, 18);
        add(body, text("Sem anúncios ou conta. Usa uma consulta HTTPS ao ipify pela rede móvel para confirmar o IP público de saída. A chave é acionada por acessibilidade, sem alterar tipo de rede, DSDS ou provisionamento.", 12, MUTED));
        setContentView(scroll);
    }

    private void begin(boolean once) {
        if (prefs.getBoolean("pending_restore", false)) {
            message("Religamento pendente", "Aguarde o rádio ser religado ou abra a tela do vídeo e religue manualmente antes de iniciar outro ciclo."); return;
        }
        if (checkSelfPermission(Manifest.permission.READ_PHONE_STATE) != PackageManager.PERMISSION_GRANTED) {
            phonePermission(); return;
        }
        if (!accessibilityEnabled()) { accessibilitySettings(); return; }
        long ms, off;
        try {
            long n = Long.parseLong(interval.getText().toString());
            if (n <= 0 || n > 86400) throw new NumberFormatException();
            ms = n * (unit.getSelectedItemPosition() == 1 ? 60000L : 1000L);
            off = Long.parseLong(pause.getText().toString()) * 1000L;
            if (ms < 10000 || ms > 86400000L || off < 1000 || off > 10000) throw new NumberFormatException();
        } catch (NumberFormatException e) {
            message("Confira os tempos", "O intervalo deve ficar entre 10 segundos e 24 horas. A pausa desligado deve ficar entre 1 e 10 segundos."); return;
        }
        prefs.edit().putLong("interval_ms", ms).putLong("off_ms", off)
                .putBoolean("enabled", !once).putBoolean("request_now", once)
                .putBoolean("awaiting_network", !once)
                .putString("phase", once ? "idle" : "waiting_network")
                .putLong("next_run", 0L)
                .putString("status", once ? "Teste solicitado." : "Aguardando internet móvel e IP público.").commit();
        if (Build.VERSION.SDK_INT >= 33 && checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS)
                != PackageManager.PERMISSION_GRANTED) requestPermissions(new String[]{Manifest.permission.POST_NOTIFICATIONS}, 11);
        RadioSupport.updateNotification(this); update();
    }

    private boolean accessibilityEnabled() {
        AccessibilityManager manager = getSystemService(AccessibilityManager.class);
        if (manager == null) return false;
        ComponentName expected = new ComponentName(this, RadioAccessibilityService.class);
        for (AccessibilityServiceInfo info : manager.getEnabledAccessibilityServiceList(AccessibilityServiceInfo.FEEDBACK_ALL_MASK)) {
            if (info.getResolveInfo() == null || info.getResolveInfo().serviceInfo == null) continue;
            android.content.pm.ServiceInfo service = info.getResolveInfo().serviceInfo;
            if (expected.equals(new ComponentName(service.packageName, service.name))) return true;
        }
        return false;
    }

    private void accessibilitySettings() {
        Intent details = new Intent("android.settings.ACCESSIBILITY_DETAILS_SETTINGS");
        details.putExtra(Intent.EXTRA_COMPONENT_NAME, new ComponentName(this, RadioAccessibilityService.class));
        try { startActivity(details); }
        catch (RuntimeException e) { startActivity(new Intent(Settings.ACTION_ACCESSIBILITY_SETTINGS)); }
    }
    private void phonePermission() {
        if (checkSelfPermission(Manifest.permission.READ_PHONE_STATE) == PackageManager.PERMISSION_GRANTED) {
            message("Permissão já concedida", "Ela é usada apenas para verificar se há uma chamada em andamento antes de desligar o rádio."); return;
        }
        requestPermissions(new String[]{Manifest.permission.READ_PHONE_STATE}, 10);
    }
    private void message(String title, String value) {
        new AlertDialog.Builder(this).setTitle(title).setMessage(value).setPositiveButton("OK", null).show();
    }
    private void update() {
        if (prefs == null || status == null) return;
        boolean enabled = prefs.getBoolean("enabled", false);
        boolean restoring = prefs.getBoolean("pending_restore", false);
        boolean once = prefs.getBoolean("request_now", false);
        permissions.setText("Chamadas: " + (checkSelfPermission(Manifest.permission.READ_PHONE_STATE) == PackageManager.PERMISSION_GRANTED ? "permitido" : "pendente")
                + "  ·  Acessibilidade: " + (accessibilityEnabled() ? "ativa" : "pendente"));
        status.setText(prefs.getString("status", "Pronto para configurar."));
        String lastIp = prefs.getString("public_ip", "");
        publicIp.setText(lastIp.length() == 0 ? "" : "Último IP público confirmado: " + lastIp);
        if (restoring) countdown.setText("Religamento pendente");
        else if (once) countdown.setText("Preparando teste…");
        else if (enabled && prefs.getBoolean("awaiting_network", true)) countdown.setText("Aguardando conexão e IP público…");
        else if (enabled) {
            long secs = Math.max(0, (prefs.getLong("next_run", 0) - SystemClock.elapsedRealtime() + 999) / 1000);
            countdown.setText(secs > 0 ? "Próximo ciclo em " + (secs / 60) + ":" + String.format(java.util.Locale.ROOT, "%02d", secs % 60) : "Aguardando tela e chamada livres…");
        } else countdown.setText("Ciclos parados");
        start.setEnabled(!restoring);
        if (enabled || restoring || once) getWindow().addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);
        else getWindow().clearFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);
    }

    @Override protected void onResume() {
        super.onResume(); handler.removeCallbacks(refresh); handler.post(refresh);
    }
    @Override protected void onPause() {
        handler.removeCallbacks(refresh); super.onPause();
    }
}
