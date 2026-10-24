/* Imported only by the original wrapper. No process-wide libc interposition. */
#include <jni.h>
#include <android/log.h>
#include <errno.h>
#include <pthread.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <unistd.h>

#define EXPORT __attribute__((visibility("default")))
#define TAG "YCModCompat"
static JavaVM *vm;
static jclass pages;
static jmethodID protect_method;
static int translated;
static pthread_mutex_t copy_lock = PTHREAD_MUTEX_INITIALIZER;
struct region { uintptr_t lo, hi; int prot; };
static struct region guest_ro[64];
static unsigned guest_ro_count;

static int parse_map(const char *line, struct region *range) {
    unsigned long start, end;
    char flags[5];
    if (sscanf(line, "%lx-%lx %4s", &start, &end, flags) != 3) return 0;
    range->lo = start;
    range->hi = end;
    range->prot = (flags[0] == 'r' ? PROT_READ : 0)
                | (flags[1] == 'w' ? PROT_WRITE : 0)
                | (flags[2] == 'x' ? PROT_EXEC : 0);
    return 1;
}

static int mapping_for(uintptr_t start, uintptr_t end, struct region *result) {
    FILE *file = fopen("/proc/self/maps", "re");
    if (!file) return 0;
    char line[1024];
    int found = 0;
    while (fgets(line, sizeof line, file)) {
        struct region range;
        if (parse_map(line, &range) && start >= range.lo && end <= range.hi) {
            *result = range;
            found = 1;
            break;
        }
    }
    fclose(file);
    return found;
}

static void remember_guest_code(void) {
    FILE *file = fopen("/proc/self/maps", "re");
    if (!file) return;
    char line[1024];
    while (guest_ro_count < 64 && fgets(line, sizeof line, file)) {
        struct region range;
        if ((strstr(line, "/system/lib/arm/") || strstr(line, "/system/lib64/arm64/"))
                && parse_map(line, &range) && (range.prot & PROT_READ)
                && !(range.prot & PROT_WRITE)) guest_ro[guest_ro_count++] = range;
    }
    fclose(file);
}

static int host_protect(void *address, size_t length, int flags) {
    JNIEnv *env = NULL;
    int attached = 0;
    if ((*vm)->GetEnv(vm, (void **)&env, JNI_VERSION_1_6) != JNI_OK) {
        if ((*vm)->AttachCurrentThread(vm, &env, NULL) != JNI_OK) { errno = EIO; return -1; }
        attached = 1;
    }
    jint result = (*env)->CallStaticIntMethod(env, pages, protect_method,
            (jlong)(uintptr_t)address, (jlong)length, (jint)flags);
    if ((*env)->ExceptionCheck(env)) {
        (*env)->ExceptionDescribe(env);
        (*env)->ExceptionClear(env);
        result = -EIO;
    }
    if (attached) (*vm)->DetachCurrentThread(vm);
    if (result < 0) { errno = -result; return -1; }
    return 0;
}

/* mprotect is routed through the host's own Bionic JNI helper.
 * The translated ARM syscall shim cannot be relied on to change host mappings. */
EXPORT int yc_mprot(void *address, size_t length, int flags) {
    if (!translated) return mprotect(address, length, flags);
    return host_protect(address, length, flags);
}

/* Guard the exact readonly guest-code copy seen in the supplied tombstone.
 * Other memcpy calls remain plain memcpy. Page permissions are restored. */
EXPORT void *yc_cpy(void *destination, const void *source, size_t length) {
    if (!translated || !length) return memcpy(destination, source, length);
    uintptr_t start = (uintptr_t)destination, end = start + length;
    int guest = 0;
    for (unsigned i = 0; i < guest_ro_count; ++i) {
        if (start >= guest_ro[i].lo && start < guest_ro[i].hi) { guest = 1; break; }
    }
    if (!guest) return memcpy(destination, source, length);
    pthread_mutex_lock(&copy_lock);
    struct region range;
    if (end < start || !mapping_for(start, end, &range)) {
        __android_log_assert("valid guest code mapping", TAG, "v2 invalid copy destination");
    }
    if (range.prot & PROT_WRITE) {
        void *result = memcpy(destination, source, length);
        pthread_mutex_unlock(&copy_lock);
        return result;
    }
    uintptr_t page_size = (uintptr_t)sysconf(_SC_PAGESIZE);
    uintptr_t page = start & ~(page_size - 1);
    size_t count = (size_t)(((end + page_size - 1) & ~(page_size - 1)) - page);
    if (host_protect((void *)page, count, range.prot | PROT_WRITE) != 0) {
        __android_log_assert("host mprotect writable", TAG, "v2 refusing readonly hook copy errno=%d", errno);
    }
    void *result = memcpy(destination, source, length);
    __builtin___clear_cache((char *)destination, (char *)destination + length);
    if (host_protect((void *)page, count, range.prot) != 0) {
        __android_log_assert("host mprotect restore", TAG, "v2 cannot restore guest code page errno=%d", errno);
    }
    __android_log_print(ANDROID_LOG_INFO, TAG, "v2 guest hook copy addr=%p bytes=%zu; protection restored", destination, length);
    pthread_mutex_unlock(&copy_lock);
    return result;
}

JNIEXPORT jint JNICALL JNI_OnLoad(JavaVM *java_vm, void *reserved) {
    (void)reserved;
    JNIEnv *env;
    vm = java_vm;
    if ((*vm)->GetEnv(vm, (void **)&env, JNI_VERSION_1_6) != JNI_OK) return JNI_ERR;
    jclass local = (*env)->FindClass(env, "org/yc/compat/NativePages");
    if (!local) return JNI_ERR;
    pages = (*env)->NewGlobalRef(env, local);
    jmethodID mode = (*env)->GetStaticMethodID(env, local, "translated", "()Z");
    protect_method = (*env)->GetStaticMethodID(env, local, "protect", "(JJI)I");
    if (!pages || !mode || !protect_method) return JNI_ERR;
    translated = (*env)->CallStaticBooleanMethod(env, local, mode);
    (*env)->DeleteLocalRef(env, local);
    if ((*env)->ExceptionCheck(env)) return JNI_ERR;
    if (translated) remember_guest_code();
    __android_log_print(ANDROID_LOG_INFO, TAG, "v2 native guard ready translated=%d guest_ranges=%u", translated, guest_ro_count);
    return JNI_VERSION_1_6;
}
