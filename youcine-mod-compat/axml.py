"""Binary manifest edits without rebuilding resources."""
import struct
NONE = 0xffffffff
ANDROID = "http://schemas.android.com/apk/res/android"

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
    pi = next(i for i, p in enumerate(parts) if p[0] == 1)
    attributes = {"multiArch": 0x0101048e, "use32bitAbi": 0x01010515}
    pool, strings = string_pool(parts[pi][2], attributes)
    parts[pi] = (1, struct.unpack_from("<H", pool, 2)[0], pool)
    mi = next(i for i, p in enumerate(parts) if p[0] == 0x180)
    kind, header, old_map = parts[mi]
    ids = list(struct.unpack_from("<%dI" % ((len(old_map)-header)//4), old_map, header))
    ids.extend([0] * max(0, max(strings.index(n) for n in attributes)+1-len(ids)))
    for name, value in attributes.items():
        index = strings.index(name)
        if ids[index] not in (0, value):
            raise ValueError("Conflicting resource ID: " + name)
        ids[index] = value
    resource_map = bytearray(old_map[:header])
    resource_map.extend(struct.pack("<%dI" % len(ids), *ids))
    struct.pack_into("<I", resource_map, 4, len(resource_map))
    parts[mi] = (kind, header, resource_map)
    namespace = strings.index(ANDROID)
    result = bytearray(manifest[:8])
    changed = 0
    for kind, header, raw in parts:
        part = bytearray(raw)
        if kind == 0x102 and strings[struct.unpack_from("<I", part, 20)[0]] == "application":
            start, size, count, id_i, class_i, style_i = struct.unpack_from("<6H", part, 24)
            if size != 20:
                raise ValueError("Unsupported attribute size")
            at = 16 + start
            entries = [(i+1, bytearray(part[at+i*size:at+(i+1)*size])) for i in range(count)]
            for name in attributes:
                name_i = strings.index(name)
                existing = next((entry for _, entry in entries if struct.unpack_from("<II", entry) == (namespace, name_i)), None)
                value = struct.pack("<IIIHBBI", namespace, name_i, NONE, 8, 0, 0x12, 0xffffffff)
                if existing is not None:
                    existing[:] = value
                else:
                    entries.append((0, bytearray(value)))
            def attr_order(item):
                ns, name = struct.unpack_from("<II", item[1])
                return ids[name] if name < len(ids) and ids[name] else 0
            entries.sort(key=attr_order)
            def remap(index):
                return next(i+1 for i, (old, _) in enumerate(entries) if old == index) if index else 0
            part = part[:at] + b"".join(entry for _, entry in entries) + part[at+count*size:]
            struct.pack_into("<4H", part, 28, len(entries), remap(id_i), remap(class_i), remap(style_i))
            struct.pack_into("<I", part, 4, len(part))
            changed += 1
        result.extend(part)
    if changed != 1:
        raise ValueError("Expected one application element")
    struct.pack_into("<I", result, 4, len(result))
    return bytes(result)

