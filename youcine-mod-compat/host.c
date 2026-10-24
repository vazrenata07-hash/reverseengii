/* Executed with the actual x86/x86_64 process ISA, outside NativeBridge. */
#include <jni.h>
#include <errno.h>
#include <stdint.h>
#include <sys/mman.h>

JNIEXPORT jint JNICALL Java_org_yc_compat_NativePages_protect0(
        JNIEnv *env, jclass cls, jlong address, jlong length, jint flags) {
    (void)env; (void)cls;
    if (address < 0 || length < 0) return -EINVAL;
#if UINTPTR_MAX < UINT64_MAX
    if ((uint64_t)address > UINTPTR_MAX || (uint64_t)length > SIZE_MAX) return -EINVAL;
#endif
    int result = mprotect((void *)(uintptr_t)address, (size_t)length, flags);
    return result == 0 ? 0 : -errno;
}

JNIEXPORT jint JNICALL JNI_OnLoad(JavaVM *vm, void *reserved) {
    (void)vm; (void)reserved;
    return JNI_VERSION_1_6;
}
