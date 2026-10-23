package org.yc.lean;

import android.content.ContentProvider;
import android.content.ContentValues;
import android.content.Context;
import android.database.Cursor;
import android.net.Uri;
import android.os.Build;
import android.util.Log;
import java.io.File;
import java.lang.reflect.Field;

/** Initializes before Application.onCreate using the normal Android lifecycle. */
public final class IdentityProvider extends ContentProvider {
    @Override public boolean onCreate() {
        Context context = getContext();
        if (context == null) return true;
        try {
            File parent = Build.VERSION.SDK_INT >= 21
                    ? context.getNoBackupFilesDir()
                    : context.getDir("yc_lean", Context.MODE_PRIVATE);
            if (parent == null) throw new IllegalStateException("No application data directory");
            String identity = InstallIdentity.readOrCreate(new File(parent, "yc_lean"));

            // The reference changes the fingerprint sent by its request beans.
            // This prototype supplies it through Build in this process only.
            // Directly replacing encrypted bean constructors requires their decoded DEX.
            Field field = Build.class.getField("FINGERPRINT");
            field.setAccessible(true);
            field.set(null, identity);
            if (!identity.equals(Build.FINGERPRINT)) {
                throw new IllegalStateException("Fingerprint assignment was not applied");
            }
            Log.i("YCLean", "Per-install identity initialized");
        } catch (Exception failure) {
            // An optional initializer must not prevent the original application opening.
            Log.w("YCLean", "Original initialization retained", failure);
        } catch (LinkageError failure) {
            Log.w("YCLean", "Initializer unavailable on this runtime", failure);
        }
        return true;
    }

    @Override public Cursor query(Uri uri, String[] projection, String selection,
            String[] selectionArgs, String sortOrder) { return null; }
    @Override public String getType(Uri uri) { return null; }
    @Override public Uri insert(Uri uri, ContentValues values) { return null; }
    @Override public int delete(Uri uri, String selection, String[] args) { return 0; }
    @Override public int update(Uri uri, ContentValues values, String selection,
            String[] args) { return 0; }
}
