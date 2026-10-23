package org.yc.lean;

import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.RandomAccessFile;
import java.nio.channels.FileLock;
import java.nio.charset.StandardCharsets;
import java.util.UUID;

/** An identity scoped to application data; no hardware identifier is changed. */
public final class InstallIdentity {
    private InstallIdentity() {}

    public static synchronized String readOrCreate(File directory) throws IOException {
        if (!directory.isDirectory() && !directory.mkdirs()) {
            throw new IOException("Cannot create identity directory");
        }
        File identity = new File(directory, "identity-v1");
        try (RandomAccessFile guard = new RandomAccessFile(
                new File(directory, "identity.lock"), "rw")) {
            FileLock lock = guard.getChannel().tryLock();
            if (lock == null) {
                throw new IOException("Identity is being initialized by another process");
            }
            try {
                String existing = read(identity);
                if (existing != null) return existing;

                String value = UUID.randomUUID().toString();
                File temporary = File.createTempFile("identity-", ".tmp", directory);
                try {
                    try (FileOutputStream stream = new FileOutputStream(temporary)) {
                        stream.write(value.getBytes(StandardCharsets.US_ASCII));
                        stream.getFD().sync();
                    }
                    if (!temporary.renameTo(identity)) {
                        throw new IOException("Cannot persist identity");
                    }
                    return value;
                } finally {
                    temporary.delete();
                }
            } finally {
                lock.release();
            }
        }
    }

    private static String read(File file) throws IOException {
        if (!file.isFile() || file.length() != 36) return null;
        byte[] bytes = new byte[36];
        try (FileInputStream stream = new FileInputStream(file)) {
            int offset = 0;
            while (offset < bytes.length) {
                int count = stream.read(bytes, offset, bytes.length - offset);
                if (count < 0) return null;
                offset += count;
            }
            if (stream.read() != -1) return null;
        }
        String value = new String(bytes, StandardCharsets.US_ASCII);
        try {
            UUID uuid = UUID.fromString(value);
            return uuid.version() == 4 && uuid.variant() == 2
                    && uuid.toString().equals(value) ? value : null;
        } catch (IllegalArgumentException ignored) {
            return null;
        }
    }
}
