#!/usr/bin/env python3
"""Compile, package and sign. Does not execute the application or run tests."""
import hashlib
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BUILD = ROOT / "build"
TOOLS = BUILD / "tools"
ARTIFACT = "yc-tv-1.15.4-lean-v2"
DOWNLOADS = {
    "original.apk": (
        "https://github.com/vazrenata07-hash/reverseengii/releases/download/2.01/yc_1.15.4_ycsite.apk",
        "5629c0dc0dc0b631f09bd21f81a5d671e64e6d516cb4a28a9b9fb45a2971b231"),
    "android-34.jar": (
        "https://raw.githubusercontent.com/Sable/android-platforms/master/android-34/android.jar",
        "6cea1df3efb77103ac3e2beb9bf4718964b0e0869ab16d39d29d5cbae1c147ad"),
    "r8.jar": (
        "https://dl.google.com/dl/android/maven2/com/android/tools/r8/8.6.27/r8-8.6.27.jar",
        "9007144728d47b5f11338c9292d5b74899b6579ad9ddc6942d419e3600c3d6d7"),
    "signer.jar": (
        "https://github.com/patrickfav/uber-apk-signer/releases/download/v1.3.0/uber-apk-signer-1.3.0.jar",
        "e1299fd6fcf4da527dd53735b56127e8ea922a321128123b9c32d619bba1d835"),
}


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def run(*args):
    subprocess.run([str(arg) for arg in args], check=True, cwd=ROOT)


def main():
    TOOLS.mkdir(parents=True, exist_ok=True)
    for name, (url, sha256) in DOWNLOADS.items():
        destination = TOOLS / name
        if not destination.exists() or digest(destination) != sha256:
            temporary = destination.with_suffix(".download")
            with urllib.request.urlopen(url, timeout=120) as source, temporary.open("wb") as output:
                shutil.copyfileobj(source, output)
            if digest(temporary) != sha256:
                temporary.unlink()
                raise RuntimeError("Unexpected SHA-256: " + name)
            temporary.replace(destination)

    classes = BUILD / "classes"
    dex = BUILD / "dex"
    for directory in (classes, dex):
        if directory.exists():
            shutil.rmtree(directory)
        directory.mkdir()
    sources = sorted((ROOT / "src").rglob("*.java"))
    run("java", "com.sun.tools.javac.Main", "-source", "8", "-target", "8",
        "-Xlint:-options", "-bootclasspath", TOOLS / "android-34.jar",
        "-d", classes, *sources)
    run("java", "-cp", TOOLS / "r8.jar", "com.android.tools.r8.D8",
        "--min-api", "19", "--lib", TOOLS / "android-34.jar", "--output", dex,
        *sorted(classes.rglob("*.class")))
    unsigned = BUILD / (ARTIFACT + "-unsigned.apk")
    run(sys.executable, ROOT / "package_apk.py", TOOLS / "original.apk",
        dex / "classes.dex", unsigned)
    run("java", "-jar", TOOLS / "signer.jar", "-a", unsigned, "--overwrite")
    # The signer selects the embedded development key and signs in place.
    destination = BUILD / (ARTIFACT + ".apk")
    shutil.copy2(unsigned, destination)
    (BUILD / "SHA256SUMS.txt").write_text(
        digest(destination) + "  " + destination.name + "\n", encoding="utf-8")
    print(destination)


if __name__ == "__main__":
    main()
