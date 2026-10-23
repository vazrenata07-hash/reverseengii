package org.yc.lean;

import android.content.pm.ApplicationInfo;
import android.os.Build;
import android.os.ParcelFileDescriptor;
import android.system.Os;
import android.util.Log;
import java.io.File;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.lang.reflect.Field;
import java.lang.reflect.Method;
import java.security.MessageDigest;
import java.util.zip.ZipEntry;
import java.util.zip.ZipFile;

/** Supplies the original signed image to the original protected loader. */
final class OriginalApk {
    private static final String PACKAGE = "com.world.youcinetv";
    private static final String ENTRY = "assets/yc_original_1_15_4.apk";
    private static final String SHA256 = "5629c0dc0dc0b631f09bd21f81a5d671e64e6d516cb4a28a9b9fb45a2971b231";
    private static final long SIZE = 34006186L;
    private static volatile String originalPath;

    private OriginalApk() {}

    static synchronized void prepare(ApplicationInfo info) throws Exception {
        if (info == null || info.dataDir == null || info.sourceDir == null) {
            throw new IOException("Application paths unavailable");
        }
        if (originalPath == null) {
            File directory = new File(info.dataDir, "no_backup/yc_lean");
            if (!directory.isDirectory() && !directory.mkdirs()) {
                throw new IOException("Cannot create original image directory");
            }
            File image = new File(directory, "original-1.15.4-5629c0dc.apk");
            if (!validImage(image)) extract(new File(info.sourceDir), directory, image);
            // The native loader checks readlink(/proc/self/fd/<opened APK>)
            // against sourceDir. Absolute paths preserve Android's /data/user/0
            // alias, whereas the kernel can report /data/data for that file.
            // Supply the same spelling the kernel uses for the opened image.
            originalPath = kernelPath(image);
            Log.i("YCLean", "Original image path normalized: "
                    + !image.getAbsolutePath().equals(originalPath));
        }
        apply(info);
        updateBoundApplication();
        Log.i("YCLean", "Original signed image supplied to protected loader");
    }

    private static String kernelPath(File image) throws Exception {
        try (ParcelFileDescriptor descriptor = ParcelFileDescriptor.open(
                image, ParcelFileDescriptor.MODE_READ_ONLY)) {
            String path = Os.readlink("/proc/self/fd/" + descriptor.getFd());
            if (!path.startsWith("/") || path.endsWith(" (deleted)")) {
                throw new IOException("Original image has no stable kernel path");
            }
            return path;
        }
    }

    static void apply(ApplicationInfo info) {
        String path = originalPath;
        if (path == null || info == null || !PACKAGE.equals(info.packageName)) return;
        info.sourceDir = path;
        info.publicSourceDir = path;
        if (Build.VERSION.SDK_INT >= 28) info.appComponentFactory = "s.h.e.l.l.A";
    }

    private static boolean validImage(File image) throws Exception {
        if (!image.isFile() || image.length() != SIZE) return false;
        MessageDigest digest = MessageDigest.getInstance("SHA-256");
        byte[] buffer = new byte[131072];
        try (InputStream input = new java.io.FileInputStream(image)) {
            int count;
            while ((count = input.read(buffer)) != -1) digest.update(buffer, 0, count);
        }
        return SHA256.equals(hex(digest.digest()));
    }

    private static void extract(File container, File directory, File image) throws Exception {
        File temporary = File.createTempFile("original-", ".part", directory);
        try {
            MessageDigest digest = MessageDigest.getInstance("SHA-256");
            long total = 0;
            try (ZipFile zip = new ZipFile(container)) {
                ZipEntry entry = zip.getEntry(ENTRY);
                if (entry == null || entry.getSize() != SIZE) {
                    throw new IOException("Original signed image missing from package");
                }
                try (InputStream input = zip.getInputStream(entry);
                        FileOutputStream output = new FileOutputStream(temporary)) {
                    byte[] buffer = new byte[131072];
                    int count;
                    while ((count = input.read(buffer)) != -1) {
                        total += count;
                        if (total > SIZE) throw new IOException("Original image exceeds expected size");
                        digest.update(buffer, 0, count);
                        output.write(buffer, 0, count);
                    }
                    output.getFD().sync();
                }
            }
            if (total != SIZE || !SHA256.equals(hex(digest.digest()))) {
                throw new IOException("Original image digest mismatch");
            }
            if (!temporary.renameTo(image)) throw new IOException("Cannot persist original image");
        } finally {
            temporary.delete();
        }
    }

    private static String hex(byte[] bytes) {
        char[] chars = new char[bytes.length * 2];
        char[] alphabet = "0123456789abcdef".toCharArray();
        for (int index = 0; index < bytes.length; index++) {
            chars[index * 2] = alphabet[(bytes[index] & 255) >>> 4];
            chars[index * 2 + 1] = alphabet[bytes[index] & 15];
        }
        return new String(chars);
    }

    private static Field field(Class<?> type, String name) throws NoSuchFieldException {
        for (Class<?> current = type; current != null; current = current.getSuperclass()) {
            try {
                Field result = current.getDeclaredField(name);
                result.setAccessible(true);
                return result;
            } catch (NoSuchFieldException ignored) {}
        }
        throw new NoSuchFieldException(name);
    }

    private static void updateBoundApplication() {
        try {
            Class<?> threadType = Class.forName("android.app.ActivityThread");
            Method current = threadType.getDeclaredMethod("currentActivityThread");
            current.setAccessible(true);
            Object thread = current.invoke(null);
            Object bound = field(threadType, "mBoundApplication").get(thread);
            ApplicationInfo boundInfo = (ApplicationInfo) field(bound.getClass(), "appInfo").get(bound);
            apply(boundInfo);
            Object loaded = field(bound.getClass(), "info").get(bound);
            if (loaded != null) {
                apply((ApplicationInfo) field(loaded.getClass(), "mApplicationInfo").get(loaded));
                field(loaded.getClass(), "mAppDir").set(loaded, originalPath);
                field(loaded.getClass(), "mResDir").set(loaded, originalPath);
            }
        } catch (Exception failure) {
            Log.w("YCLean", "Framework source path adaptation incomplete", failure);
        }
    }
}
