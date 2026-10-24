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
import java.lang.annotation.Annotation;
import java.lang.reflect.Constructor;
import java.lang.reflect.Field;
import java.lang.reflect.Modifier;
import java.lang.reflect.Parameter;
import org.json.JSONArray;
import org.json.JSONObject;

/** Diagnostic build only: stage journal independent of Java/native log filters. */
final class StartupTrace {
    enum Mode { OFF, BOUNDARY, RUNTIME, BEANS, PROPERTIES, FULL }
    static final String VERSION = "v3.5";
    private static Mode mode = Mode.FULL;
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
            // Run IDs are unique across phases. Append so a restarted process
            // cannot erase the fatal event of the previous PID in this run.
            try (FileOutputStream output = new FileOutputStream(journal, true)) {
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
    static boolean diagnostic() { return !run.equals("manual"); }
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

    static void requestSchema(Class<?> type) {
        try {
            JSONObject schema = new JSONObject();
            schema.put("class", type.getName());
            JSONArray fields = new JSONArray();
            for (Field field : type.getDeclaredFields()) {
                JSONObject item = new JSONObject();
                item.put("name", field.getName());
                item.put("type", field.getType().getName());
                item.put("static", Modifier.isStatic(field.getModifiers()));
                fields.put(item);
            }
            schema.put("fields", fields);
            JSONArray constructors = new JSONArray();
            for (Constructor<?> constructor : type.getDeclaredConstructors()) {
                JSONObject item = new JSONObject();
                JSONArray parameters = new JSONArray();
                for (Parameter parameter : constructor.getParameters()) {
                    JSONObject value = new JSONObject();
                    value.put("type", parameter.getType().getName());
                    value.put("name", parameter.getName());
                    value.put("name_present", parameter.isNamePresent());
                    parameters.put(value);
                }
                item.put("parameters", parameters);
                item.put("synthetic", constructor.isSynthetic());
                constructors.put(item);
            }
            schema.put("constructors", constructors);
            for (Annotation annotation : type.getDeclaredAnnotations()) {
                if (!annotation.annotationType().getName().equals("kotlin.Metadata")) continue;
                JSONObject metadata = new JSONObject();
                for (String key : new String[] {"k", "mv", "bv", "d1", "d2", "xs", "xi", "pn"}) {
                    try { metadata.put(key, JSONObject.wrap(annotation.annotationType().getDeclaredMethod(key).invoke(annotation))); }
                    catch (ReflectiveOperationException ignored) {}
                }
                schema.put("kotlin_metadata", metadata);
            }
            event("request-schema", schema.toString());
        } catch (Exception failure) { failure("request-schema-failed", failure); }
        catch (LinkageError failure) { failure("request-schema-linkage-failed", failure); }
    }
}
