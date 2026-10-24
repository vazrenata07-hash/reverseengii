package org.yc.lean;

import android.app.Activity;
import android.app.AppComponentFactory;
import android.app.Application;
import android.app.Service;
import android.content.BroadcastReceiver;
import android.content.ContentProvider;
import android.content.Intent;
import android.content.pm.ApplicationInfo;
import android.util.Log;
import java.lang.reflect.Field;

/** Runs before the protected application's component factory (Android 9+). */
public final class EarlyFactory extends AppComponentFactory {
    private AppComponentFactory original;
    private boolean identityPrepared;

    public EarlyFactory() {
        Log.i("YCLean", "v3.5 early factory entered");
        SignatureAdapter.install();
    }

    private synchronized AppComponentFactory original() {
        if (original == null) {
            try {
                original = (AppComponentFactory) Class.forName("s.h.e.l.l.A", true,
                        EarlyFactory.class.getClassLoader()).getDeclaredConstructor().newInstance();
            } catch (Exception failure) {
                Log.w("YCLean", "Original factory could not be instantiated", failure);
                original = new AppComponentFactory();
            }
        }
        return original;
    }

    private synchronized void prepare(ApplicationInfo info) {
        if (identityPrepared) return;
        try {
            if (info == null || info.dataDir == null) {
                throw new IllegalStateException("Application data directory unavailable");
            }
            OriginalApk.prepare(info);
            identityPrepared = true;
            Log.i("YCLean", "Original image prepared; identity rules run after protected loading");
        } catch (Exception failure) {
            Log.w("YCLean", "Identity initialization skipped", failure);
        } catch (LinkageError failure) {
            Log.w("YCLean", "Identity initialization unsupported", failure);
        }
    }

    private static ApplicationInfo boundApplicationInfo() {
        // Android 9 does not pass ApplicationInfo to instantiateApplication.
        try {
            Class<?> threadClass = Class.forName("android.app.ActivityThread");
            java.lang.reflect.Method method = threadClass.getDeclaredMethod("currentActivityThread");
            method.setAccessible(true);
            Object thread = method.invoke(null);
            Field bound = threadClass.getDeclaredField("mBoundApplication");
            bound.setAccessible(true);
            Object data = bound.get(thread);
            Field appInfo = data.getClass().getDeclaredField("appInfo");
            appInfo.setAccessible(true);
            return (ApplicationInfo) appInfo.get(data);
        } catch (Exception failure) {
            Log.w("YCLean", "Android 9 application metadata unavailable", failure);
            return null;
        }
    }

    @Override public ClassLoader instantiateClassLoader(ClassLoader loader, ApplicationInfo info) {
        prepare(info);
        Log.i("YCLean", "Delegating original class loader");
        ClassLoader result = original().instantiateClassLoader(loader, info);
        Log.i("YCLean", "Original class loader returned");
        return result;
    }

    @Override public Application instantiateApplication(ClassLoader loader, String name)
            throws InstantiationException, IllegalAccessException, ClassNotFoundException {
        if (!identityPrepared) prepare(boundApplicationInfo());
        Log.i("YCLean", "Delegating original application");
        Application result = original().instantiateApplication(loader, name);
        Log.i("YCLean", "Original application instantiated");
        return result;
    }

    @Override public Activity instantiateActivity(ClassLoader loader, String name, Intent intent)
            throws InstantiationException, IllegalAccessException, ClassNotFoundException {
        return original().instantiateActivity(loader, name, intent);
    }

    @Override public Service instantiateService(ClassLoader loader, String name, Intent intent)
            throws InstantiationException, IllegalAccessException, ClassNotFoundException {
        return original().instantiateService(loader, name, intent);
    }

    @Override public BroadcastReceiver instantiateReceiver(ClassLoader loader, String name, Intent intent)
            throws InstantiationException, IllegalAccessException, ClassNotFoundException {
        return original().instantiateReceiver(loader, name, intent);
    }

    @Override public ContentProvider instantiateProvider(ClassLoader loader, String name)
            throws InstantiationException, IllegalAccessException, ClassNotFoundException {
        // Our classes belong to the installed container's loader. The original
        // factory may replace the app loader while unpacking protected code.
        if (IdentityProvider.class.getName().equals(name)) return new IdentityProvider();
        return original().instantiateProvider(loader, name);
    }
}
