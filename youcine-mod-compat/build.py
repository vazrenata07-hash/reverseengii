#!/usr/bin/env python3
"""Patch only the original third-party mod loader; never rewrite its module."""
import argparse
import copy
import hashlib
import json
import re
import shutil
import subprocess
import urllib.request
import zipfile
from pathlib import Path
from axml import patch_manifest
from native_patch import patch_native
from build_native import build as build_native

ROOT = Path(__file__).resolve().parent
ARTIFACT = 'youcine-tv-mod-compat-v2'

SOURCE_URL = "https://github.com/vazrenata07-hash/reverseengii/releases/download/2.0/YOUCINE.TV.MOD.apk"
SOURCE_SHA = "cf725dbfa652671f925a517ab9e42e8bafcbff8fdc6e0b600d573c3e87a8f51e"
TOOLS = {
    "apktool.jar": ("https://github.com/iBotPeaches/Apktool/releases/download/v3.0.3/apktool_3.0.3.jar", "dbf930b076c6b9be08d57c449cacefc3bdd6b71ebd59b3066fc0e1f5b14f9423"),
    "signer.jar": ("https://github.com/patrickfav/uber-apk-signer/releases/download/v1.3.0/uber-apk-signer-1.3.0.jar", "e1299fd6fcf4da527dd53735b56127e8ea922a321128123b9c32d619bba1d835"),
    "android-34.jar": ("https://raw.githubusercontent.com/Sable/android-platforms/master/android-34/android.jar", "6cea1df3efb77103ac3e2beb9bf4718964b0e0869ab16d39d29d5cbae1c147ad"),
    "r8.jar": ("https://dl.google.com/dl/android/maven2/com/android/tools/r8/8.6.27/r8-8.6.27.jar", "9007144728d47b5f11338c9292d5b74899b6579ad9ddc6942d419e3600c3d6d7"),
}
SIGNATURE = re.compile(r"META-INF/(MANIFEST\.MF|[^/]+\.(SF|RSA|DSA|EC))", re.I)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def obtain(path, url, expected):
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        with urllib.request.urlopen(url) as response, path.open("wb") as out:
            shutil.copyfileobj(response, out)
    if sha(path.read_bytes()) != expected:
        raise ValueError("SHA256 mismatch: " + str(path))


def patch_smali(decoded):
    candidates = [p for p in (decoded / "smali").rglob("*.smali") if "No HookRecord found" in p.read_text()]
    if len(candidates) != 1:
        raise ValueError("Expected one Pine engine")
    path = candidates[0]
    source = path.read_text()
    engine = re.search(r"^\.class .* (L[^;]+;)$", source, re.M).group(1)
    match = re.search(r"(\.method public static a\((L[^;]+;)Ljava/lang/Object;\[Ljava/lang/Object;\)Ljava/lang/Object;)\n.*?\.end method", source, re.S)
    if not match or "->syncMethodInfo" not in match[0]:
        raise ValueError("Unexpected original delegation method")
    record = match[2]
    record_path = decoded / "smali" / (record[1:-1] + ".smali")
    record_source = record_path.read_text()
    old = ".field public b:Ljava/lang/reflect/Method;"
    if record_source.count(old) != 1:
        raise ValueError("Unexpected backup field")
    record_path.write_text(record_source.replace(old, ".field public volatile b:Ljava/lang/reflect/Method;"))
    # hook0 installs the bridge before e() publishes the returned backup Method.
    # Acquire the volatile field before any native dereference. Keep original
    # delegation and exception behavior once ready; do not fabricate a result.
    body = f"""{match[1]}
    .locals 9
    move-object v3, p0
    invoke-static {{}}, Ljava/lang/System;->nanoTime()J
    move-result-wide v4
    const-wide v6, 0x12a05f200L
    add-long/2addr v4, v6
    :compat_wait
    iget-object p0, v3, {record}->b:Ljava/lang/reflect/Method;
    if-nez p0, :compat_ready
    invoke-static {{}}, Ljava/lang/System;->nanoTime()J
    move-result-wide v6
    cmp-long v8, v6, v4
    if-gez v8, :compat_failed
    const-wide/32 v6, 0xf4240
    invoke-static {{v6, v7}}, Ljava/util/concurrent/locks/LockSupport;->parkNanos(J)V
    goto :compat_wait
    :compat_failed
    new-instance v0, Ljava/lang/IllegalStateException;
    const-string v1, "ModCompat: original hook backup was not published"
    invoke-direct {{v0, v1}}, Ljava/lang/IllegalStateException;-><init>(Ljava/lang/String;)V
    throw v0
    :compat_ready
    iget-object v0, v3, {record}->a:Ljava/lang/reflect/Member;
    invoke-interface {{v0}}, Ljava/lang/reflect/Member;->getDeclaringClass()Ljava/lang/Class;
    move-result-object v1
    const/4 v2, 0x0
    invoke-static {{v0, p0, v2}}, {engine}->syncMethodInfo(Ljava/lang/reflect/Member;Ljava/lang/reflect/Method;Z)V
    invoke-virtual {{p0, p1, p2}}, Ljava/lang/reflect/Method;->invoke(Ljava/lang/Object;[Ljava/lang/Object;)Ljava/lang/Object;
    move-result-object p0
    invoke-virtual {{v1}}, Ljava/lang/Object;->getClass()Ljava/lang/Class;
    return-object p0
.end method"""
    path.write_text(source[:match.start()] + body + source[match.end():])
    return {"engine": str(path.relative_to(decoded)), "record": str(record_path.relative_to(decoded)),
            "backup_publication": "volatile + bounded acquire before native delegation", "wait_limit_ms": 5000}


def run(*args):
    subprocess.run([str(x) for x in args], check=True)


def add_guard_class(decoded, work, original, apktool):
    android = work / 'android-34.jar'
    r8 = work / 'r8.jar'
    for name, path in [('android-34.jar', android), ('r8.jar', r8)]:
        obtain(path, *TOOLS[name])
    classes, dex = work / 'guard-classes', work / 'guard-dex'
    classes.mkdir(exist_ok=True)
    dex.mkdir(exist_ok=True)
    run('java', 'com.sun.tools.javac.Main', '-source', '8', '-target', '8', '-Xlint:-options',
        '-bootclasspath', android, '-d', classes, ROOT / 'NativePages.java')
    run('java', '-cp', r8, 'com.android.tools.r8.D8', '--min-api', '23', '--lib', android,
        '--output', dex, *sorted(classes.rglob('*.class')))
    stub = work / 'guard-stub.apk'
    with zipfile.ZipFile(original) as source, zipfile.ZipFile(stub, 'w') as target:
        target.writestr('AndroidManifest.xml', source.read('AndroidManifest.xml'))
        target.write(dex / 'classes.dex', 'classes.dex')
    helper_decoded = work / 'guard-decoded'
    run('java', '-jar', apktool, 'd', '-f', '-r', '--no-assets', '-o', helper_decoded, stub)
    # Patch the single original System.load call before merging the helper,
    # so calls inside NativePages itself are never redirected recursively.
    old = 'Ljava/lang/System;->load(Ljava/lang/String;)V'
    matches = [p for p in (decoded / 'smali').rglob('*.smali') if old in p.read_text()]
    if len(matches) != 1 or matches[0].read_text().count(old) != 1:
        raise ValueError('Expected one original native loader call')
    path = matches[0]
    path.write_text(path.read_text().replace(old, 'Lorg/yc/compat/NativePages;->load(Ljava/lang/String;)V'))
    shutil.copytree(helper_decoded / 'smali/org/yc/compat', decoded / 'smali/org/yc/compat', dirs_exist_ok=True)
    return str(path.relative_to(decoded))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path)
    parser.add_argument("--apktool", type=Path)
    parser.add_argument("--signer", type=Path)
    parser.add_argument("--work", type=Path, default=Path("build"))
    parser.add_argument("--out", type=Path, default=Path("dist"))
    args = parser.parse_args()
    args.work.mkdir(parents=True, exist_ok=True)
    args.out.mkdir(parents=True, exist_ok=True)
    original = args.input or args.work / "original.apk"
    obtain(original, SOURCE_URL, SOURCE_SHA)
    apktool = args.apktool or args.work / "apktool.jar"
    signer = args.signer or args.work / "signer.jar"
    for name, path in (("apktool.jar", apktool), ("signer.jar", signer)):
        obtain(path, *TOOLS[name])
    decoded = args.work / "decoded"
    run("java", "-jar", apktool, "d", "-f", "-r", "--no-assets", "-o", decoded, original)
    changes = patch_smali(decoded)
    changes['native_loader'] = add_guard_class(decoded, args.work, original, apktool)
    native = build_native(args.work)
    rebuilt = args.work / "rebuilt.apk"
    run("java", "-jar", apktool, "b", decoded, "-o", rebuilt)
    with zipfile.ZipFile(rebuilt) as build:
        dex = build.read("classes.dex")
    unsigned = args.work / (ARTIFACT + '-unsigned.apk')
    replacements = {"classes.dex": dex}
    additions = {('assets/yc_compat/' + abi + '/yc_mprot'): (native / abi / 'yc_mprot').read_bytes()
                 for abi in ('armeabi-v7a', 'arm64-v8a')}
    additions.update({('assets/yc_compat/' + abi + '/yc_host'): (native / abi / 'yc_host').read_bytes()
                      for abi in ('x86', 'x86_64')})
    native_changes = {}
    with zipfile.ZipFile(original) as source:
        if len(source.namelist()) != len(set(source.namelist())):
            raise ValueError("Duplicate original ZIP entries")
        replacements["AndroidManifest.xml"] = patch_manifest(source.read("AndroidManifest.xml"))
        for name in ['@monxx_mod/arm.so', '@monxx_mod/arm64.so']:
            replacements[name], native_changes[name] = patch_native(source.read(name))
            native_changes[name]['original_sha256'] = sha(source.read(name))
            native_changes[name]['patched_sha256'] = sha(replacements[name])
        with zipfile.ZipFile(unsigned, "w") as target:
            for info in source.infolist():
                if not SIGNATURE.fullmatch(info.filename):
                    target.writestr(copy.copy(info), replacements.get(info.filename, source.read(info)))
            for name, data in additions.items():
                target.writestr(name, data, compress_type=zipfile.ZIP_DEFLATED)
    signed_dir = args.work / "signed"
    signed_dir.mkdir(exist_ok=True)
    run("java", "-jar", signer, "--apks", unsigned, "--out", signed_dir, "--allowResign")
    signed = signed_dir / (ARTIFACT + '-aligned-debugSigned.apk')
    output = args.out / (ARTIFACT + '.apk')
    shutil.copyfile(signed, output)
    # Packaging integrity only: no emulator, installation, launch or trial tests.
    with zipfile.ZipFile(original) as source, zipfile.ZipFile(output) as target:
        expected = {n for n in source.namelist() if not SIGNATURE.fullmatch(n)}
        actual = {n for n in target.namelist() if not SIGNATURE.fullmatch(n)}
        if expected | set(additions) != actual:
            raise ValueError("Unexpected added/removed APK entries")
        changed = sorted(n for n in expected if source.read(n) != target.read(n))
        if changed != sorted(replacements):
            raise ValueError("Unexpected modified APK contents: " + repr(changed))
        preserved = {n: sha(target.read(n)) for n in sorted(expected) if n == "res/dex/classes.dex" or n == "res/origin.apk" or n.startswith("lib/")}
        report = {"input_sha256": SOURCE_SHA, "output_sha256": sha(output.read_bytes()),
                  "modified_entries": changed, "unchanged_entries": len(expected)-len(changed),
                  "preserved_sha256": preserved, "loader_patch": changes,
                  "native_patch": native_changes,
                  "added_entries": {n: sha(target.read(n)) for n in additions},
                  "manifest": {"android:multiArch": True, "android:use32bitAbi": True},
                  "device_tests": "not run; performed by user"}
    (args.out / "CHANGESET.json").write_text(json.dumps(report, indent=2, ensure_ascii=False)+"\n")
    root = Path(__file__).parent
    with zipfile.ZipFile(args.out / (ARTIFACT + '-source.zip'), "w", zipfile.ZIP_DEFLATED) as archive:
        for file in sorted(root.iterdir()):
            if file.is_file():
                archive.write(file, "youcine-mod-compat/" + file.name)
    sums = "".join(sha(p.read_bytes()) + "  " + p.name + "\n" for p in sorted(args.out.iterdir()) if p.is_file() and p.name != "SHA256SUMS")
    (args.out / "SHA256SUMS").write_text(sums)
    print(json.dumps({"apk": str(output), "sha256": report["output_sha256"], "changed": changed, "preserved": report["unchanged_entries"]}))


if __name__ == "__main__":
    main()
