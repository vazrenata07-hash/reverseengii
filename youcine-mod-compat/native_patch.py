"""Size-preserving ELF import edits; no relocation/code addresses are moved."""
from io import BytesIO
import struct
from elftools.elf.elffile import ELFFile


def patch_native(data):
    result = bytearray(data)
    elf = ELFFile(BytesIO(data))
    symbols = elf.get_section_by_name('.dynsym')
    strings = elf.get_section(symbols['sh_link'])
    versions = elf.get_section_by_name('.gnu.version')
    dynamic = elf.get_section_by_name('.dynamic')
    changed = {}
    for original, replacement in [('mprotect', 'yc_mprot'), ('memcpy', 'yc_cpy')]:
        matches = [(i, s) for i, s in enumerate(symbols.iter_symbols()) if s.name == original]
        if len(matches) != 1 or matches[0][1]['st_shndx'] != 'SHN_UNDEF':
            raise ValueError('Unexpected native import: ' + original)
        index, symbol = matches[0]
        start = strings['sh_offset'] + symbol['st_name']
        old = original.encode() + b'\0'
        new = replacement.encode() + b'\0'
        if len(new) != len(old) or data[start:start+len(old)] != old:
            raise ValueError('Import edit must preserve ELF size')
        # No exported symbol is renamed. Relocations still reference the same
        # undefined dynsym index; resolve its new name as unversioned GLOBAL.
        result[start:start+len(old)] = new
        struct.pack_into('<H', result, versions['sh_offset'] + index*2, 1)
        changed[original] = {'symbol_index': index, 'name_offset': symbol['st_name'], 'replacement': replacement}
    # Both DT_FLAGS and DT_FLAGS_1 request BIND_NOW. Keep DT_FLAGS_1=NOW,
    # repurpose only the redundant DT_FLAGS slot for the guard dependency.
    tags = list(dynamic.iter_tags())
    if not any(t.entry.d_tag == 'DT_FLAGS_1' and t.entry.d_val & 1 for t in tags):
        raise ValueError('Missing independent NOW flag')
    slots = [i for i, t in enumerate(tags) if t.entry.d_tag == 'DT_FLAGS' and t.entry.d_val == 8]
    if len(slots) != 1:
        raise ValueError('Expected one redundant BIND_NOW slot')
    width = 16 if elf.elfclass == 64 else 8
    fmt = '<QQ' if elf.elfclass == 64 else '<II'
    struct.pack_into(fmt, result, dynamic['sh_offset'] + slots[0]*width,
                     1, changed['mprotect']['name_offset'])
    if len(result) != len(data):
        raise ValueError('ELF size changed')
    return bytes(result), {'imports': changed, 'needed': 'yc_mprot', 'size_preserved': True,
                           'machine_code_unchanged': True, 'bind_now_preserved': True}
