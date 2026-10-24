package org.yc.lean;

import android.content.ContentProvider;
import android.content.ContentValues;
import android.database.Cursor;
import android.net.Uri;
import android.util.Log;

/** Installs the verified DTO hook before the original authentication startup. */
public final class IdentityProvider extends ContentProvider {
    @Override public boolean onCreate() {
        StartupTrace.initialize(getContext());
        StartupTrace.event("provider-enter", "mode=" + StartupTrace.mode());
        Log.i("YCLean", "v3.5 identity provider entered; mode=" + StartupTrace.mode());
        if (StartupTrace.mode() == StartupTrace.Mode.OFF) {
            StartupTrace.event("rules-disabled", "No engine, app hooks or instrumentation boundary");
        } else {
            if (StartupTrace.engine()) {
                StartupTrace.event("early-rules-enter", "before original Application.onCreate");
                IdentityRules.install(getContext());
                StartupTrace.event("early-rules-return", "before original Application.onCreate");
            }
            AfterApplication.schedule(getContext());
        }
        return true;
    }
    @Override public Cursor query(Uri uri, String[] projection, String selection, String[] arguments, String order) { return null; }
    @Override public String getType(Uri uri) { return null; }
    @Override public Uri insert(Uri uri, ContentValues values) { return null; }
    @Override public int delete(Uri uri, String selection, String[] arguments) { return 0; }
    @Override public int update(Uri uri, ContentValues values, String selection, String[] arguments) { return 0; }
}
