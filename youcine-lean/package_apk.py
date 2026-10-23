#!/usr/bin/env python3
"""Add the bootstrap DEX and provider without recompiling the application's resources."""
import argparse
import copy
import re
import struct
import zipfile
from pathlib import Path

NONE = 0xFFFFFFFF
ANDROID = "http://schemas.android.com/apk/res/android"
PROVIDER = "org.yc.lean.IdentityProvider"
AUTHORITY = "com.world.youcinetv.yc_lean.init"


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
    attrs = {"name": 0x01010003, "exported": 0x01010010,
             "authorities": 0x01010018, "initOrder": 0x0101001A}
    pool, strings = string_pool(parts[pool_index][2],
        [ANDROID, "provider", PROVIDER, AUTHORITY] + list(attrs))
    ids = {text: strings.index(text) for text in [ANDROID, "provider", PROVIDER, AUTHORITY] + list(attrs)}
    parts[pool_index] = (1, struct.unpack_from("<H", pool, 2)[0], pool)
    map_index = next(i for i, part in enumerate(parts) if part[0] == 0x180)
    old_map = parts[map_index][2]
    resources = list(struct.unpack_from("<%dI" % ((len(old_map) - 8) // 4), old_map, 8))
    resources += [0] * (len(strings) - len(resources))
    for text, resource in attrs.items():
        existing = resources[ids[text]]
        if existing not in (0, resource):
            raise ValueError("Conflicting Android attribute resource ID")
        resources[ids[text]] = resource
    resource_map = struct.pack("<HHI", 0x180, 8, 8 + len(resources) * 4)
    resource_map += struct.pack("<%dI" % len(resources), *resources)
    parts[map_index] = (0x180, 8, resource_map)

    def attribute(name, kind, value):
        return struct.pack("<IIIHBBI", ids[ANDROID], ids[name],
                           value if kind == 3 else NONE, 8, 0, kind, value)

    attributes = b"".join([
        attribute("name", 3, ids[PROVIDER]),
        attribute("exported", 0x12, 0),
        attribute("authorities", 3, ids[AUTHORITY]),
        attribute("initOrder", 0x10, 2147483647),
    ])
    start = struct.pack("<HHIII", 0x102, 16, 36 + len(attributes), 0, NONE)
    start += struct.pack("<II6H", NONE, ids["provider"], 20, 20, 4, 0, 0, 0) + attributes
    end = struct.pack("<HHIIIII", 0x103, 16, 24, 0, NONE, NONE, ids["provider"])
    result = bytearray(manifest[:8])
    inserted = False
    for kind, _, part in parts:
        if kind == 0x103 and strings[struct.unpack_from("<I", part, 20)[0]] == "application":
            if inserted:
                raise ValueError("More than one application element")
            result.extend(start + end)
            inserted = True
        result.extend(part)
    if not inserted:
        raise ValueError("Application element not found")
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
        if PROVIDER.encode() in source.read("AndroidManifest.xml"):
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
    print(args.output)


if __name__ == "__main__":
    main()
