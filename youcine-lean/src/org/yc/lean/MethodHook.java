package org.yc.lean;

import java.lang.reflect.InvocationTargetException;
import java.lang.reflect.Field;
import java.lang.reflect.Member;
import java.lang.reflect.Method;
import java.lang.reflect.Modifier;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import java.util.UUID;
import java.util.concurrent.CountDownLatch;

/** Small per-method callbacks; the original mod's loader/native code is not used. */
public final class MethodHook {
    private static final List<MethodHook> KEEP = new ArrayList<>();
    private final int fingerprint;
    private final int maskIndex;
    private final int maskBit;
    private final boolean skip;
    private final boolean isStatic;
    private final String label;
    private final CountDownLatch installed = new CountDownLatch(1);
    private volatile Method backup;
    private boolean logged;
    private boolean invocationLogged;
    private final Field fingerprintField;

    private MethodHook(Member target, int fingerprint, int maskIndex, boolean skip) throws Exception {
        this.fingerprint = fingerprint;
        this.maskIndex = maskIndex;
        this.maskBit = 1 << fingerprint;
        this.skip = skip;
        this.isStatic = Modifier.isStatic(target.getModifiers());
        this.label = target.getDeclaringClass().getName() + "." + target.getName();
        fingerprintField = skip ? null : target.getDeclaringClass().getDeclaredField("fingerprint");
        if (fingerprintField != null) fingerprintField.setAccessible(true);
    }

    private native Method install0(Member target, Method callback);

    static synchronized boolean constructor(Member target, int fingerprint, int stringCount) throws Exception {
        return install(target, fingerprint, stringCount, false);
    }
    static synchronized boolean noOp(Member target) throws Exception {
        return install(target, 0, 0, true);
    }
    private static boolean install(Member target, int fingerprint, int maskIndex, boolean skip) throws Exception {
        MethodHook hook = new MethodHook(target, fingerprint, maskIndex, skip);
        try {
            hook.backup = hook.install0(target, MethodHook.class.getDeclaredMethod("callback", Object[].class));
            if (hook.backup == null) return false;
            hook.backup.setAccessible(true);
            KEEP.add(hook);
            return true;
        } finally { hook.installed.countDown(); }
    }

    public Object callback(Object[] arguments) throws Throwable {
        if (skip) {
            reportOnce("Properties persistence callback skipped: ");
            return null;
        }
        installed.await();
        Method original = backup;
        if (original == null) throw new IllegalStateException("Original method unavailable: " + label);
        int offset = isStatic ? 0 : 1;
        int flags = (Integer) arguments[offset + maskIndex];
        reportInvocation(flags);
        String generated = null;
        if ((flags & maskBit) != 0) {
            generated = UUID.randomUUID().toString();
            arguments[offset + fingerprint] = generated;
            arguments[offset + maskIndex] = flags & ~maskBit;
        }
        try {
            Object receiver = isStatic ? null : arguments[0];
            Object[] parameters = isStatic ? arguments : Arrays.copyOfRange(arguments, 1, arguments.length);
            Object result = original.invoke(receiver, parameters);
            if (generated != null) {
                if (generated.equals(fingerprintField.get(receiver))) {
                    reportOnce("Fresh request fingerprint applied: ");
                    StartupTrace.event("fingerprint-field-verified", label);
                } else {
                    NativeRuntime.warn("Fingerprint constructor argument did not reach target field: " + label);
                }
            }
            return result;
        } catch (InvocationTargetException failure) { throw failure.getCause(); }
    }

    private synchronized void reportOnce(String prefix) {
        if (!logged) { logged = true; NativeRuntime.info(prefix + label); }
    }
    private synchronized void reportInvocation(int flags) {
        if (invocationLogged) return;
        invocationLogged = true;
        NativeRuntime.info("Request default constructor invoked: " + label + " mask=" + flags
                + " fingerprint_default=" + ((flags & maskBit) != 0));
    }
}
