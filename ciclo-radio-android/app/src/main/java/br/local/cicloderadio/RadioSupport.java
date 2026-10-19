package br.local.cicloderadio;

import android.Manifest;
import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.content.ComponentName;
import android.content.Context;
import android.content.Intent;
import android.content.SharedPreferences;
import android.content.pm.PackageManager;
import android.os.Build;

public final class RadioSupport {
    private RadioSupport() {}

    public static SharedPreferences prefs(Context context) {
        return context.getSharedPreferences("radio_cycle", Context.MODE_PRIVATE);
    }

    public static boolean openRadioInfo(Context context) {
        // RadioInfo mudou de pacote entre versões do AOSP; MIUI usa o pacote Settings.
        String[][] activities = {
            {"com.android.settings", "com.android.settings.RadioInfo"},
            {"com.android.phone", "com.android.phone.settings.RadioInfo"},
            {"com.android.phone", "com.android.phone.RadioInfo"},
            {"com.android.settings", "com.android.settings.TestingSettings"}
        };
        for (String[] name : activities) {
            Intent intent = new Intent(Intent.ACTION_MAIN);
            intent.setComponent(new ComponentName(name[0], name[1]));
            intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_REORDER_TO_FRONT);
            try {
                context.startActivity(intent);
                return true;
            } catch (RuntimeException ignored) {
                // Nenhum código de discagem é enviado; segue para a próxima atividade conhecida.
            }
        }
        return false;
    }

    public static void returnToApp(Context context) {
        Intent intent = new Intent(context, MainActivity.class);
        intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_REORDER_TO_FRONT);
        try { context.startActivity(intent); } catch (RuntimeException ignored) {}
    }

    public static void updateNotification(Context context) {
        SharedPreferences prefs = prefs(context);
        NotificationManager manager = context.getSystemService(NotificationManager.class);
        if (manager == null) return;
        boolean restoring = prefs.getBoolean("pending_restore", false);
        boolean enabled = prefs.getBoolean("enabled", false);
        if (!enabled && !restoring) {
            manager.cancel(10);
            return;
        }
        if (Build.VERSION.SDK_INT >= 33 && context.checkSelfPermission(
                Manifest.permission.POST_NOTIFICATIONS) != PackageManager.PERMISSION_GRANTED) return;
        NotificationChannel channel = new NotificationChannel("radio_cycle",
                "Ciclo de rádio em execução", NotificationManager.IMPORTANCE_LOW);
        channel.setDescription("Andamento e botão para parar e religar o rádio.");
        manager.createNotificationChannel(channel);
        PendingIntent open = PendingIntent.getActivity(context, 1,
                new Intent(context, MainActivity.class), PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE);
        PendingIntent stop = PendingIntent.getActivity(context, 2,
                new Intent(context, StopActivity.class), PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE);
        Notification notification = new Notification.Builder(context, "radio_cycle")
                .setSmallIcon(R.drawable.ic_radio)
                .setContentTitle(restoring ? "Religamento do rádio pendente" : "Ciclo de rádio ativo")
                .setContentText(prefs.getString("status", "Aguardando próximo ciclo."))
                .setContentIntent(open).setOngoing(true).setOnlyAlertOnce(true)
                .addAction(new Notification.Action.Builder(null, "Parar e religar", stop).build())
                .build();
        manager.notify(10, notification);
    }
}
