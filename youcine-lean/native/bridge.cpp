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
    symbols = std::make_shared<ArtSymbols>();
    if (!symbols->load()) {
        __android_log_print(ANDROID_LOG_WARN, "YCLean", "ART symbols unavailable; identity rules disabled");
        return JNI_VERSION_1_6;
    }
    lsplant::InitInfo info;
    info.inline_hooker = [](void* target, void* replacement) -> void* {
        dobby_dummy_func_t backup = nullptr;
        return DobbyHook(target, reinterpret_cast<dobby_dummy_func_t>(replacement), &backup) == 0
            ? reinterpret_cast<void*>(backup) : nullptr;
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
