#!/usr/bin/env python3
"""Add the bootstrap DEX and early factory without recompiling resources."""
import argparse
import copy
import re
import struct
import zipfile
from pathlib import Path

NONE = 0xFFFFFFFF
ANDROID = "http://schemas.android.com/apk/res/android"
FACTORY = "org.yc.lean.EarlyFactory"


def chunks(data, offset=8):
    while offset < len(data):
        kind, header, size = struct.unpack_from("<HHI", data, offset)
        if header < 8 or size < header or offset + size > len(data):
            raise ValueError("Invalid Android XML chunk")
        yield kind, header, data[offset:offset + size]
        offset += size


def length(data, at, utf8):
    if utf8:
        value = data[at]
        return (((value & 127) << 8) | data[at + 1], at + 2) if value & 128 else (value, at + 1)
    value = struct.unpack_from("<H", data, at)[0]
    return (((value & 32767) << 16) | struct.unpack_from("<H", data, at + 2)[0], at + 4) if value & 32768 else (value, at + 2)


def string_pool(pool, additions):
    _, header, _ = struct.unpack_from("<HHI", pool)
    count, styles, flags, start, style_start = struct.unpack_from("<5I", pool, 8)
    utf8 = bool(flags & 0x100)
    offsets = list(struct.unpack_from("<%dI" % count, pool, header))
    strings = []
    for offset in offsets:
        at = start + offset
        size, at = length(pool, at, utf8)
        if utf8:
            size, at = length(pool, at, True)
        else:
            size *= 2
        strings.append(pool[at:at + size].decode("utf-8" if utf8 else "utf-16-le"))
    data = bytearray(pool[start:style_start or len(pool)])
    for text in additions:
        if text in strings:
            continue
        offsets.append(len(data))
        raw = text.encode("utf-8" if utf8 else "utf-16-le")
        units = len(text.encode("utf-16-le")) // 2
        if utf8:
            if max(units, len(raw)) > 127:
                raise ValueError("Added XML strings must fit one-byte UTF-8 lengths")
            data.extend(bytes([units, len(raw)]) + raw + b"\0")
        else:
            data.extend(struct.pack("<H", units) + raw + b"\0\0")
        strings.append(text)
    data.extend(b"\0" * (-len(data) % 4))
    style_offsets = pool[header + count * 4:header + (count + styles) * 4]
    style_data = pool[style_start:] if style_start else b""
    new_start = header + 4 * len(strings) + len(style_offsets)
    result = bytearray(pool[:header])
    struct.pack_into("<5I", result, 8, len(strings), styles, flags & ~1,
                     new_start, new_start + len(data) if style_start else 0)
    result.extend(struct.pack("<%dI" % len(offsets), *offsets))
    result.extend(style_offsets)
    result.extend(data)
    result.extend(style_data)
    struct.pack_into("<I", result, 4, len(result))
    return bytes(result), strings


def patch_manifest(manifest):
    parts = list(chunks(manifest))
    pool_index = next(i for i, part in enumerate(parts) if part[0] == 1)
    pool, strings = string_pool(parts[pool_index][2], [FACTORY])
    parts[pool_index] = (1, struct.unpack_from("<H", pool, 2)[0], pool)
    factory_index = strings.index(FACTORY)
    changed = False
    result = bytearray(manifest[:8])
    for kind, _, original in parts:
        part = bytearray(original)
        if kind == 0x102 and strings[struct.unpack_from("<I", part, 20)[0]] == "application":
            attribute_start, attribute_size, count = struct.unpack_from("<3H", part, 24)
            for index in range(count):
                at = 16 + attribute_start + index * attribute_size
                namespace, name = struct.unpack_from("<II", part, at)
                if namespace != NONE and strings[namespace] == ANDROID and strings[name] == "appComponentFactory":
                    struct.pack_into("<I", part, at + 8, factory_index)
                    part[at + 15] = 3
                    struct.pack_into("<I", part, at + 16, factory_index)
                    changed = True
        result.extend(part)
    if not changed:
        raise ValueError("Original appComponentFactory attribute not found")
    struct.pack_into("<I", result, 4, len(result))
    return bytes(result)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("original", type=Path)
    parser.add_argument("dex", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    if args.original.resolve() == args.output.resolve():
        raise ValueError("Output must differ from the original APK")
    with zipfile.ZipFile(args.original) as source:
        names = source.namelist()
        if len(names) != len(set(names)):
            raise ValueError("Duplicate APK entries are not supported")
        if FACTORY.encode("utf-16-le") in source.read("AndroidManifest.xml") or FACTORY.encode() in source.read("AndroidManifest.xml"):
            raise ValueError("Use the original APK, not a previous bootstrap build")
        indexes = [1]
        for name in names:
            match = re.fullmatch(r"classes(\d*)\.dex", name)
            if match: indexes.append(int(match[1] or 1))
        dex_name = "classes%d.dex" % (max(indexes) + 1)
        with zipfile.ZipFile(args.output, "w") as target:
            for info in source.infolist():
                if re.fullmatch(r"META-INF/(MANIFEST\.MF|[^/]+\.(SF|RSA|DSA|EC))", info.filename, re.I):
                    continue
                data = source.read(info)
                if info.filename == "AndroidManifest.xml":
                    data = patch_manifest(data)
                target.writestr(copy.copy(info), data)
            target.writestr(dex_name, args.dex.read_bytes(), compress_type=zipfile.ZIP_DEFLATED)
            target.writestr("assets/yc_original_1_15_4.apk", args.original.read_bytes(),
                            compress_type=zipfile.ZIP_STORED)
    print(args.output)


if __name__ == "__main__":
    main()
