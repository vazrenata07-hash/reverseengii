package org.yc.lean;

/** Loaded only through a boot-parent class loader with a native ISA path. */
public final class EngineEntry {
    private EngineEntry() {}
    public static boolean load(String path, Class<?> runtime, Class<?> hook) {
        System.load(path);
        return bind(runtime, hook);
    }
    private static native boolean bind(Class<?> runtime, Class<?> hook);
}
