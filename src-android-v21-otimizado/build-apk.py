#!/usr/bin/env python3
"""Build Mint's five Java classes, replace classes3.dex + JS, and sign locally.

Linux build prerequisites: Python 3.10+ and Java/keytool (Java 21 used here).
Pinned Google Android build-tools/API28 and Eclipse ECJ are fetched into --tools-dir.
No runtime tests, benchmark, browser, device, or third-party site requests are run.
The signing key/password live only in --signing-dir; do not add them to Git.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import os
from pathlib import Path
import secrets
import shutil
import struct
import subprocess
import tempfile
import urllib.request
import zipfile

DOWNLOADS = (
    ('https://dl.google.com/android/repository/build-tools_r35_linux.zip',
     'build-tools_r35_linux.zip',
     'bd3a4966912eb8b30ed0d00b0cda6b6543b949d5ffe00bea54c04c81e1561d88'),
    ('https://dl.google.com/android/repository/platform-28_r06.zip',
     'platform-28_r06.zip',
     '8452dbbf9668a428abb243c4f02a943b7aa83af3cca627629a15c4c09f28e7bd'),
    ('https://repo.maven.apache.org/maven2/org/eclipse/jdt/ecj/3.40.0/ecj-3.40.0.jar',
     'ecj-3.40.0.jar',
     '05cc22a24e7982970f63a405fc6c820bc80b806f27f3c5a6236fc475f8f7152b'),
)
JAVA_FILES = ('Bootstrap.java', 'DataWiper.java', 'PageScripts.java',
              'ResetActivity.java', 'WagerStore.java')


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def run(command: list[str]) -> None:
    subprocess.run(command, check=True)


def prepare_tools(root: Path) -> tuple[Path, Path, Path]:
    root.mkdir(parents=True, exist_ok=True)

    def fetch(item: tuple[str, str, str]) -> None:
        url, name, expected = item
        path = root / name
        if not path.exists():
            partial = root / (name + '.partial')
            with urllib.request.urlopen(url, timeout=120) as response, partial.open('wb') as out:
                while data := response.read(1024 * 1024):
                    out.write(data)
            partial.rename(path)
        if sha(path.read_bytes()) != expected:
            raise RuntimeError('Tool archive SHA256 does not match pinned value: ' + name)

    with ThreadPoolExecutor(max_workers=3) as pool:
        list(pool.map(fetch, DOWNLOADS))
    for archive, directory in (('build-tools_r35_linux.zip', 'android-15'),
                               ('platform-28_r06.zip', 'android-9')):
        if not (root / directory).exists():
            with zipfile.ZipFile(root / archive) as zipped:
                zipped.extractall(root)
                for entry in zipped.infolist():
                    mode = (entry.external_attr >> 16) & 0o777
                    if mode:
                        (root / entry.filename).chmod(mode)
    return root / 'android-15', root / 'android-9/android.jar', root / 'ecj-3.40.0.jar'


def compile_sources(source: Path, work: Path, android: Path, ecj: Path, tools: Path) -> None:
    snapshot = work / 'java-sources'
    classes = work / 'classes'
    dex = work / 'dex'
    for directory in (snapshot, classes, dex):
        if directory.exists():
            shutil.rmtree(directory)
        directory.mkdir(parents=True)
    source_hashes = {}
    for name in JAVA_FILES:
        data = (source / name).read_bytes()
        source_hashes[name] = sha(data)
        (snapshot / name).write_bytes(data)
    run(['java', '-jar', str(ecj), '-source', '8', '-target', '8',
         '-encoding', 'UTF-8', '-bootclasspath', str(android),
         '-d', str(classes)] + [str(snapshot / name) for name in JAVA_FILES])
    compiled = sorted(classes.rglob('*.class'))
    if not compiled:
        raise RuntimeError('Compilation produced no class files.')
    run(['java', '-cp', str(tools / 'lib/d8.jar'), 'com.android.tools.r8.D8',
         '--min-api', '19', '--lib', str(android), '--output', str(dex)]
        + [str(path) for path in compiled])
    metadata = {
        'java_source_sha256': source_hashes,
        'class_files': [str(path.relative_to(classes)) for path in compiled],
        'replacement_dex_sha256': sha((dex / 'classes.dex').read_bytes()),
        'compiler': 'Eclipse ECJ 3.40.0, source/target 8',
        'dex_compiler': 'D8 from Google build-tools 35.0.0, min API 19',
        'android_compile_api': 28,
    }
    (work / 'compile.json').write_text(json.dumps(metadata, indent=2) + '\n')
    print('Compiled five Java source files into replacement classes3.dex.', flush=True)


def keypair(signing: Path) -> tuple[Path, Path, Path]:
    signing.mkdir(parents=True, exist_ok=True, mode=0o700)
    signing.chmod(0o700)
    key = signing / 'mint-optimized.p12'
    password = signing / 'mint-optimized.password'
    certificate = signing / 'mint-optimized.cer'
    if key.exists() != password.exists():
        raise RuntimeError('Signing key/password pair is incomplete; preserve and inspect it.')
    if not key.exists():
        fd = os.open(password, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, 'w', encoding='ascii') as stream:
            stream.write(secrets.token_urlsafe(36) + '\n')
        try:
            run(['keytool', '-genkeypair', '-noprompt', '-storetype', 'PKCS12',
                 '-keystore', str(key), '-storepass:file', str(password),
                 '-keypass:file', str(password), '-alias', 'mint-optimized',
                 '-keyalg', 'RSA', '-keysize', '3072', '-validity', '10000',
                 '-dname', 'CN=Mint Optimized Build'])
            key.chmod(0o600)
        except BaseException:
            if not key.exists():
                password.unlink(missing_ok=True)
            raise
    if not certificate.exists():
        run(['keytool', '-exportcert', '-keystore', str(key),
             '-storepass:file', str(password), '-alias', 'mint-optimized',
             '-file', str(certificate)])
    return key, password, certificate


def dex_classes(data: bytes) -> list[str]:
    def u32(offset: int) -> int:
        return struct.unpack_from('<I', data, offset)[0]
    strings = []
    for index in range(u32(56)):
        offset = u32(u32(60) + 4 * index)
        while data[offset] & 128:
            offset += 1
        offset += 1
        end = data.index(0, offset)
        strings.append(data[offset:end].decode('utf-8', errors='replace'))
    types = [strings[u32(u32(68) + 4 * index)] for index in range(u32(64))]
    return [types[u32(u32(100) + index * 32)] for index in range(u32(96))]


def package(base: Path, source: Path, work: Path, tools: Path,
            signing: Path, output: Path) -> None:
    if output == base:
        raise RuntimeError('Output must not overwrite the original APK.')
    if output.exists():
        raise RuntimeError('Output already exists; select a new output path.')
    replacement = (work / 'dex/classes.dex').read_bytes()
    payload = (source / 'mint-rebuilt-danill0.js').read_bytes()
    original_hashes = {}
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='package-', dir=work) as temporary:
        unsigned = Path(temporary) / 'unsigned.apk'
        aligned = Path(temporary) / 'aligned.apk'
        with zipfile.ZipFile(base) as original, zipfile.ZipFile(unsigned, 'w', allowZip64=False) as rebuilt:
            rebuilt.comment = original.comment
            for info in original.infolist():
                name = info.filename
                upper = name.upper()
                old_signature = upper.startswith('META-INF/') and (
                    upper.endswith(('.SF', '.RSA', '.DSA', '.EC'))
                    or upper == 'META-INF/MANIFEST.MF')
                if old_signature:
                    continue
                data = original.read(info)
                original_hashes[name] = sha(data)
                if name == 'classes3.dex':
                    data = replacement
                elif name == 'assets/mint-rebuilt.js':
                    data = payload
                rebuilt.writestr(info, data)
        key, password, certificate = keypair(signing)
        run([str(tools / 'zipalign'), '-p', '-f', '4', str(unsigned), str(aligned)])
        run([str(tools / 'apksigner'), 'sign', '--ks', str(key),
             '--ks-key-alias', 'mint-optimized', '--ks-pass', 'file:' + str(password),
             '--v4-signing-enabled', 'false',
             '--out', str(output), str(aligned)])
    # Build inventory records package contents and signer; it is not a runtime test.
    with zipfile.ZipFile(output) as built:
        changed = [name for name, digest in original_hashes.items()
                   if sha(built.read(name)) != digest]
    metadata = json.loads((work / 'compile.json').read_text())
    metadata.update({
        'output': str(output),
        'apk_sha256': sha(output.read_bytes()),
        'base_apk_sha256': sha(base.read_bytes()),
        'changed_payloads': changed,
        'javascript_sha256': sha(payload),
        'replacement_dex_classes': dex_classes(replacement),
        'preserved_manifest_sha256': original_hashes['AndroidManifest.xml'],
        'preserved_primary_dex_sha256': original_hashes['classes.dex'],
        'preserved_secondary_dex_sha256': original_hashes['classes2.dex'],
        'new_signer_certificate_sha256': sha(certificate.read_bytes()),
        'signing_key_location': str(key),
        'new_certificate_requires_reinstallation': True,
        'runtime_tests_executed': False,
        'benchmarks_executed': False,
    })
    (work / 'build.json').write_text(json.dumps(metadata, indent=2) + '\n')
    print(json.dumps(metadata, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-dir', type=Path, required=True)
    parser.add_argument('--base-apk', type=Path, required=True)
    parser.add_argument('--work-dir', type=Path, required=True)
    parser.add_argument('--tools-dir', type=Path, required=True)
    parser.add_argument('--signing-dir', type=Path)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--phase', choices=('all', 'compile', 'package'), default='all')
    args = parser.parse_args()
    if args.phase in ('all', 'package') and (args.output is None or args.signing_dir is None):
        parser.error('--output and --signing-dir are required for packaging.')
    source = args.source_dir.resolve()
    work = args.work_dir.resolve()
    work.mkdir(parents=True, exist_ok=True)
    tools, android, ecj = prepare_tools(args.tools_dir.resolve())
    if args.phase in ('all', 'compile'):
        compile_sources(source, work, android, ecj, tools)
    if args.phase in ('all', 'package'):
        package(args.base_apk.resolve(), source, work, tools,
                args.signing_dir.resolve(), args.output.resolve())


if __name__ == '__main__':
    main()
