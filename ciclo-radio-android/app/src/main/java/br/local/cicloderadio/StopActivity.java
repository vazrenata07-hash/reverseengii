package br.local.cicloderadio;

import android.app.Activity;
import android.os.Bundle;

public final class StopActivity extends Activity {
    @Override public void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        RadioSupport.prefs(this).edit().putBoolean("enabled", false)
                .putBoolean("request_now", false).putBoolean("awaiting_network", false)
                .putLong("next_run", 0L).putString("phase", "stop_requested").commit();
        RadioSupport.returnToApp(this);
        finish();
    }
}
