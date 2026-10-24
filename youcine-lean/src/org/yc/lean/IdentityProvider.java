package org.yc.lean;

import android.content.ContentProvider;
import android.content.ContentValues;
import android.database.Cursor;
import android.net.Uri;
import android.util.Log;

/** Schedules rules; never initializes ART while providers are being installed. */
public final class IdentityProvider extends ContentProvider {
    @Override public boolean onCreate() {
        Log.i("YCLean", "v3.3.3 identity provider entered; scheduling only");
        AfterApplication.schedule(getContext());
        return true;
    }
    @Override public Cursor query(Uri uri, String[] projection, String selection, String[] arguments, String order) { return null; }
    @Override public String getType(Uri uri) { return null; }
    @Override public Uri insert(Uri uri, ContentValues values) { return null; }
    @Override public int delete(Uri uri, String selection, String[] arguments) { return 0; }
    @Override public int update(Uri uri, ContentValues values, String selection, String[] arguments) { return 0; }
}
