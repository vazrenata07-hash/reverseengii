package org.yc.lean;

import android.app.Activity;
import android.app.Application;
import android.app.Instrumentation;
import android.content.Context;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import java.lang.reflect.Field;
import java.lang.reflect.Method;

/** One-shot boundary after the original Application.onCreate returns. */
final class AfterApplication {
    private static boolean scheduled;
    private static boolean started;

    static synchronized void schedule(final Context context) {
        if (scheduled) return;
        scheduled = true;
        try {
            Class<?> type = Class.forName("android.app.ActivityThread");
            Method current = type.getDeclaredMethod("currentActivityThread");
            current.setAccessible(true);
            final Object thread = current.invoke(null);
            final Field field = type.getDeclaredField("mInstrumentation");
            field.setAccessible(true);
            final Instrumentation original = (Instrumentation) field.get(thread);
            // Custom instrumentation may have its own dispatch rules.
            if (original == null || original.getClass() != Instrumentation.class)
                throw new IllegalStateException("Nonstandard instrumentation");
            field.set(thread, new Instrumentation() {
                @Override public void callApplicationOnCreate(Application application) {
                    // Restore before entering the app: all its subsequent
                    // instrumentation calls see the original object and fields.
                    try { field.set(thread, original); }
                    catch (Exception failure) {
                        NativeRuntime.warn("Original instrumentation restoration failed", failure);
                    }
                    original.callApplicationOnCreate(application);
                    initialize(application, "application-return");
                }
                @Override public boolean onException(Object object, Throwable failure) {
                    return original.onException(object, failure);
                }
            });
            NativeRuntime.info("Identity startup scheduled after original Application.onCreate");
        } catch (Exception failure) {
            NativeRuntime.warn("Application-return boundary unavailable; using main queue", failure);
            new Handler(Looper.getMainLooper()).post(new Runnable() {
                @Override public void run() {
                    Context application = context.getApplicationContext();
                    if (application instanceof Application) initialize((Application) application, "main-queue");
                    else NativeRuntime.warn("Identity startup skipped: original Application unavailable");
                }
            });
        }
    }

    private static synchronized void initialize(final Application application, String boundary) {
        if (started) return;
        started = true;
        try {
            NativeRuntime.info("v3.3.3 original Application.onCreate completed; boundary=" + boundary);
            IdentityRules.install(application);
            NativeRuntime.info("v3.3.3 identity rules initialization completed; app=" + application.getClass().getName());
            application.registerActivityLifecycleCallbacks(new Application.ActivityLifecycleCallbacks() {
                @Override public void onActivityPreCreated(Activity activity, Bundle state) {
                    IdentityRules.retryBeans(activity.getClassLoader());
                }
                @Override public void onActivityCreated(Activity activity, Bundle state) {
                    IdentityRules.retryBeans(activity.getClassLoader());
                }
                @Override public void onActivityStarted(Activity activity) {}
                @Override public void onActivityResumed(Activity activity) {}
                @Override public void onActivityPaused(Activity activity) {}
                @Override public void onActivityStopped(Activity activity) {}
                @Override public void onActivitySaveInstanceState(Activity activity, Bundle state) {}
                @Override public void onActivityDestroyed(Activity activity) {}
            });
        } catch (Exception failure) {
            NativeRuntime.warn("Post-application identity initialization failed", failure);
        } catch (LinkageError failure) {
            NativeRuntime.warn("Post-application identity initialization unavailable", failure);
        }
    }
}
