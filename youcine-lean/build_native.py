#!/usr/bin/env python3
"""Cross-compile four native helpers. Does not run the app or any tests."""
import os
import shutil
import subprocess
import patch_vendor
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BUILD = ROOT / "build"
VENDOR = BUILD / "vendor"
ABIS = ("armeabi-v7a", "arm64-v8a", "x86", "x86_64")
DEPENDENCIES = {
    "lsplant": ("https://github.com/LSPosed/LSPlant.git", "7217ac6f41e2bda549e4acb54e632abb03e5ccaf"),
    "dobby": ("https://github.com/jmpews/Dobby.git", "9c85e74f92eda36b99ddb0fddb17a9df2278a4d3"),
    "xz": ("https://github.com/tukaani-project/xz.git", "6e8732c5a317a349986a4078718f1d95b67072c5"),
}

def run(*args, cwd=ROOT):
    subprocess.run([str(arg) for arg in args], cwd=cwd, check=True)

def main():
    ndk = Path(os.environ["ANDROID_NDK_HOME"]).resolve()
    toolchain = ndk / "build/cmake/android.toolchain.cmake"
    if not toolchain.is_file():
        raise RuntimeError("ANDROID_NDK_HOME must point to an Android NDK installation")
    VENDOR.mkdir(parents=True, exist_ok=True)
    for name, (url, revision) in DEPENDENCIES.items():
        directory = VENDOR / name
        if not (directory / ".git").exists():
            directory.mkdir(exist_ok=True)
            run("git", "init", directory)
            run("git", "remote", "add", "origin", url, cwd=directory)
        run("git", "fetch", "--depth", "1", "origin", revision, cwd=directory)
        run("git", "checkout", "--detach", "FETCH_HEAD", cwd=directory)
        if name == "lsplant":
            run("git", "restore", "--", "lsplant/src/main/jni/include/utils/hook_helper.hpp", cwd=directory)
            patch_vendor.apply(directory)
            run("git", "-c", "url.https://github.com/.insteadOf=git@github.com:", "submodule", "update",
                "--init", "--recursive", "--depth", "1", "lsplant/src/main/jni/external/dex_builder", cwd=directory)
    strip = next((ndk / "toolchains/llvm/prebuilt").glob("*/bin/llvm-strip"))
    for abi in ABIS:
        directory = BUILD / "native" / abi
        run("cmake", "-S", ROOT / "native", "-B", directory, "-G", "Ninja",
            "-DCMAKE_TOOLCHAIN_FILE=" + str(toolchain), "-DANDROID_ABI=" + abi,
            "-DANDROID_PLATFORM=android-23", "-DANDROID_STL=c++_static", "-DCMAKE_BUILD_TYPE=Release",
            "-DYC_VENDOR=" + str(VENDOR))
        run("cmake", "--build", directory, "--target", "ycidentity", "--parallel", "4")
        output = BUILD / "native-libs" / abi / "libycidentity.so"
        output.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(directory / "libycidentity.so", output)
        run(strip, "--strip-unneeded", output)

if __name__ == "__main__":
    main()
