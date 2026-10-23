package org.yc.lean;

import android.content.Context;
import android.os.Process;
import android.util.Log;
import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.security.MessageDigest;
import java.util.Locale;
import java.util.zip.ZipEntry;
import java.util.zip.ZipFile;

final class NativeRuntime {
    private static boolean attempted;
    private static boolean available;
    private static native boolean ready();

    static synchronized boolean load(Context context) {
        if (attempted) return available;
        attempted = true;
        try {
            String arch = System.getProperty("os.arch", "").toLowerCase(Locale.US);
            String abi;
            if (arch.contains("x86") || arch.contains("amd64") || arch.matches("i[3-6]86")) {
                abi = Process.is64Bit() ? "x86_64" : "x86";
            } else if (arch.contains("arm") || arch.contains("aarch64")) {
                abi = Process.is64Bit() ? "arm64-v8a" : "armeabi-v7a";
            } else throw new IOException("Unsupported VM architecture: " + arch);
            File directory = new File(context.getCodeCacheDir(), "yc_identity/" + abi);
            if (!directory.isDirectory() && !directory.mkdirs()) throw new IOException("Cannot create hook directory");
            File library = new File(directory, "libycidentity.so");
            String entryName = "assets/yc_hooks/" + abi + "/libycidentity.so";
            try (ZipFile zip = new ZipFile(OriginalApk.container(context))) {
                ZipEntry entry = zip.getEntry(entryName);
                ZipEntry digestEntry = zip.getEntry(entryName + ".sha256");
                if (entry == null || digestEntry == null) throw new IOException("Native hook asset missing for " + abi);
                byte[] digestBytes = new byte[64];
                try (InputStream input = zip.getInputStream(digestEntry)) {
                    int offset = 0;
                    while (offset < digestBytes.length) {
                        int count = input.read(digestBytes, offset, digestBytes.length - offset);
                        if (count < 0) throw new IOException("Native digest incomplete");
                        offset += count;
                    }
                }
                String expected = new String(digestBytes, java.nio.charset.StandardCharsets.US_ASCII);
                if (!library.isFile() || library.length() != entry.getSize() || !expected.equals(digest(library))) {
                    File temporary = File.createTempFile("hook-", ".so", directory);
                    try {
                        try (InputStream input = zip.getInputStream(entry); FileOutputStream output = new FileOutputStream(temporary)) {
                            byte[] buffer = new byte[65536];
                            int count;
                            while ((count = input.read(buffer)) != -1) output.write(buffer, 0, count);
                            output.getFD().sync();
                        }
                        if (temporary.length() != entry.getSize() || !expected.equals(digest(temporary))) throw new IOException("Native digest mismatch");
                        if (!temporary.renameTo(library)) throw new IOException("Cannot persist native hook");
                    } finally { temporary.delete(); }
                }
            }
            System.load(library.getAbsolutePath());
            available = ready();
            Log.i("YCLean", "ART identity runtime ready=" + available + " VM ABI=" + abi);
        } catch (Exception failure) {
            Log.w("YCLean", "ART identity runtime unavailable", failure);
        } catch (LinkageError failure) {
            Log.w("YCLean", "ART identity runtime could not load", failure);
        }
        return available;
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
