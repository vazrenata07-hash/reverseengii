#include "art_symbols.hpp"
#include <elf.h>
#include <link.h>
#include <lzma.h>
#include <array>
#include <android/log.h>
#include <cerrno>
#include <cstdlib>
#include <cstring>
#include <fstream>
#include <limits>
#include <sstream>
#include <unistd.h>
#include <vector>

namespace {
constexpr size_t MAX_IMAGE = 256 * 1024 * 1024;
struct Location { std::string path; uintptr_t bias = 0; };
struct Mapping { uintptr_t start; uint64_t offset; std::string path; };

bool compatible(const ElfW(Ehdr)& header) {
    if (std::memcmp(header.e_ident, ELFMAG, SELFMAG) != 0
        || header.e_ident[EI_CLASS] != (sizeof(void*) == 8 ? ELFCLASS64 : ELFCLASS32)
        || header.e_ident[EI_DATA] != ELFDATA2LSB) return false;
#if defined(__aarch64__)
    return header.e_machine == EM_AARCH64;
#elif defined(__arm__)
    return header.e_machine == EM_ARM;
#elif defined(__x86_64__)
    return header.e_machine == EM_X86_64;
#elif defined(__i386__)
    return header.e_machine == EM_386;
#else
    return false;
#endif
}

std::vector<Mapping> art_mappings() {
    std::ifstream maps("/proc/self/maps");
    std::vector<Mapping> result;
    std::string line;
    while (std::getline(maps, line)) {
        std::istringstream fields(line);
        std::string addresses, access, offset, device, inode, path;
        if (!(fields >> addresses >> access >> offset >> device >> inode)) continue;
        std::getline(fields >> std::ws, path);
        size_t slash = path.rfind('/');
        if (path.empty() || path[0] != '/' || path.substr(slash == path.npos ? 0 : slash + 1) != "libart.so") continue;
        size_t dash = addresses.find('-');
        if (dash == addresses.npos) continue;
        std::string start = addresses.substr(0, dash);
        char* end = nullptr;
        errno = 0;
        uint64_t begin = std::strtoull(start.c_str(), &end, 16);
        if (errno || end != start.c_str() + start.size() || begin > std::numeric_limits<uintptr_t>::max()) continue;
        errno = 0;
        uint64_t file_offset = std::strtoull(offset.c_str(), &end, 16);
        if (errno || end != offset.c_str() + offset.size()) continue;
        result.push_back({static_cast<uintptr_t>(begin), file_offset, path});
    }
    return result;
}

int locate(dl_phdr_info* info, size_t, void* opaque) {
    std::string_view path = info->dlpi_name ? info->dlpi_name : "";
    size_t slash = path.rfind('/');
    if (path.substr(slash == path.npos ? 0 : slash + 1) != "libart.so") return 0;
    auto& location = *static_cast<Location*>(opaque);
    location.path = path;
    location.bias = info->dlpi_addr;
    return 1;
}

bool range(size_t size, uint64_t offset, uint64_t count) {
    return offset <= size && count <= size - offset;
}

template<class T> bool read(const std::vector<uint8_t>& bytes, uint64_t offset, T& value) {
    if (!range(bytes.size(), offset, sizeof(T))) return false;
    std::memcpy(&value, bytes.data() + offset, sizeof(T));
    return true;
}

std::string_view string_at(const std::vector<uint8_t>& bytes, const ElfW(Shdr)& strings, uint64_t offset) {
    if (!range(bytes.size(), strings.sh_offset, strings.sh_size) || offset >= strings.sh_size) return {};
    const char* start = reinterpret_cast<const char*>(bytes.data() + strings.sh_offset + offset);
    const char* end = static_cast<const char*>(std::memchr(start, 0, strings.sh_size - offset));
    return end ? std::string_view(start, end - start) : std::string_view{};
}

std::vector<uint8_t> inflate(const uint8_t* bytes, size_t count) {
    lzma_stream stream = LZMA_STREAM_INIT;
    if (lzma_stream_decoder(&stream, MAX_IMAGE, 0) != LZMA_OK) return {};
    stream.next_in = bytes;
    stream.avail_in = count;
    std::vector<uint8_t> output;
    std::array<uint8_t, 65536> block;
    for (;;) {
        stream.next_out = block.data();
        stream.avail_out = block.size();
        size_t previous = stream.avail_in;
        lzma_ret status = lzma_code(&stream, LZMA_FINISH);
        size_t written = block.size() - stream.avail_out;
        if (written > MAX_IMAGE - output.size()) { output.clear(); break; }
        output.insert(output.end(), block.begin(), block.begin() + written);
        if (status == LZMA_STREAM_END) break;
        if (status != LZMA_OK || (!written && previous == stream.avail_in)) { output.clear(); break; }
    }
    lzma_end(&stream);
    return output;
}

void parse(const std::vector<uint8_t>& bytes, uintptr_t bias,
           std::map<std::string, void*, std::less<>>& symbols, bool debugdata) {
    ElfW(Ehdr) header{};
    if (!read(bytes, 0, header) || !compatible(header) || header.e_shentsize != sizeof(ElfW(Shdr))
        || !header.e_shnum || !range(bytes.size(), header.e_shoff, uint64_t(header.e_shnum) * header.e_shentsize)) return;
    auto section = [&](size_t index, ElfW(Shdr)& value) {
        return index < header.e_shnum && read(bytes, header.e_shoff + index * header.e_shentsize, value);
    };
    ElfW(Shdr) names{};
    section(header.e_shstrndx, names);
    for (size_t i = 0; i < header.e_shnum; ++i) {
        ElfW(Shdr) table{};
        if (!section(i, table) || !range(bytes.size(), table.sh_offset, table.sh_size)) continue;
        if (table.sh_type == SHT_DYNSYM || table.sh_type == SHT_SYMTAB) {
            ElfW(Shdr) strings{};
            if (table.sh_entsize != sizeof(ElfW(Sym)) || !section(table.sh_link, strings)) continue;
            for (uint64_t at = 0; at + sizeof(ElfW(Sym)) <= table.sh_size; at += table.sh_entsize) {
                ElfW(Sym) symbol{};
                if (!read(bytes, table.sh_offset + at, symbol) || !symbol.st_value || symbol.st_shndx == SHN_UNDEF) continue;
                auto name = string_at(bytes, strings, symbol.st_name);
                if (name.empty() || symbol.st_value > std::numeric_limits<uintptr_t>::max() - bias) continue;
                uintptr_t address = symbol.st_shndx == SHN_ABS ? symbol.st_value : bias + symbol.st_value;
                symbols.emplace(std::string(name), reinterpret_cast<void*>(address));
            }
        } else if (debugdata && string_at(bytes, names, table.sh_name) == ".gnu_debugdata") {
            auto expanded = inflate(bytes.data() + table.sh_offset, table.sh_size);
            if (!expanded.empty()) parse(expanded, bias, symbols, false);
        }
    }
}
}

bool ArtSymbols::load() {
    Location location;
    dl_iterate_phdr(locate, &location);
    // Android linker namespaces can hide libart from dl_iterate_phdr. Maps
    // describe the actual process independently of that namespace filter.
    const auto mappings = art_mappings();
    std::vector<std::string> candidates;
    if (!location.path.empty()) candidates.push_back(location.path);
    for (const auto& mapping : mappings) {
        bool present = false;
        for (const auto& path : candidates) present |= path == mapping.path;
        if (!present) candidates.push_back(mapping.path);
    }
    __android_log_print(ANDROID_LOG_INFO, "YCLean", "ART discovery phdr=%d maps=%zu candidates=%zu vm_bits=%zu",
                        !location.path.empty(), mappings.size(), candidates.size(), sizeof(void*) * 8);
    for (const auto& path : candidates) {
        std::ifstream input(path, std::ios::binary | std::ios::ate);
        if (!input) {
            __android_log_print(ANDROID_LOG_WARN, "YCLean", "ART image open failed: %s", path.c_str());
            continue;
        }
        std::streamoff size = input.tellg();
        if (size <= 0 || static_cast<uint64_t>(size) > MAX_IMAGE) {
            __android_log_print(ANDROID_LOG_WARN, "YCLean", "ART image size rejected: %s", path.c_str());
            continue;
        }
        std::vector<uint8_t> bytes(static_cast<size_t>(size));
        input.seekg(0);
        if (!input.read(reinterpret_cast<char*>(bytes.data()), size)) {
            __android_log_print(ANDROID_LOG_WARN, "YCLean", "ART image read failed: %s", path.c_str());
            continue;
        }
        ElfW(Ehdr) header{};
        if (!read(bytes, 0, header) || !compatible(header)) {
            __android_log_print(ANDROID_LOG_WARN, "YCLean", "ART image ABI mismatch: %s class=%d machine=%d",
                                path.c_str(), header.e_ident[EI_CLASS], header.e_machine);
            continue;
        }
        uintptr_t bias = 0;
        bool located = false;
        const long page_size = sysconf(_SC_PAGESIZE);
        const uint64_t alignment = page_size > 0 ? static_cast<uint64_t>(page_size) : 4096;
        if (header.e_phentsize == sizeof(ElfW(Phdr))
            && range(bytes.size(), header.e_phoff, uint64_t(header.e_phnum) * header.e_phentsize)) {
            for (size_t i = 0; i < header.e_phnum && !located; ++i) {
                ElfW(Phdr) segment{};
                if (!read(bytes, header.e_phoff + i * header.e_phentsize, segment) || segment.p_type != PT_LOAD) continue;
                const uint64_t offset = segment.p_offset / alignment * alignment;
                const uint64_t address = segment.p_vaddr / alignment * alignment;
                for (const auto& mapping : mappings) {
                    if (mapping.path == path && mapping.offset == offset && mapping.start >= address) {
                        bias = mapping.start - address;
                        located = true;
                        break;
                    }
                }
            }
        }
        if (!located && path == location.path) { bias = location.bias; located = true; }
        if (!located) {
            __android_log_print(ANDROID_LOG_WARN, "YCLean", "ART load bias unavailable: %s", path.c_str());
            continue;
        }
        parse(bytes, bias, symbols_, true);
        __android_log_print(symbols_.empty() ? ANDROID_LOG_WARN : ANDROID_LOG_INFO, "YCLean",
                            "ART symbols parsed=%zu source=%s bias_source=%s sections=%u", symbols_.size(), path.c_str(),
                            path == location.path ? "phdr/maps" : "maps", header.e_shnum);
        if (!symbols_.empty()) return true;
    }
    return false;
}

void* ArtSymbols::exact(std::string_view name) const {
    auto found = symbols_.find(name);
    return found == symbols_.end() ? nullptr : found->second;
}

void* ArtSymbols::prefix(std::string_view name) const {
    auto found = symbols_.lower_bound(name);
    return found != symbols_.end() && std::string_view(found->first).substr(0, name.size()) == name
        ? found->second : nullptr;
}
