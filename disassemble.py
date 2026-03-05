#!/usr/bin/env python3
"""
Atalla ISA Disassembler
Decodes 48-bit Atalla instructions from ELF binary
"""

def extract_bits(value, start, end):
    """Extract bits [start:end) from value (LSB = bit 0)"""
    mask = (1 << (end - start)) - 1
    return (value >> start) & mask

def bytes_to_int48(data):
    """Convert 6 bytes to 48-bit integer (little-endian)"""
    return int.from_bytes(data, byteorder='little')

def sign_extend(value, bits):
    """Sign extend a value from 'bits' width to full int"""
    sign_bit = 1 << (bits - 1)
    if value & sign_bit:
        return value - (1 << bits)
    return value

# Opcode mappings (from ISA spec)
OPCODES = {
    # R-type
    0b0000001: ("add_s", "R"),
    0b0000010: ("sub_s", "R"),
    0b0000011: ("mul_s", "R"),
    0b0000100: ("div_s", "R"),
    0b0000101: ("mod_s", "R"),
    0b0000110: ("or_s", "R"),
    0b0000111: ("and_s", "R"),
    0b0001000: ("xor_s", "R"),
    0b0001001: ("sll_s", "R"),
    0b0001010: ("srl_s", "R"),
    0b0001011: ("sra_s", "R"),
    0b0001100: ("slt_s", "R"),
    0b0001101: ("sltu_s", "R"),
    
    # BF16 R-type
    0b0001110: ("add_bf", "R"),
    0b0001111: ("sub_bf", "R"),
    0b0010000: ("mul_bf", "R"),
    0b0010001: ("div_bf", "R"),
    0b0010010: ("slt_bf", "R"),
    0b0010011: ("sltu_bf", "R"),
    0b0010100: ("stbf_s", "R"),
    0b0010101: ("bfts_s", "R"),
    
    # I-type
    0b0010110: ("addi_s", "I"),
    0b0010111: ("subi_s", "I"),
    0b0011000: ("muli_s", "I"),
    0b0011001: ("divi_s", "I"),
    0b0011010: ("modi_s", "I"),
    0b0011011: ("ori_s", "I"),
    0b0011100: ("andi_s", "I"),
    0b0011101: ("xori_s", "I"),
    0b0011110: ("slli_s", "I"),
    0b0011111: ("srli_s", "I"),
    0b0100000: ("srai_s", "I"),
    0b0100001: ("slti_s", "I"),
    0b0100010: ("sltui_s", "I"),
    
    # BR-type
    0b0100011: ("beq_s", "BR"),
    0b0100100: ("bne_s", "BR"),
    0b0100101: ("blt_s", "BR"),
    0b0100110: ("bge_s", "BR"),
    0b0100111: ("bgt_s", "BR"),
    0b0101000: ("ble_s", "BR"),
    
    # M-type
    0b0101001: ("lw_s", "M"),
    0b0101010: ("sw_s", "M"),
    
    # MI-type
    0b0101011: ("jal", "MI"),
    0b0101100: ("jalr", "I"),
    0b0101101: ("li_s", "MI"),
    
    # S-type
    0b0101111: ("nop", "S"),
    0b0110000: ("halt", "S"),

    # Vector VV
    0b0110010: ("add_vv", "VV"),
    0b0110011: ("sub_vv", "VV"),
    0b0110100: ("mul_vv", "VV"),
    0b0110101: ("div_vv", "VV"),
    # 0b0110110: ("and_vv", "VV"),
    # 0b0110111: ("or_vv", "VV"),
    0b0111000: ("shift_vs", "VS"),
    0b0111001: ("gemm_vv", "VV"),

    # Mask MVV
    0b0111010: ("mgt_mvv", "MVV"),
    0b0111011: ("mlt_mvv", "MVV"),
    0b0111100: ("meq_mvv", "MVV"),
    0b0111101: ("mneq_mvv", "MVV"),

    # Vector VI
    0b0111110: ("addi_vi", "VI"),
    0b0111111: ("subi_vi", "VI"),
    0b1000000: ("muli_vi", "VI"),
    0b1000001: ("divi_vi", "VI"),
    0b1000010: ("expi_vi", "VI"),
    0b1000011: ("sqrti_vi", "VI"),
    0b1000100: ("not_vi", "VI"),
    0b1000101: ("shift_vi", "VI"),
    0b1000110: ("lw_vi", "VI"),
    0b1000111: ("rsum_vi", "VI"),
    0b1001000: ("rmin_vi", "VI"),
    0b1001001: ("rmax_vi", "VI"),

    # Mask transfer
    0b1001011: ("mv_mts", "MTS"),
    0b1001100: ("mv_stm", "STM"),

    # Vector memory / vector-to-scalar
    0b1001101: ("vreg_ld", "VMEM"),
    0b1001110: ("vreg_st", "VMEM"),
    0b1001111: ("vmov_vts", "VTS"),

    # Vector VS
    0b1010000: ("add_vs", "VS"),
    0b1010001: ("sub_vs", "VS"),
    0b1010010: ("mul_vs", "VS"),
    0b1010011: ("div_vs", "VS"),

    # Mask MVS
    0b1010100: ("mgt_mvs", "MVS"),
    0b1010101: ("mlt_mvs", "MVS"),
    0b1010110: ("meq_mvs", "MVS"),
    0b1010111: ("mneq_mvs", "MVS"),

    # SDMA
    0b1011000: ("scpad_ld", "SDMA"),
    0b1011001: ("scpad_st", "SDMA"),

    # Special canonical encodings used by current backend
    0b0000000: ("all0s", "S"),
    0b1111111: ("all1", "S"),
}

def decode_one(mnemonic, fmt, insn_int, offset):
    """Decode one instruction interpretation."""
    if fmt == "R":
        # R-type: opcode rd rs1 rs2
        rd = extract_bits(insn_int, 7, 15)
        rs1 = extract_bits(insn_int, 15, 23)
        rs2 = extract_bits(insn_int, 23, 31)
        return f"{mnemonic:10s} x{rd}, x{rs1}, x{rs2}"

    elif fmt == "I":
        # I-type: opcode rd rs1 imm12
        rd = extract_bits(insn_int, 7, 15)
        rs1 = extract_bits(insn_int, 15, 23)
        imm12 = extract_bits(insn_int, 23, 35)
        imm12_signed = sign_extend(imm12, 12)
        return f"{mnemonic:10s} x{rd}, x{rs1}, {imm12_signed}"

    elif fmt == "BR":
        # BR-type: opcode incr_imm7 i1 rs1 rs2 imm9
        incr_imm7 = extract_bits(insn_int, 7, 14)
        i1 = extract_bits(insn_int, 14, 15)
        rs1 = extract_bits(insn_int, 15, 23)
        rs2 = extract_bits(insn_int, 23, 31)
        imm9 = extract_bits(insn_int, 31, 40)
        
        # Reconstruct imm10 = {imm9, i1}
        imm10 = (imm9 << 1) | i1
        imm10_signed = sign_extend(imm10, 10)

        # PC-relative offset in instruction words (6-byte instruction)
        byte_offset = imm10_signed * 6
        target = offset + byte_offset

        return f"{mnemonic:10s} x{rs1}, x{rs2}, 0x{target:X}  # offset={imm10_signed}"

    elif fmt == "M":
        # M-type: opcode rd rs1 imm12
        rd = extract_bits(insn_int, 7, 15)
        rs1 = extract_bits(insn_int, 15, 23)
        imm12 = extract_bits(insn_int, 23, 35)
        imm12_signed = sign_extend(imm12, 12)
        return f"{mnemonic:10s} x{rd}, {imm12_signed}(x{rs1})"

    elif fmt == "MI":
        # MI-type: opcode rd imm25
        rd = extract_bits(insn_int, 7, 15)
        imm25 = extract_bits(insn_int, 15, 40)

        if mnemonic == "jal":
            # PC-relative jump
            imm25_signed = sign_extend(imm25, 25)
            byte_offset = imm25_signed * 6
            target = offset + byte_offset
            return f"{mnemonic:10s} x{rd}, 0x{target:X}  # offset={imm25_signed}"
        else:
            # Load immediate
            return f"{mnemonic:10s} x{rd}, {imm25}"

    elif fmt == "S":
        # S-type: just opcode
        return f"{mnemonic:10s}"

    elif fmt == "VV":
        vd = extract_bits(insn_int, 7, 15)
        vs1 = extract_bits(insn_int, 15, 23)
        vs2 = extract_bits(insn_int, 23, 31)
        mask_reg = extract_bits(insn_int, 31, 35)
        return f"{mnemonic:10s} v{vd}, v{vs1}, v{vs2}, m{mask_reg}"

    elif fmt == "VS":
        vd = extract_bits(insn_int, 7, 15)
        vs1 = extract_bits(insn_int, 15, 23)
        rs1 = extract_bits(insn_int, 23, 31)
        mask_reg = extract_bits(insn_int, 31, 35)
        return f"{mnemonic:10s} v{vd}, v{vs1}, x{rs1}, m{mask_reg}"

    elif fmt == "VI":
        vd = extract_bits(insn_int, 7, 15)
        vs1 = extract_bits(insn_int, 15, 23)
        imm_hi8 = extract_bits(insn_int, 23, 31)
        imm_lo2 = extract_bits(insn_int, 40, 42)
        imm10 = (imm_hi8 << 2) | imm_lo2
        mask_reg = extract_bits(insn_int, 31, 35)
        return f"{mnemonic:10s} v{vd}, v{vs1}, {imm10}, m{mask_reg}"

    elif fmt == "VMEM":
        vd = extract_bits(insn_int, 7, 15)
        rs1 = extract_bits(insn_int, 15, 23)
        num_cols = extract_bits(insn_int, 23, 28)
        num_rows = extract_bits(insn_int, 28, 33)
        sid = extract_bits(insn_int, 33, 34)
        rc = extract_bits(insn_int, 34, 35)
        rc_id = extract_bits(insn_int, 35, 40)
        return f"{mnemonic:10s} v{vd}, x{rs1}, {num_cols}, {num_rows}, {rc}, {rc_id}, {sid}"

    elif fmt == "MVV":
        vmd = extract_bits(insn_int, 7, 15)
        vs1 = extract_bits(insn_int, 15, 23)
        vs2 = extract_bits(insn_int, 23, 31)
        mask_reg = extract_bits(insn_int, 31, 35)
        return f"{mnemonic:10s} m{vmd}, v{vs1}, v{vs2}, m{mask_reg}"

    elif fmt == "MVS":
        vmd = extract_bits(insn_int, 7, 15)
        vs1 = extract_bits(insn_int, 15, 23)
        rs1 = extract_bits(insn_int, 23, 31)
        mask_reg = extract_bits(insn_int, 31, 35)
        return f"{mnemonic:10s} m{vmd}, v{vs1}, x{rs1}, m{mask_reg}"

    elif fmt == "STM":
        vmd = extract_bits(insn_int, 7, 15)
        rs1 = extract_bits(insn_int, 15, 23)
        return f"{mnemonic:10s} m{vmd}, x{rs1}"

    elif fmt == "MTS":
        rd = extract_bits(insn_int, 7, 15)
        vms = extract_bits(insn_int, 15, 23)
        return f"{mnemonic:10s} x{rd}, m{vms}"

    elif fmt == "VTS":
        rd = extract_bits(insn_int, 7, 15)
        vs1 = extract_bits(insn_int, 15, 23)
        imm8 = extract_bits(insn_int, 23, 31)
        return f"{mnemonic:10s} x{rd}, v{vs1}, {imm8}"

    elif fmt == "SDMA":
        rs1_rd1 = extract_bits(insn_int, 7, 15)
        rs2 = extract_bits(insn_int, 15, 23)
        num_cols = extract_bits(insn_int, 23, 28)
        num_rows = extract_bits(insn_int, 28, 33)
        sid = extract_bits(insn_int, 33, 34)
        return f"{mnemonic:10s} x{rs2}, x{rs1_rd1}, {num_cols}, {num_rows}, {sid}"
    
    return f"UNIMPLEMENTED FORMAT: {fmt}"


def disassemble_instruction(insn_int, offset):
    """Disassemble a 48-bit Atalla instruction."""

    opcode = extract_bits(insn_int, 0, 7)
    entry = OPCODES.get(opcode)
    if entry is None:
        return f"UNKNOWN (opcode=0x{opcode:02X})"

    mnemonic, fmt = entry
    return decode_one(mnemonic, fmt, insn_int, offset)

def disassemble_elf(input_file, output_file):
    """Disassemble Atalla code from ELF file"""
    
    with open(input_file, 'rb') as f:
        data = f.read()
    
    with open(output_file, 'w') as out:
        out.write(f"Atalla Disassembly: {input_file}\n")
        out.write("=" * 100 + "\n\n")
        
        # Code section starts around 0x30, ends around 0xF0
        code_start = 0x34  # Adjust if needed
        code_end = 0xF0
        
        out.write("=== CODE SECTION ===\n\n")
        out.write(f"{'Offset':<10} {'Bytes':<30} {'Instruction'}\n")
        out.write("-" * 100 + "\n")
        
        offset = code_start
        while offset < code_end:
            if offset + 6 <= len(data):
                # Read 6 bytes (48 bits)
                insn_bytes = data[offset:offset+6]
                insn_int = bytes_to_int48(insn_bytes)
                
                # Format bytes
                hex_str = ' '.join(f'{b:02X}' for b in insn_bytes)
                
                # Disassemble
                disasm = disassemble_instruction(insn_int, offset)
                
                out.write(f"0x{offset:04X}    {hex_str:<28} {disasm}\n")
                
                offset += 6
            else:
                break
        
        out.write("\n" + "=" * 100 + "\n")

if __name__ == "__main__":
    disassemble_elf("output.elf", "disassembly.txt")
    print("Disassembly written to disassembly.txt")
