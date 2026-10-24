#!/usr/bin/env python3
"""Compile ARM bridges and x86 host helpers, without running device code."""
import os
from pathlib import Path
import subprocess


def build(work):
    root = Path(__file__).parent
    ndk = Path(os.environ['ANDROID_NDK_HOME'])
    toolchains = list((ndk / 'toolchains/llvm/prebuilt').glob('linux-*/bin'))
    if len(toolchains) != 1:
        raise ValueError('ANDROID_NDK_HOME must identify the Linux NDK')
    native = work / 'native'
    for abi, target, name, source in [
            ('armeabi-v7a', 'armv7a-linux-androideabi23-clang', 'yc_mprot', 'guard.c'),
            ('arm64-v8a', 'aarch64-linux-android23-clang', 'yc_mprot', 'guard.c'),
            ('x86', 'i686-linux-android23-clang', 'yc_host', 'host.c'),
            ('x86_64', 'x86_64-linux-android23-clang', 'yc_host', 'host.c')]:
        directory = native / abi
        directory.mkdir(parents=True, exist_ok=True)
        subprocess.run([str(toolchains[0] / target), '-shared', '-fPIC', '-O2', '-g',
                        '-fvisibility=hidden', '-fno-builtin-memcpy', '-Wall', '-Wextra', '-Werror',
                        '-Wl,-soname,' + name, '-Wl,-z,now', '-Wl,-z,relro',
                        str(root / source), '-llog', '-o', str(directory / name)], check=True)
    return native
