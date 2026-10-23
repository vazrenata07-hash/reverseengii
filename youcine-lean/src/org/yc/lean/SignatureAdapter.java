package org.yc.lean;

import android.content.pm.PackageInfo;
import android.content.pm.Signature;
import android.os.Build;
import android.os.Parcel;
import android.os.Parcelable;
import android.util.Base64;
import android.util.Log;
import java.lang.reflect.Field;
import java.util.Map;

/** Local PackageInfo compatibility for the repackaged application's own identity. */
final class SignatureAdapter {
    private static final String PACKAGE = "com.world.youcinetv";
    private static boolean installed;

    private SignatureAdapter() {}

    static synchronized void install() {
        if (installed) return;
        try {
            final Signature certificate = new Signature(Base64.decode(OriginalCertificate.BASE64, Base64.DEFAULT));
            final Parcelable.Creator<PackageInfo> source = PackageInfo.CREATOR;
            Parcelable.Creator<PackageInfo> adapter = new Parcelable.Creator<PackageInfo>() {
                @Override public PackageInfo createFromParcel(Parcel parcel) {
                    PackageInfo info = source.createFromParcel(parcel);
                    if (info != null && PACKAGE.equals(info.packageName)) {
                        if (info.signatures != null) info.signatures = new Signature[] { certificate };
                        if (Build.VERSION.SDK_INT >= 28 && info.signingInfo != null) {
                            signingDetails(info.signingInfo, certificate);
                        }
                    }
                    return info;
                }
                @Override public PackageInfo[] newArray(int size) { return source.newArray(size); }
            };
            Field creator = PackageInfo.class.getDeclaredField("CREATOR");
            creator.setAccessible(true);
            creator.set(null, adapter);
            clearCreatorCache("mCreators");
            clearCreatorCache("sPairedCreators");
            installed = true;
            Log.i("YCLean", "Local PackageInfo signature adapter installed");
        } catch (Exception failure) {
            Log.w("YCLean", "Local signature adapter unavailable", failure);
        } catch (LinkageError failure) {
            Log.w("YCLean", "Local signature adapter unsupported", failure);
        }
    }

    private static void signingDetails(Object signingInfo, Signature certificate) {
        try {
            Field detailsField = signingInfo.getClass().getDeclaredField("mSigningDetails");
            detailsField.setAccessible(true);
            Object details = detailsField.get(signingInfo);
            if (details == null) return;
            Field signatures = details.getClass().getDeclaredField("signatures");
            signatures.setAccessible(true);
            signatures.set(details, new Signature[] { certificate });
            try {
                Field history = details.getClass().getDeclaredField("pastSigningCertificates");
                history.setAccessible(true);
                history.set(details, null);
            } catch (NoSuchFieldException ignored) {
                // This Android release stores no certificate history under this name.
            }
        } catch (Exception failure) {
            Log.w("YCLean", "SigningInfo adaptation skipped", failure);
        }
    }

    private static void clearCreatorCache(String name) {
        try {
            Field field = Parcel.class.getDeclaredField(name);
            field.setAccessible(true);
            Object cache = field.get(null);
            if (cache instanceof Map) {
                synchronized (cache) { ((Map<?, ?>) cache).clear(); }
            }
        } catch (Exception ignored) {
            // Cache names differ across Android releases; the cache may not exist.
        }
    }
}
