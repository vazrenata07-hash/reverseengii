package br.local.cicloderadio;

import android.app.Activity;
import android.os.Bundle;

public final class StopActivity extends Activity {
    @Override public void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        RadioSupport.prefs(this).edit().putBoolean("enabled", false)
                .putBoolean("request_now", false).putString("phase", "stop_requested").commit();
        RadioSupport.returnToApp(this);
        finish();
    }
}
