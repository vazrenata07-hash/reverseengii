#pragma once
#include <map>
#include <string>
#include <string_view>

// Reads this process's ART ELF symbol tables, including .gnu_debugdata.
class ArtSymbols {
public:
    bool load();
    void* exact(std::string_view name) const;
    void* prefix(std::string_view name) const;
private:
    std::map<std::string, void*, std::less<>> symbols_;
};
