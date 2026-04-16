import re

MMAP_FILE = "atalla_layout.mmap"
DIS_FILE = "disassembly.txt"

# ----------------------------
# Parse memory map
# ----------------------------
def parse_mmap(path):
    text = open(path).read()

    regions = {}
    for name, base, size in re.findall(
        r"MEMORY\s+(\w+)\s+LOCATION=0x([0-9A-Fa-f]+)\s+SIZE=0x([0-9A-Fa-f]+)",
        text,
    ):
        base = int(base, 16)
        size = int(size, 16)
        regions[name] = (base, base + size)

    return regions

# ----------------------------
# Parse disassembly.txt file
# ----------------------------
def parse_disassembly(path):
    lines = open(path).read().splitlines()

    instructions = []
    symbols = {}

    in_code = False
    in_symbols = False

    for line in lines:
        if "=== CODE SECTION ===" in line:
            in_code = True
            continue
        if "=== SYMBOL TABLE ===" in line:
            in_symbols = True
            in_code = False
            continue

        if in_code:
            m = re.match(r"\s*(0x[0-9A-Fa-f]+)\s+(.+)", line)
            if m:
                offset = int(m.group(1), 16)
                instructions.append((offset, line.strip()))

        if in_symbols:
            m = re.match(r"(\w+)\s+(0x[0-9A-Fa-f]+)", line.strip())
            if m:
                name = m.group(1)
                addr = int(m.group(2), 16)
                symbols[addr] = name

    return instructions, symbols

# ----------------------------
# Extract relocation targets
# ----------------------------
def extract_target(line):
    matches = re.findall(r"0x([0-9A-Fa-f]+)", line)
    if not matches:
        return None
    return int(matches[-1], 16)

# ----------------------------
# Control flow test
# ----------------------------
def test_control_flow(instructions, symbols, code_base, code_end):
    print("\n=== CONTROL FLOW TEST ===")

    PASS = WARN = FAIL = 0

    for offset, line in instructions:
        if re.search(r"\b(jal|bgt_s|blt_s|beq_s|bne_s)\b", line):
            target = extract_target(line)
            if target is None:
                continue

            target_va = target + code_base
            pc_va = code_base + offset
            # This comment should stay here for critical debugging at a later point
            # print(f'PC_VA: 0x{pc_va:X}, Target 0x{target:X}')

            if not (code_base <= target_va < code_end):
                print(f"Failed {line} -> OUTSIDE CODE (0x{target_va:X})")
                FAIL += 1
            elif target_va in symbols:
                print(f"Correct {line} -> {symbols[target_va]} (0x{target_va:X})")
                PASS += 1
            else:
                print(f"Warning {line} -> 0x{target_va:X} (no symbol)")
                WARN += 1

    print(f"\nPASS={PASS} WARN={WARN} FAIL={FAIL}")

# ----------------------------
# Global relocation test
# ----------------------------
def test_globals(instructions, data_base, data_end, code_base):
    print("\n=== GLOBAL ADDRESS TEST ===")
    PASS = FAIL = 0
    i = 0
    while i < len(instructions) - 1:
        off1, l1 = instructions[i]
        off2, l2 = instructions[i + 1]

        # detect LUI + ADDI pair
        if "lui_s" in l1 and "addi_s" in l2:
            m1 = re.search(r"lui_s\s+x(\d+),\s*([0-9]+)", l1)
            m2 = re.search(r"addi_s\s+x(\d+),\s*x(\d+),\s*([0-9\-]+)", l2)

            if m1 and m2:
                reg_lui = int(m1.group(1))
                reg_addi_dst = int(m2.group(1))
                reg_addi_src = int(m2.group(2))

                # ensure it's the same register chain
                if reg_lui != reg_addi_dst or reg_lui != reg_addi_src:
                    i += 1
                    continue

                upper = int(m1.group(2))
                lower = int(m2.group(3))

                addr = (upper << 12) + lower

            if m1 and m2:
                reg = int(m1.group(1))
                upper = int(m1.group(2))
                lower = int(m2.group(1))

                addr = upper + lower

                if data_base <= addr < data_end:
                    PASS += 1
                elif code_base <= addr < data_end:
                    print(f"WRONG REGION (code used as global): 0x{addr:X}")
                    FAIL += 1
                else:
                    print(f"INVALID ADDRESS: 0x{addr:X}")
                    FAIL += 1

        i += 1

    print(f"\nPASS={PASS} FAIL={FAIL}")


# ----------------------------
# Symbol range sanity
# ----------------------------
def test_symbols(symbols, code_base, code_end, data_base, data_end):
    print("\n=== SYMBOL RANGE TEST ===")

    PASS = FAIL = 0

    for addr, name in symbols.items():
        if (code_base <= addr < code_end) or (data_base <= addr < data_end):
            PASS += 1
        else:
            print(f"Incorrect {name} at 0x{addr:X} outside all regions")
            FAIL += 1

    print(f"\nPASS={PASS} FAIL={FAIL}")


# ----------------------------
# Main
# ----------------------------
def main():
    print("Parsing memory map...")
    regions = parse_mmap(MMAP_FILE)

    code_base, code_end = regions["code"]
    data_base, data_end = regions["data"]

    print(f"code: 0x{code_base:X} - 0x{code_end:X}")
    print(f"data: 0x{data_base:X} - 0x{data_end:X}")

    print("\nParsing disassembly...")
    instructions, symbols = parse_disassembly(DIS_FILE)

    print(f"Found {len(instructions)} instructions")
    print(f"Found {len(symbols)} symbols")

    test_symbols(symbols, code_base, code_end, data_base, data_end)
    test_control_flow(instructions, symbols, code_base, code_end)
    test_globals(instructions, data_base, data_end, code_base)


if __name__ == "__main__":
    main()