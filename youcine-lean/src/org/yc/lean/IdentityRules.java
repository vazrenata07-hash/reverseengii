package org.yc.lean;

import android.content.Context;
import android.content.SharedPreferences;
import dalvik.system.DexFile;
import java.lang.reflect.Constructor;
import java.lang.reflect.Field;
import java.lang.reflect.Method;
import java.lang.reflect.Modifier;
import java.util.ArrayList;
import java.util.Enumeration;
import java.util.HashSet;
import java.util.List;
import java.util.Properties;
import java.util.Set;
import java.util.concurrent.ConcurrentHashMap;

/** Rules confirmed in the supplied mod, guarded against a different schema. */
final class IdentityRules {
    private static final Set<String> INSTALLED = new HashSet<>();
    private static boolean runtime;
    private static int retries;
    private static boolean candidatesReported;
    private static boolean attempted;

    static synchronized void install(Context context) {
        if (attempted || context == null) return;
        attempted = true;
        if (!NativeRuntime.load(context)) return;
        runtime = true;
        ClassLoader loader = context.getClassLoader();
        StartupTrace.event("rules-selected", "mode=" + StartupTrace.mode() + " loader=" + loader.getClass().getName());
        try { if (StartupTrace.diagnostic()) StartupTrace.inventory(candidates(loader)); }
        catch (Exception failure) { StartupTrace.failure("class-inventory-failed", failure); }
        if (StartupTrace.beans()) retryBeans(loader);
        try { if (StartupTrace.properties()) installPersistence(context, loader); }
        catch (Exception failure) { NativeRuntime.warn("Properties rule discovery failed", failure); }
        catch (LinkageError failure) { NativeRuntime.warn("Properties rule unavailable", failure); }
        if (StartupTrace.diagnostic() && StartupTrace.mode() == StartupTrace.Mode.FULL) {
            try {
                int inspected = 0;
                for (String name : candidates(loader)) {
                    if (!name.matches("(?i).*(preinstall|sntoken|terminalauth|dcsauth|getauthinfo|authreport|swlauth.*authbean).*")) continue;
                    try { StartupTrace.requestSchema(Class.forName(name, false, loader)); }
                    catch (Exception failure) { StartupTrace.failure("request-schema-class-failed", failure); }
                    catch (LinkageError failure) { StartupTrace.failure("request-schema-class-linkage-failed", failure); }
                    if (++inspected >= 30) break;
                }
            } catch (Exception failure) { StartupTrace.failure("request-schema-enumeration-failed", failure); }
        }
    }

    static synchronized void retryBeans(ClassLoader loader) {
        if (!runtime || !StartupTrace.beans() || INSTALLED.contains("SnTokenBean") || retries++ >= 4) return;
        // The supplied 1.15.4 inventory confirms this exact class/schema.
        // TerminalAuthBean has no fingerprint; the old PreInstall bean is absent.
        bean(loader, "core.request.bean.SnTokenBean", "SnTokenBean", 20, 15);
        if (StartupTrace.diagnostic() && !candidatesReported && INSTALLED.isEmpty()) {
            candidatesReported = true;
            List<String> names;
            try { names = candidates(loader); }
            catch (Exception failure) { StartupTrace.failure("request-name-enumeration-failed", failure); return; }
            int count = 0;
            for (String name : names) {
                if (name.matches("(?i).*(preinstall|sntoken|auth.*bean|bean.*auth|token.*bean|bean.*token).*")) {
                    NativeRuntime.info("Request class candidate (name only): " + name);
                    if (++count >= 40) break;
                }
            }
            NativeRuntime.info("Request class discovery entries=" + names.size() + " related_names=" + count);
        }
    }

    private static void bean(ClassLoader loader, String name, String role, int strings, int fingerprint) {
        if (INSTALLED.contains(role)) return;
        try {
            Class<?> type = Class.forName(name, false, loader);
            for (String field : new String[] {"fingerprint", "androidId", "wifiMac", "serialNumber"}) {
                if (type.getDeclaredField(field).getType() != String.class) {
                    throw new IllegalStateException("Unexpected identity field: " + field);
                }
            }
            Constructor<?> selected = null;
            for (Constructor<?> constructor : type.getDeclaredConstructors()) {
                Class<?>[] parameters = constructor.getParameterTypes();
                if (parameters.length != strings + 2 || parameters[strings] != int.class
                        || parameters[strings + 1].isPrimitive()) continue;
                boolean matches = true;
                for (int i = 0; i < strings; i++) matches &= parameters[i] == String.class;
                if (matches) {
                    if (selected != null) throw new IllegalStateException("Ambiguous request constructor");
                    selected = constructor;
                }
            }
            if (selected == null) throw new IllegalStateException("Request constructor schema differs from reference");
            selected.setAccessible(true);
            StartupTrace.event("bean-hook-enter", name);
            if (!MethodHook.constructor(selected, fingerprint, strings)) throw new IllegalStateException("Constructor hook rejected");
            INSTALLED.add(role);
            StartupTrace.event("bean-hook-installed", name);
            NativeRuntime.info("Request fingerprint hook installed: " + name + " mask=" + (1 << fingerprint));
        } catch (Exception failure) {
            NativeRuntime.warn("Request identity rule not installed: " + name, failure);
        } catch (LinkageError failure) {
            NativeRuntime.warn("Request identity class unavailable: " + name, failure);
        }
    }

    private static final class Storage {
        final Class<?> type;
        final Method writer;
        final Method reset;
        Storage(Class<?> type, Method writer, Method reset) {
            this.type = type; this.writer = writer; this.reset = reset;
        }
    }

    private static Storage storage(ClassLoader loader, String name) {
        try {
            Class<?> type = Class.forName(name, false, loader);
            int strings = 0;
            boolean singleton = false, list = false, map = false;
            for (Field field : type.getDeclaredFields()) {
                if (!Modifier.isStatic(field.getModifiers())) continue;
                Class<?> value = field.getType();
                if (value == String.class) strings++;
                singleton |= value == type;
                list |= List.class.isAssignableFrom(value);
                map |= ConcurrentHashMap.class.isAssignableFrom(value);
            }
            if (strings < 12 || !singleton || !list || !map) return null;
            Method writer = null, reader = null, reset = null;
            for (Method method : type.getDeclaredMethods()) {
                Class<?>[] parameters = method.getParameterTypes();
                if (method.getReturnType() == Properties.class && parameters.length == 1 && parameters[0] == String.class) reader = method;
                if (method.getReturnType() == void.class && parameters.length == 3
                        && parameters[0] == String.class && parameters[1] == String.class && parameters[2] == String.class) {
                    if (writer != null) return null;
                    writer = method;
                }
                if (method.getName().equals("t") && method.getReturnType() == void.class && parameters.length == 0) reset = method;
            }
            return writer != null && reader != null ? new Storage(type, writer, reset) : null;
        } catch (Exception ignored) { return null; }
        catch (LinkageError ignored) { return null; }
    }

    private static void installPersistence(Context context, ClassLoader loader) throws Exception {
        SharedPreferences cache = context.getSharedPreferences("yc_lean_discovery_v1", 0);
        String cached = cache.getString("storage_class_11504", "");
        Storage selected = cached.isEmpty() ? null : storage(loader, cached);
        if (selected == null) selected = storage(loader, "o2.g");
        if (selected == null) selected = storage(loader, "i2.f");
        if (selected == null) {
            for (String name : candidates(loader)) {
                if (!name.matches("[A-Za-z][A-Za-z0-9_]{0,5}\\.[A-Za-z][A-Za-z0-9_]{0,5}")) continue;
                Storage candidate = storage(loader, name);
                if (candidate == null) continue;
                if (selected != null && selected.type != candidate.type) {
                    NativeRuntime.warn("Properties rule skipped: ambiguous class schema");
                    return;
                }
                selected = candidate;
            }
        }
        if (selected == null) {
            NativeRuntime.warn("Properties rule skipped: no matching class schema");
            return;
        }
        selected.writer.setAccessible(true);
        StartupTrace.event("properties-hook-enter", selected.type.getName() + "." + selected.writer.getName());
        if (!MethodHook.noOp(selected.writer)) throw new IllegalStateException("Properties writer hook rejected");
        StartupTrace.event("properties-hook-installed", selected.type.getName() + "." + selected.writer.getName());
        // t() was also an empty routine in the supplied mod. Only use that
        // name for the reference class; renamed classes require new evidence.
        if (selected.type.getName().equals("i2.f") && selected.reset != null) {
            selected.reset.setAccessible(true);
            if (!MethodHook.noOp(selected.reset)) NativeRuntime.warn("Reference t() rule not installed");
        }
        cache.edit().putString("storage_class_11504", selected.type.getName()).apply();
        NativeRuntime.info("Properties persistence rule installed: " + selected.type.getName() + "." + selected.writer.getName());
    }

    private static List<String> candidates(ClassLoader loader) throws Exception {
        Set<String> names = new HashSet<>();
        for (ClassLoader current = loader; current != null; current = current.getParent()) {
            try {
                Object path = field(current.getClass(), "pathList").get(current);
                Object[] elements = (Object[]) field(path.getClass(), "dexElements").get(path);
                for (Object element : elements) {
                    Object dex = field(element.getClass(), "dexFile").get(element);
                    if (!(dex instanceof DexFile)) continue;
                    Enumeration<String> entries = ((DexFile) dex).entries();
                    while (entries.hasMoreElements()) {
                        String name = entries.nextElement();
                        // Enumerate names only. Each rule filters its own
                        // candidates before loading or inspecting any class.
                        names.add(name);
                    }
                }
            } catch (NoSuchFieldException ignored) {
                // Non-dex parents, including the boot class loader.
            }
        }
        List<String> result = new ArrayList<>(names);
        java.util.Collections.sort(result);
        return result;
    }

    private static Field field(Class<?> type, String name) throws NoSuchFieldException {
        for (Class<?> current = type; current != null; current = current.getSuperclass()) {
            try { Field result = current.getDeclaredField(name); result.setAccessible(true); return result; }
            catch (NoSuchFieldException ignored) {}
        }
        throw new NoSuchFieldException(name);
    }
}
