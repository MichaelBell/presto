#!/usr/bin/env python3

# Expects a file in `objdump -t` format giving symbols from an elf
# as the first argument, or piped into stdin
import sys

import cxxfilt

if len(sys.argv) > 1:
    syms = open(sys.argv[1], "r")
else:
    syms = sys.stdin

sym_table = {}

while True:
    line = syms.readline()
    if not line or len(line) == 0:
        break
    if line[0] not in ('0', '1', '2'):
        continue

    fields = line.split()
    try:
        sym_len = int(fields[-2], base=16)
        if sym_len == 0:
            continue
        start_addr = int(fields[0], base=16)
        sym_name = cxxfilt.demangle(fields[-1])

        sym_table[start_addr] = (sym_name, sym_len)

    except IndexError:
        continue
    except ValueError:
        continue

print("constexpr int num_symbols = %d;" % (len(sym_table),))
print("constexpr SymbolLookup symbols[num_symbols] = {")
for addr, sym in sorted(sym_table.items()):
    print("    { 0x%08x, \"%s\"}," % (addr, sym[0]))
print("};")
