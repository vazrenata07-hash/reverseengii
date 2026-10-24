package org.yc.compat;

import android.os.Process;
import android.util.Log;
import java.io.ByteArrayOutputStream;
import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.util.Arrays;

/** JNI handoff from the translated wrapper to a helper with the real VM ISA. */
public final class NativePages {
    private static boolean loaded;
    private NativePages() {}
    private static native int protect0(long address, long length, int protection);

    public static boolean translated() {
        String arch = System.getProperty("os.arch", "").toLowerCase(java.util.Locale.ROOT);
        return arch.contains("x86") || arch.contains("amd64") || arch.matches("i[3-6]86");
    }

    public static int protect(long address, long length, int protection) {
        int result = protect0(address, length, protection);
        if (result < 0) {
            Log.e("YCModCompat", "host mprotect failed addr=0x" + Long.toHexString(address)
                    + " bytes=" + length + " prot=" + protection + " errno=" + (-result));
        }
        return result;
    }

    private static byte[] read(InputStream stream) throws IOException {
        if (stream == null) throw new IOException("Missing native compatibility asset");
        try (InputStream input = stream; ByteArrayOutputStream output = new ByteArrayOutputStream()) {
            byte[] buffer = new byte[8192];
            int count;
            while ((count = input.read(buffer)) != -1) output.write(buffer, 0, count);
            return output.toByteArray();
        }
    }

    public static synchronized void load(String originalPath) {
        if (!loaded) {
            try {
                byte[] header = new byte[20];
                try (InputStream input = new FileInputStream(originalPath)) {
                    if (input.read(header) != header.length) throw new IOException("Short native ELF");
                }
                int machine = (header[18] & 255) | ((header[19] & 255) << 8);
                if (machine != 40 && machine != 183) throw new IOException("Unexpected wrapper ISA: " + machine);
                String abi = machine == 40 ? "armeabi-v7a" : "arm64-v8a";
                File directory = new File(originalPath).getParentFile();
                byte[] patched = read(NativePages.class.getClassLoader().getResourceAsStream(
                        "@monxx_mod/" + (machine == 40 ? "arm.so" : "arm64.so")));
                writeIfChanged(new File(originalPath), patched);
                if (translated()) {
                    String hostAbi = Process.is64Bit() ? "x86_64" : "x86";
                    System.load(extract(directory, hostAbi, "yc_host").getAbsolutePath());
                }
                System.load(extract(directory, abi, "yc_mprot").getAbsolutePath());
                loaded = true;
                Log.i("YCModCompat", "v2 guard loaded; wrapper=" + abi + " translated=" + translated());
            } catch (IOException error) {
                throw new IllegalStateException("YCModCompat: cannot prepare native loader", error);
            }
        }
        System.load(originalPath);
    }

    private static File extract(File directory, String abi, String name) throws IOException {
        byte[] bytes = read(NativePages.class.getClassLoader().getResourceAsStream(
                "assets/yc_compat/" + abi + "/" + name));
        File guard = new File(directory, name + "-v2-" + abi + ".so");
        writeIfChanged(guard, bytes);
        return guard;
    }

    private static void writeIfChanged(File file, byte[] bytes) throws IOException {
        if (file.isFile() && file.length() == bytes.length
                && Arrays.equals(bytes, read(new FileInputStream(file)))) return;
        File temporary = File.createTempFile("yc-mprot-v2-", ".tmp", file.getParentFile());
        try {
            try (FileOutputStream output = new FileOutputStream(temporary)) {
                output.write(bytes);
                output.getFD().sync();
            }
            if (!temporary.setReadable(true, true) || !temporary.setExecutable(true, true)) {
                throw new IOException("Cannot set compatibility library permissions");
            }
            if (!temporary.renameTo(file)) throw new IOException("Cannot publish compatibility library");
        } finally {
            if (temporary.exists()) temporary.delete();
        }
    }
}
