#!/usr/bin/env python3
"""Apply the reviewed backup-publication fix to the pinned LSPlant header."""
import hashlib
from pathlib import Path

ORIGINAL_SHA256 = "2a345fad7a3f64cfa458039a40b437d45403e0ed6ac75faa842c6bef1b1effea"

def apply(directory):
    header = Path(directory) / "lsplant/src/main/jni/include/utils/hook_helper.hpp"
    raw = header.read_bytes()
    if hashlib.sha256(raw).hexdigest() != ORIGINAL_SHA256:
        raise RuntimeError("Pinned LSPlant hook helper differs; publication patch refused")
    source = raw.decode("utf-8")
    source = source.replace('#include <concepts>', '#include <concepts>\n#include "yc_ready_backup.hpp"', 1)
    source = source.replace('inline static Ret (*backup)(Args...) = nullptr;',
                            'inline static YCReadyBackup<Ret (*)(Args...)> backup;', 1)
    source = source.replace('inline static MemberFunction<Ret(Args...)> backup;',
                            'inline static YCReadyBackup<MemberFunction<Ret(Args...)>> backup;', 1)
    start = source.index('template <HookerType T>\ninline static bool HookSymNoHandle')
    end = source.index('\ntemplate <HookerType T>\ninline static bool HookSym(', start)
    replacement = '''template <HookerType T>
inline static bool HookSymNoHandle(const HookHandler &handler, void *original, T &arg) {
    if (!original) return false;
    using Backup = typename std::remove_cvref_t<decltype(arg.backup)>::ValueType;
    void *address = handler.inline_hooker(original, reinterpret_cast<void *>(arg.replace));
    if (!address) {
        arg.backup.fail();
        return false;
    }
    if constexpr (is_instance_v<Backup, MemberFunction>) {
        arg.backup.publish(Backup(reinterpret_cast<typename Backup::FunType>(address)));
    } else {
        arg.backup.publish(reinterpret_cast<Backup>(address));
    }
    return true;
}
'''
    header.write_text(source[:start] + replacement + source[end:], encoding="utf-8")
    print("LSPlant: applied synchronized backup publication")
