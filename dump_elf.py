#!/usr/bin/env python3
"""
Better ELF dump with instruction highlighting
"""

def dump_elf_better(input_file, output_file):
    with open(input_file, 'rb') as f:
        data = f.read()
    
    with open(output_file, 'w') as out:
        out.write(f"ELF File: {input_file}\n")
        out.write(f"Total size: {len(data)} bytes (0x{len(data):X})\n")
        out.write("=" * 100 + "\n\n")
        
        # ELF Header
        out.write("=== ELF HEADER (first 52 bytes) ===\n")
        header = data[0:52]
        out.write(f"Magic: {' '.join(f'{b:02X}' for b in header[0:4])} = ")
        out.write(f"{''.join(chr(b) if 32 <= b < 127 else '.' for b in header[0:4])}\n")
        out.write(f"Class: {header[4]:02X} ({'32-bit' if header[4] == 1 else '64-bit'})\n")
        out.write(f"Machine Type: {header[18]:02X}{header[19]:02X} = {header[18] + (header[19] << 8)}\n")
        out.write(f"  (Should be 9999/0x270F for Atalla)\n\n")
        
        # Find the code section (around 0x30-0xF0 based on your dump)
        out.write("=== CODE SECTION (estimated 0x30-0xF0) ===\n")
        out.write("Showing as 5-byte (40-bit) Atalla instructions:\n\n")
        
        code_start = 0x34
        code_end = 0xF0
        
        for offset in range(code_start, code_end, 6):
            if offset + 6 <= len(data):
                insn_bytes = data[offset:offset+6]
                hex_str = ' '.join(f'{b:02X}' for b in insn_bytes)
                
                # Show as binary for bit-level analysis
                binary_str = ''.join(f'{b:08b}' for b in insn_bytes)
                
                out.write(f"Offset 0x{offset:04X}: {hex_str:20s}  |  {binary_str}\n")
        
        out.write("\n=== STRING TABLE (function/section names) ===\n")
        # Strings usually start around 0x180 in your dump
        string_section = data[0x180:0x210]
        # Split by null bytes
        strings = string_section.split(b'\x00')
        for s in strings:
            if s:  # Skip empty strings
                try:
                    decoded = s.decode('ascii')
                    out.write(f"  \"{decoded}\"\n")
                except:
                    out.write(f"  (binary data: {s.hex()})\n")
        
        out.write("\n=== FULL HEX DUMP ===\n")
        bytes_per_line = 16
        for offset in range(0, len(data), bytes_per_line):
            chunk = data[offset:offset + bytes_per_line]
            hex_offset = f"{offset:08X}"
            hex_bytes = ' '.join(f"{b:02X}" for b in chunk)
            hex_bytes = hex_bytes.ljust(bytes_per_line * 3 - 1)
            ascii_repr = ''.join(chr(b) if 32 <= b < 127 else '.' for b in chunk)
            out.write(f"{hex_offset}  {hex_bytes}  |{ascii_repr}|\n")

if __name__ == "__main__":
    dump_elf_better("output.elf", "output_detailed.txt")
    print("Detailed dump written to output_detailed.txt")