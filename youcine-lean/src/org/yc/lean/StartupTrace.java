package org.yc.lean;

import android.content.Context;
import android.os.Process;
import android.os.SystemClock;
import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.PrintWriter;
import java.io.StringWriter;
import java.util.List;
import java.util.Locale;
import java.util.Properties;
import org.json.JSONObject;

/** Diagnostic build only: stage journal independent of Java/native log filters. */
final class StartupTrace {
    enum Mode { OFF, BOUNDARY, RUNTIME, BEANS, PROPERTIES, FULL }
    static final String VERSION = "v3.4-debug";
    private static Mode mode = Mode.OFF;
    private static String run = "manual";
    private static File directory;
    private static File journal;
    private static boolean initialized;

    static synchronized void initialize(Context context) {
        if (initialized) return;
        initialized = true;
        try {
            directory = context.getExternalFilesDir("yc_lean");
            if (directory == null || (!directory.isDirectory() && !directory.mkdirs())) return;
            File control = new File(directory, "diagnostic.properties");
            if (control.isFile()) {
                Properties properties = new Properties();
                try (FileInputStream input = new FileInputStream(control)) { properties.load(input); }
                try { mode = Mode.valueOf(properties.getProperty("mode", "off").toUpperCase(Locale.US)); }
                catch (IllegalArgumentException ignored) { mode = Mode.OFF; }
                String requested = properties.getProperty("run", "manual");
                if (requested.matches("[A-Za-z0-9_-]{1,80}")) run = requested;
            }
            journal = new File(directory, "trace-" + run + ".jsonl");
            try (FileOutputStream output = new FileOutputStream(journal, false)) {
                output.write(new byte[0]);
                output.getFD().sync();
            }
            event("trace-start", "mode=" + mode + " app=" + context.getPackageName());
            final Thread.UncaughtExceptionHandler previous = Thread.getDefaultUncaughtExceptionHandler();
            if (previous != null) {
                Thread.setDefaultUncaughtExceptionHandler(new Thread.UncaughtExceptionHandler() {
                    @Override public void uncaughtException(Thread thread, Throwable failure) {
                        failure("uncaught-java", failure);
                        previous.uncaughtException(thread, failure);
                    }
                });
            }
        } catch (Exception ignored) {
            // Diagnostic I/O cannot become an application startup failure.
        }
    }

    static Mode mode() { return mode; }
    static boolean beans() { return mode == Mode.BEANS || mode == Mode.FULL; }
    static boolean properties() { return mode == Mode.PROPERTIES || mode == Mode.FULL; }
    static boolean engine() { return mode != Mode.OFF && mode != Mode.BOUNDARY; }

    static void event(String name, String detail) { append(name, detail, null); }
    static void failure(String name, Throwable failure) {
        StringWriter writer = new StringWriter();
        failure.printStackTrace(new PrintWriter(writer));
        append(name, failure.toString(), writer.toString());
    }
    private static synchronized void append(String name, String detail, String stack) {
        if (journal == null) return;
        try {
            JSONObject record = new JSONObject();
            record.put("version", VERSION);
            record.put("run", run);
            record.put("mode", mode.name().toLowerCase(Locale.US));
            record.put("pid", Process.myPid());
            record.put("tid", Process.myTid());
            record.put("wall_ms", System.currentTimeMillis());
            record.put("uptime_ms", SystemClock.elapsedRealtime());
            record.put("event", name);
            record.put("detail", detail);
            if (stack != null) record.put("stack", stack);
            try (FileOutputStream output = new FileOutputStream(journal, true)) {
                output.write((record.toString() + "\n").getBytes(java.nio.charset.StandardCharsets.UTF_8));
                output.getFD().sync();
            }
        } catch (Exception ignored) {}
    }

    static synchronized void inventory(List<String> names) {
        if (directory == null) return;
        try (FileOutputStream output = new FileOutputStream(new File(directory, "classes-" + run + ".txt"), false)) {
            for (String name : names) output.write((name + "\n").getBytes(java.nio.charset.StandardCharsets.UTF_8));
            output.getFD().sync();
        } catch (Exception failure) { failure("class-inventory-write-failed", failure); }
    }
}
