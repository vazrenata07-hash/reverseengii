#include "art_symbols.hpp"
#include <android/log.h>
#include <jni.h>
#include <dobby.h>
#include <lsplant.hpp>
#include <memory>

namespace {
bool ready = false;
std::shared_ptr<ArtSymbols> symbols;
}

extern "C" JNIEXPORT jint JNICALL JNI_OnLoad(JavaVM* vm, void*) {
    JNIEnv* env = nullptr;
    if (vm->GetEnv(reinterpret_cast<void**>(&env), JNI_VERSION_1_6) != JNI_OK) return JNI_ERR;
#if defined(__x86_64__)
    constexpr const char* abi = "x86_64";
#elif defined(__i386__)
    constexpr const char* abi = "x86";
#elif defined(__aarch64__)
    constexpr const char* abi = "arm64-v8a";
#else
    constexpr const char* abi = "armeabi-v7a";
#endif
    __android_log_print(ANDROID_LOG_INFO, "YCLean", "ART helper loaded ABI=%s", abi);
    __android_log_print(ANDROID_LOG_INFO, "YCLean", "ART backup publication=acquire-release waiting callbacks");
    symbols = std::make_shared<ArtSymbols>();
    if (!symbols->load()) {
        __android_log_print(ANDROID_LOG_WARN, "YCLean", "ART symbols unavailable; identity rules disabled");
        return JNI_VERSION_1_6;
    }
    lsplant::InitInfo info;
    info.inline_hooker = [](void* target, void* replacement) -> void* {
        dobby_dummy_func_t backup = nullptr;
        int status = DobbyHook(target, reinterpret_cast<dobby_dummy_func_t>(replacement), &backup);
        if (status != 0 || !backup) {
            __android_log_print(ANDROID_LOG_ERROR, "YCLean", "ART inline backend failed status=%d backup_present=%d", status, backup != nullptr);
            return nullptr;
        }
        return reinterpret_cast<void*>(backup);
    };
    info.inline_unhooker = [](void* target) { return DobbyDestroy(target) == 0; };
    info.art_symbol_resolver = [resolver = symbols](std::string_view name) { return resolver->exact(name); };
    info.art_symbol_prefix_resolver = [resolver = symbols](std::string_view name) { return resolver->prefix(name); };
    info.generated_class_name = "YCIdentityHook_";
    info.generated_source_name = "YCLean";
    ready = lsplant::Init(env, info);
    if (env->ExceptionCheck()) { env->ExceptionDescribe(); env->ExceptionClear(); ready = false; }
    __android_log_print(ready ? ANDROID_LOG_INFO : ANDROID_LOG_WARN, "YCLean", "ART hook initialization ready=%d", ready);
    return JNI_VERSION_1_6;
}

extern "C" JNIEXPORT jboolean JNICALL Java_org_yc_lean_NativeRuntime_ready(JNIEnv*, jclass) {
    return ready ? JNI_TRUE : JNI_FALSE;
}

extern "C" JNIEXPORT jobject JNICALL Java_org_yc_lean_MethodHook_install0(
        JNIEnv* env, jobject hooker, jobject target, jobject callback) {
    if (!ready) return nullptr;
    return lsplant::Hook(env, target, hooker, callback);
}

extern "C" JNIEXPORT void JNICALL Java_org_yc_lean_NativeRuntime_log0(JNIEnv* env, jclass, jint priority, jstring message) {
    if (!message) return;
    const char* text = env->GetStringUTFChars(message, nullptr);
    if (!text) return;
    __android_log_write(priority, "YCLean", text);
    env->ReleaseStringUTFChars(message, text);
}

extern "C" JNIEXPORT jboolean JNICALL Java_org_yc_lean_EngineEntry_bind(JNIEnv* env, jclass, jclass runtime, jclass hook) {
    // The library belongs to the isolated loader. Bind app-owned declarations
    // explicitly rather than relying on that loader's native-library search.
    JNINativeMethod runtime_methods[] = {
        {const_cast<char*>("ready"), const_cast<char*>("()Z"), reinterpret_cast<void*>(Java_org_yc_lean_NativeRuntime_ready)},
        {const_cast<char*>("log0"), const_cast<char*>("(ILjava/lang/String;)V"), reinterpret_cast<void*>(Java_org_yc_lean_NativeRuntime_log0)}
    };
    JNINativeMethod hook_methods[] = {
        {const_cast<char*>("install0"), const_cast<char*>("(Ljava/lang/reflect/Member;Ljava/lang/reflect/Method;)Ljava/lang/reflect/Method;"), reinterpret_cast<void*>(Java_org_yc_lean_MethodHook_install0)}
    };
    if (env->RegisterNatives(runtime, runtime_methods, 2) != JNI_OK
        || env->RegisterNatives(hook, hook_methods, 1) != JNI_OK) return JNI_FALSE;
    __android_log_print(ANDROID_LOG_INFO, "YCLean", "ART native bindings installed ready=%d", ready);
    return ready ? JNI_TRUE : JNI_FALSE;
}
