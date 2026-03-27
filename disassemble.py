#!/usr/bin/env python3
"""
Atalla ISA Disassembler
Decodes Atalla instructions from ELF binary
"""

ISA_BYTES = 5

def extract_bits(value, start, end):
    """Extract bits [start:end) from value (LSB = bit 0)"""
    mask = (1 << (end - start)) - 1
    return (value >> start) & mask

def bytes_to_insn_int(data):
    """Convert ISA_BYTES bytes to an instruction integer (little-endian)."""
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
    0b0010001: ("rcp_bf", "R"),
    0b0010010: ("slt_bf", "R"),
    0b0010011: ("sqrt_bf", "R"),
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
    
    # MI/S-type
    0b0101110: ("lui_s", "MI"),

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
    0b0000000: ("nop", "S"),
    0b1111111: ("halt", "S"),
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

        # PC-relative offset in instruction words (ISA_BYTES-byte instruction)
        byte_offset = imm10_signed * ISA_BYTES
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
            byte_offset = imm25_signed * ISA_BYTES
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
        imm8 = extract_bits(insn_int, 23, 31)
        mask_reg = extract_bits(insn_int, 31, 35)
        return f"{mnemonic:10s} v{vd}, v{vs1}, {imm8}, m{mask_reg}"

    elif fmt == "VMEM":
        vd = extract_bits(insn_int, 7, 15)
        rs1 = extract_bits(insn_int, 15, 23)
        rs2 = extract_bits(insn_int, 23, 31)
        num_cols = extract_bits(insn_int, 31, 36)
        sid = extract_bits(insn_int, 36, 38)
        return f"{mnemonic:10s} v{vd}, x{rs1}, x{rs2}, {num_cols}, {sid}"

    elif fmt == "MVV":
        vmd = extract_bits(insn_int, 7, 11)
        vs1 = extract_bits(insn_int, 15, 23)
        vs2 = extract_bits(insn_int, 23, 31)
        mask_reg = extract_bits(insn_int, 31, 35)
        return f"{mnemonic:10s} m{vmd}, v{vs1}, v{vs2}, m{mask_reg}"

    elif fmt == "MVS":
        vmd = extract_bits(insn_int, 7, 11)
        vs1 = extract_bits(insn_int, 15, 23)
        rs1 = extract_bits(insn_int, 23, 31)
        mask_reg = extract_bits(insn_int, 31, 35)
        return f"{mnemonic:10s} m{vmd}, v{vs1}, x{rs1}, m{mask_reg}"

    elif fmt == "STM":
        rd = extract_bits(insn_int, 7, 15)
        vmd = extract_bits(insn_int, 15, 19)
        return f"{mnemonic:10s} m{vmd}, x{rd}"

    elif fmt == "MTS":
        vmd = extract_bits(insn_int, 7, 11)
        rs1 = extract_bits(insn_int, 15, 23)
        return f"{mnemonic:10s} x{rs1}, m{vmd}"

    elif fmt == "VTS":
        rd = extract_bits(insn_int, 7, 15)
        vs1 = extract_bits(insn_int, 15, 23)
        imm8 = extract_bits(insn_int, 23, 31)
        return f"{mnemonic:10s} x{rd}, v{vs1}, {imm8}"

    elif fmt == "SDMA":
        rs1_rd1 = extract_bits(insn_int, 7, 15)
        rs2 = extract_bits(insn_int, 15, 23)
        rs3 = extract_bits(insn_int, 23, 31)
        return f"{mnemonic:10s} x{rs1_rd1}, x{rs2}, x{rs3}"
    
    return f"UNIMPLEMENTED FORMAT: {fmt}"


def disassemble_instruction(insn_int, offset):
    """Disassemble one Atalla instruction."""

    opcode = extract_bits(insn_int, 0, 7)
    entry = OPCODES.get(opcode)
    if entry is None:
        return f"UNKNOWN (opcode=0x{opcode:02X})"

    mnemonic, fmt = entry
    return decode_one(mnemonic, fmt, insn_int, offset)


def get_code_bounds(data):
    """Infer code bounds from ELF metadata, preferring the .text section."""
    if len(data) < 52 or data[0:4] != b"\x7fELF":
        return 0, len(data)

    # ELF32 header fields used by current Atalla output.
    e_shoff = int.from_bytes(data[32:36], byteorder="little")
    e_ehsize = int.from_bytes(data[40:42], byteorder="little")
    e_shentsize = int.from_bytes(data[46:48], byteorder="little")
    e_shnum = int.from_bytes(data[48:50], byteorder="little")
    e_shstrndx = int.from_bytes(data[50:52], byteorder="little")

    # Try to locate an executable code section using section headers.
    if e_shoff and e_shentsize and e_shnum and e_shstrndx < e_shnum:
        sh_table_end = e_shoff + (e_shentsize * e_shnum)
        if sh_table_end <= len(data):
            shstr_hdr = e_shoff + (e_shstrndx * e_shentsize)
            shstr_off = int.from_bytes(data[shstr_hdr + 16:shstr_hdr + 20], byteorder="little")
            shstr_size = int.from_bytes(data[shstr_hdr + 20:shstr_hdr + 24], byteorder="little")

            if shstr_off + shstr_size <= len(data):
                shstr = data[shstr_off:shstr_off + shstr_size]

                for i in range(e_shnum):
                    sh = e_shoff + (i * e_shentsize)
                    name_off = int.from_bytes(data[sh:sh + 4], byteorder="little")
                    sec_type = int.from_bytes(data[sh + 4:sh + 8], byteorder="little")
                    sec_flags = int.from_bytes(data[sh + 8:sh + 12], byteorder="little")
                    sec_off = int.from_bytes(data[sh + 16:sh + 20], byteorder="little")
                    sec_size = int.from_bytes(data[sh + 20:sh + 24], byteorder="little")

                    if name_off >= len(shstr):
                        continue

                    end = shstr.find(b"\x00", name_off)
                    if end == -1:
                        continue

                    sec_name = shstr[name_off:end]
                    is_named_code = sec_name in (b".text", b"text", b"code")
                    is_exec_progbits = sec_type == 1 and (sec_flags & 0x4) != 0
                    if is_named_code or is_exec_progbits:
                        text_start = sec_off
                        text_end = sec_off + sec_size
                        if 0 <= text_start < text_end <= len(data):
                            return text_start, text_end

    code_start = e_ehsize if 0 < e_ehsize <= len(data) else 0
    code_end = e_shoff if code_start < e_shoff <= len(data) else len(data)

    if code_start >= code_end:
        return 0, len(data)

    return code_start, code_end

def disassemble_elf(input_file, output_file):
    """Disassemble Atalla code from ELF file"""
    
    with open(input_file, 'rb') as f:
        data = f.read()
    
    with open(output_file, 'w') as out:
        out.write(f"Atalla Disassembly: {input_file}\n")
        out.write("=" * 100 + "\n\n")
        
        code_start, code_end = get_code_bounds(data)
        
        out.write("=== CODE SECTION ===\n\n")
        out.write(f"{'Offset':<10} {'Bytes':<30} {'Instruction'}\n")
        out.write("-" * 100 + "\n")
        
        offset = code_start
        while offset < code_end:
            if offset + ISA_BYTES <= len(data):
                # Read one instruction worth of bytes.
                insn_bytes = data[offset:offset+ISA_BYTES]
                insn_int = bytes_to_insn_int(insn_bytes)
                
                # Format bytes
                hex_str = ' '.join(f'{b:02X}' for b in insn_bytes)
                
                # Disassemble
                disasm = disassemble_instruction(insn_int, offset)
                
                out.write(f"0x{offset:04X}    {hex_str:<28} {disasm}\n")
                
                offset += ISA_BYTES
            else:
                break
        
        out.write("\n" + "=" * 100 + "\n")

if __name__ == "__main__":
    disassemble_elf("output.elf", "disassembly.txt")
    print("Disassembly written to disassembly.txt")
