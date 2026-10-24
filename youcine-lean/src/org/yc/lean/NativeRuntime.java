package org.yc.lean;

import android.content.Context;
import android.util.Log;
import dalvik.system.DexClassLoader;
import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.lang.reflect.InvocationTargetException;
import java.security.MessageDigest;
import java.util.Locale;
import java.util.zip.ZipEntry;
import java.util.zip.ZipFile;

final class NativeRuntime {
    private static boolean attempted;
    private static boolean available;
    private static volatile boolean bound;
    private static ClassLoader engineLoader;
    private static native boolean ready();
    private static native void log0(int priority, String message);

    static synchronized boolean load(Context context) {
        if (attempted) return available;
        attempted = true;
        StartupTrace.event("engine-enter", "mode=" + StartupTrace.mode());
        try {
            // os.arch is ARM64 in the supplied MEmu process, while its ART and
            // executable are x86_64. Read the VM executable's actual ELF ISA.
            String abi = executableAbi();
            StartupTrace.event("engine-abi", abi);
            File directory = new File(context.getCodeCacheDir(), "yc_identity/" + abi);
            if (!directory.isDirectory() && !directory.mkdirs()) throw new IOException("Cannot create hook directory");
            File library, dex;
            try (ZipFile zip = new ZipFile(OriginalApk.container(context))) {
                library = extract(zip, "assets/yc_hooks/" + abi + "/libycidentity.so", directory, "libycidentity.so");
                dex = extract(zip, "assets/yc_hooks/engine.dex", directory, "engine.dex");
            }
            // A parent from the app would inherit its translated ARM namespace.
            // The boot parent and an ISA-specific library path make a separate
            // native loader namespace; the original player's loader is intact.
            ClassLoader boot = ClassLoader.getSystemClassLoader();
            while (boot.getParent() != null) boot = boot.getParent();
            engineLoader = new DexClassLoader(dex.getAbsolutePath(), directory.getAbsolutePath(), directory.getAbsolutePath(), boot);
            Class<?> entry = Class.forName("org.yc.lean.EngineEntry", true, engineLoader);
            StartupTrace.event("engine-load-enter", "abi=" + abi + " loader=" + engineLoader.getClass().getName());
            Object result = entry.getMethod("load", String.class, Class.class, Class.class)
                    .invoke(null, library.getAbsolutePath(), NativeRuntime.class, MethodHook.class);
            bound = true;
            available = Boolean.TRUE.equals(result) && ready();
            StartupTrace.event("engine-load-return", "ready=" + available + " abi=" + abi);
            info("ART identity runtime ready=" + available + " VM ABI=" + abi + " loader=isolated");
        } catch (Exception failure) {
            Throwable cause = failure instanceof InvocationTargetException ? ((InvocationTargetException) failure).getCause() : failure;
            StartupTrace.failure("engine-failed", cause);
            warn("ART identity runtime unavailable", cause);
        } catch (LinkageError failure) {
            StartupTrace.failure("engine-linkage-failed", failure);
            warn("ART identity runtime could not load", failure);
        }
        return available;
    }

    static void info(String message) { write(Log.INFO, message); }
    static void warn(String message) { write(Log.WARN, message); }
    static void warn(String message, Throwable failure) {
        java.io.StringWriter stack = new java.io.StringWriter();
        failure.printStackTrace(new java.io.PrintWriter(stack));
        write(Log.WARN, message + "\n" + stack);
    }
    private static void write(int priority, String message) {
        StartupTrace.event("log", message);
        if (bound) {
            try { log0(priority, message); return; }
            catch (LinkageError failure) { StartupTrace.failure("native-log-failed", failure); }
        }
        Log.println(priority, "YCLean", message);
    }

    private static String executableAbi() throws IOException {
        byte[] header = new byte[20];
        try (InputStream input = new FileInputStream("/proc/self/exe")) {
            int at = 0;
            while (at < header.length) {
                int count = input.read(header, at, header.length - at);
                if (count < 0) throw new IOException("VM executable ELF header incomplete");
                at += count;
            }
        }
        if (header[0] != 127 || header[1] != 'E' || header[2] != 'L' || header[3] != 'F' || header[5] != 1)
            throw new IOException("VM executable is not a little-endian ELF");
        int machine = (header[18] & 255) | ((header[19] & 255) << 8);
        if (header[4] == 2 && machine == 62) return "x86_64";
        if (header[4] == 1 && machine == 3) return "x86";
        if (header[4] == 2 && machine == 183) return "arm64-v8a";
        if (header[4] == 1 && machine == 40) return "armeabi-v7a";
        throw new IOException("Unsupported VM executable: class=" + header[4] + " machine=" + machine);
    }

    private static File extract(ZipFile zip, String name, File directory, String fileName) throws Exception {
        ZipEntry entry = zip.getEntry(name), digestEntry = zip.getEntry(name + ".sha256");
        if (entry == null || digestEntry == null) throw new IOException("Engine asset missing: " + name);
        byte[] expectedBytes = new byte[64];
        try (InputStream input = zip.getInputStream(digestEntry)) {
            int at = 0;
            while (at < expectedBytes.length) {
                int count = input.read(expectedBytes, at, expectedBytes.length - at);
                if (count < 0) throw new IOException("Engine digest incomplete");
                at += count;
            }
        }
        String expected = new String(expectedBytes, java.nio.charset.StandardCharsets.US_ASCII);
        File destination = new File(directory, fileName);
        if (destination.isFile() && destination.length() == entry.getSize() && expected.equals(digest(destination))) return destination;
        File temporary = File.createTempFile("engine-", ".tmp", directory);
        try {
            try (InputStream input = zip.getInputStream(entry); FileOutputStream output = new FileOutputStream(temporary)) {
                byte[] buffer = new byte[65536];
                int count;
                while ((count = input.read(buffer)) != -1) output.write(buffer, 0, count);
                output.getFD().sync();
            }
            if (temporary.length() != entry.getSize() || !expected.equals(digest(temporary))) throw new IOException("Engine asset digest mismatch");
            if (!temporary.renameTo(destination)) throw new IOException("Cannot persist engine asset");
            return destination;
        } finally { temporary.delete(); }
    }

    private static String digest(File file) throws Exception {
        MessageDigest digest = MessageDigest.getInstance("SHA-256");
        try (InputStream input = new FileInputStream(file)) {
            byte[] buffer = new byte[65536];
            int count;
            while ((count = input.read(buffer)) != -1) digest.update(buffer, 0, count);
        }
        StringBuilder result = new StringBuilder(64);
        for (byte value : digest.digest()) result.append(String.format(Locale.US, "%02x", value & 255));
        return result.toString();
    }
}
