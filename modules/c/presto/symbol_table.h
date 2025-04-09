#pragma once

namespace symbol_table
{
    struct SymbolLookup {
        uint32_t addr;
        const char* name;
    };

    #include "symbols.h"   
}
