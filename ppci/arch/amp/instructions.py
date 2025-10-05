from ..isa import Isa
from ..encoding import Instruction, Operand, Syntax
from .tokens import *
from .registers import (
    AtallaRegister,
    R0,
    R13, R12, R10, R11, R9, R7, R6, R5, R4, R3,
    FP,
)
from ..generic_instructions import (
    Alignment,
    ArtificialInstruction,
    Global,
    RegisterUseDef,
    SectionInstruction,
)
from .relocations import BImm12Relocation, BImm20Relocation
import struct

isa = Isa()

isa.register_relocation(BImm12Relocation)
isa.register_relocation(BImm20Relocation)

class AtallaRInstruction(Instruction):
    tokens = [AtallaRToken]
    isa = isa

def make_r(mnemonic, opcode):
    rd = Operand("rd", AtallaRegister, write=True)
    rn = Operand("rn", AtallaRegister, read=True)
    rm = Operand("rm", AtallaRegister, read=True)
    syntax = Syntax([mnemonic, " ", rd, ",", " ", rn, ",", " ", rm])
    tokens = [AtallaRToken]
    patterns = {
        "opcode": opcode,
        "rd1": rd,
        "rs1": rn,
        "rs2": rm,
        "imm12": 0b000000000000
        # could be not zeros (should probably ask)
        # what does RESERVED mean?
        # Need schdImm?
    }
    members = {
        "syntax": syntax,
        "rd": rd,
        "rn": rn,
        "rm": rm,
        "patterns": patterns,
        "tokens": tokens,
        "opcode": opcode,
    }
    name = mnemonic.title() + "R"
    return type(name, (AtallaRInstruction,), members)

# R-types:
Adds = make_r("add_s", 0b0000001)
Subs = make_r("sub_s", 0b0000010)
Muls = make_r("mul_s", 0b0000011)
Divs = make_r("div_s", 0b0000100)
Mods = make_r("mod_s", 0b0000101)
Ors = make_r("or_s", 0b0000110)
Ands = make_r("and_s", 0b0000111)
Xors = make_r("xor_s", 0b0001000)
Slls = make_r("sll_s", 0b0001001)
Srls = make_r("srl_s", 0b0001010)
Sras = make_r("sra_s", 0b0001011)
Slts = make_r("slt_s", 0b0001100)
Sltus = make_r("sltu_s", 0b0001101)

class AtallaIInstruction(Instruction):
    tokens = [AtallaIToken]
    isa = isa

def make_i(mnemonic, opcode):
    rd = Operand("rd", AtallaRegister, write=True)
    rs1 = Operand("rs1", AtallaRegister, read=True)
    offset = Operand("offset", int)
    fprel = False
    syntax = Syntax([mnemonic, " ", rd, ",", " ", rs1, ",", " ", offset])
    tokens = [AtallaIToken]
    patterns = {
        "opcode": opcode,
        "rd": rd,
        "rs1": rs1,
        "imm12": offset
    }
    members = {
        "syntax": syntax,
        "fprel": fprel,
        "rd": rd,
        "rs1": rs1,
        "offset": offset,
        "opcode": opcode,
        "patterns": patterns,
        "tokens" : tokens
    }
    return type(mnemonic + "_ins", (AtallaIInstruction,), members)

# I-types:
Addis = make_i("addi_s", 0b0010010)
Subis = make_i("subi_s", 0b0010011)
Mulis = make_i("mulis_s", 0b0010100)
Divis = make_i("divi_s", 0b0010101)
Modis = make_i("modi_s", 0b0010110)
Oris = make_i("ori_s", 0b0010111)
Andis = make_i("andi_s", 0b0011000)
Xoris = make_i("xori_s", 0b0011001)
Sllis = make_i("sllis_s", 0b0011010)
Srlis = make_i("srlis_s", 0b0011011)
Srais = make_i("srai_s", 0b0011100)
Sltis = make_i("slti_s", 0b0011101)
Sltuis = make_i("sltui_s", 0b0011110)


class AtallaBRInstruction(Instruction):
    tokens = [AtallaBRToken]
    isa = isa

    def relocations(self):
        return [BImm12Relocation(self.target)]


def make_br(mnemonic, opcode):
    rs1 = Operand("rs1", AtallaRegister, read=True)
    rs2 = Operand("rs2", AtallaRegister, read=True)
    target = Operand("offset", str)
    fprel = False
    syntax = Syntax([mnemonic, " ", rs1, ",", " ", rs2, ",", " ", target])
    tokens = [AtallaBRToken]
    patterns = {
        "opcode": opcode,
        "rs1": rs1,
        "rs2": rs2,
        "target": target
    }
    members = {
        "syntax": syntax,
        "rs1": rs1,
        "rs2": rs2,
        "target": target,
        "opcode": opcode,
        "patterns": patterns,
        "tokens" : tokens
    }
    return type(mnemonic + "_ins", (AtallaBRInstruction,), members)

# Branch instructions (BR-types):
Beqs = make_br("beq_s", 0b0001110)
Bnes = make_br("bne_s", 0b0001111)
Blts = make_br("blt_s", 0b0010000)
Bges = make_br("bge_s", 0b0010001)

class AtallaMInstruction(Instruction):
    tokens = [AtallaMToken]
    isa = isa

def make_m(mnemonic, opcode):
    rd = Operand("rd", AtallaRegister, write=True)
    rs1 = Operand("rs1", AtallaRegister, read=True)
    imm12 = Operand("imm12", int)
    fprel = False
    syntax = Syntax([mnemonic, " ", rd, ",", " ", imm12, "(", rs1, ")"])
    tokens = [AtallaMToken]
    patterns = {
        "opcode": opcode,
        "rd": rd,
        "rs1": rs1,
        "imm12": imm12
    }
    members = {
        "syntax": syntax,
        "fprel": fprel,
        "rd": rd,
        "rs1": rs1,
        "imm12": imm12,
        "opcode": opcode,
        "patterns": patterns,
        "tokens" : tokens
    }
    return type(mnemonic + "_ins", (AtallaIInstruction,), members)

Lws = make_m("lw_s", 0b0011111)
Sws = make_m("sw_s", 0b0100000)

class AtallaMIInstruction(Instruction):
    tokens = [AtallaMIToken]
    isa = isa

def make_mi(mnemonic, opcode):
    rd = Operand("rd", AtallaRegister, write=True)
    imm = Operand("imm", int)
    syntax = Syntax([mnemonic, " ", rd, ",", " ", imm])
    tokens = [AtallaMIToken]
    patterns = {
        "opcode": opcode,
        "rd": rd,
        "imm": imm
    }
    members = {
        "syntax": syntax,
        "rd": rd,
        "imm": imm,
        "patterns": patterns,
        "tokens": tokens,
        "opcode": opcode,
    }
    return type(mnemonic + "_ins", (AtallaMIInstruction,), members)

Lis = make_mi("li_s", 0b0100001)

class AtallaNOPInstruction:
    tokens = [AtallaNOPToken]
    isa = isa

def make_nop(mnemonic, opcode):
    syntax = Syntax([mnemonic])
    tokens = [AtallaNOPToken]
    patterns = {
        "opcode": opcode
    }
    members = {
        "syntax": syntax,
        "patterns": patterns,
        "tokens": tokens,
        "opcode": opcode,
    }
    return type(mnemonic + "_ins", (AtallaNOPInstruction,), members)

class AtallaJInstruction(Instruction):
    tokens = [AtallaJToken]
    isa = isa

class Bl(AtallaJInstruction):
    target = Operand("target", str)
    rd = Operand("rd", AtallaRegister, write=True)
    syntax = Syntax(["jal", " ", rd, ",", " ", target])

    def encode(self):
        tokens = self.get_tokens()
        tokens[0][57:64] = 0b0100010
        tokens[0][49:57] = self.rd.num
        return tokens[0].encode()

    def relocations(self):
        return [BImm20Relocation(self.target)]

class Blr(AtallaJInstruction):
    rd = Operand("rd", AtallaRegister, write=True)
    rs1 = Operand("rs1", AtallaRegister, read=True)
    offset = Operand("offset", int)
    syntax = Syntax(["jalr", " ", rd, ",", rs1, ",", " ", offset])

    def encode(self):
        tokens = self.get_tokens()
        tokens[0][57:64] = 0b0100011
        tokens[0][49:57] = self.rd.num
        tokens[0][41:49] = self.rs1.num
        tokens[0][5:25] = self.offset #TODO: fix bitspec
        return tokens[0].encode()

Halt = make_nop("halt", 0b1111111)

class PseudoAtallaInstruction(ArtificialInstruction):
    isa = isa
    pass
class Align(PseudoAtallaInstruction):
    imm = Operand("imm", int)
    syntax = Syntax([".", "align", " ", imm])

    def render(self):
        self.rep = self.syntax.render(self)
        yield Alignment(self.imm, self.rep)

class Section(PseudoAtallaInstruction):
    sec = Operand("sec", str)
    syntax = Syntax([".", "section", " ", sec])

    def render(self):
        self.rep = self.syntax.render(self)
        yield SectionInstruction(self.sec, self.rep)

@isa.pattern("stm", "MOVI16(reg)", size=2)
@isa.pattern("stm", "MOVU16(reg)", size=2)
@isa.pattern("stm", "MOVI32(reg)", size=2)
@isa.pattern("stm", "MOVU32(reg)", size=2)
@isa.pattern("stm", "MOVF32(reg)", size=10)
@isa.pattern("stm", "MOVF64(reg)", size=10)
def pattern_mov32(context, tree, c0):
    context.move(tree.value, c0)
    return tree.value


@isa.pattern("stm", "MOVU8(reg)", size=2)
@isa.pattern("stm", "MOVI8(reg)", size=2)
def pattern_movi8(context, tree, c0):
    context.move(tree.value, c0)
    return tree.value


@isa.pattern("stm", "JMP", size=4)
def pattern_jmp(context, tree):
    reg = R0
    tgt = tree.value
    context.emit(Bl(reg, tgt.name, jumps=[tgt]))


@isa.pattern("stm", "MOVB(reg, reg)", size=40)
def pattern_movb(context, tree, c0, c1):
    # Emit memcpy
    dst = c0
    src = c1
    tmp = context.new_reg(AtallaRegister)
    size = tree.value
    for instruction in context.arch.gen_riscv_memcpy(dst, src, tmp, size):
        context.emit(instruction)


@isa.pattern("reg", "REGI32", size=0)
@isa.pattern("reg", "REGI16", size=0)
@isa.pattern("reg", "REGI8", size=0)
@isa.pattern("reg", "REGU32", size=0)
@isa.pattern("reg", "REGF32", size=10)
@isa.pattern("reg", "REGF64", size=10)
@isa.pattern("reg", "REGU16", size=0)
@isa.pattern("reg", "REGU8", size=0)
def pattern_reg(context, tree):
    return tree.value


@isa.pattern("reg", "U32TOU16(reg)", size=0)
@isa.pattern("reg", "U32TOI16(reg)", size=0)
@isa.pattern("reg", "I32TOI16(reg)", size=0)
@isa.pattern("reg", "I32TOU16(reg)", size=0)
@isa.pattern("reg", "U16TOU8(reg)", size=0)
@isa.pattern("reg", "U16TOI8(reg)", size=0)
@isa.pattern("reg", "I16TOI8(reg)", size=0)
@isa.pattern("reg", "I16TOU8(reg)", size=0)
@isa.pattern("reg", "F32TOF64(reg)", size=10)
@isa.pattern("reg", "F64TOF32(reg)", size=10)
def pattern_i32_to_i32(context, tree, c0):
    return c0


@isa.pattern("reg", "I8TOI16(reg)", size=4)
@isa.pattern("reg", "I8TOI32(reg)", size=4)
def pattern_i8_to_i32(context, tree, c0):
    context.emit(Sllis(c0, c0, 24))
    context.emit(Srais(c0, c0, 24))
    return c0


@isa.pattern("reg", "I16TOI32(reg)", size=4)
def pattern_i16_to_i32(context, tree, c0):
    context.emit(Sllis(c0, c0, 16))
    context.emit(Srais(c0, c0, 16))
    return c0


@isa.pattern("reg", "I8TOU16(reg)", size=4)
@isa.pattern("reg", "U8TOU16(reg)", size=4)
@isa.pattern("reg", "U8TOI16(reg)", size=4)
def pattern_8_to_16(context, tree, c0):
    context.emit(Sllis(c0, c0, 24))
    context.emit(Srlis(c0, c0, 24))
    return c0


@isa.pattern("reg", "I8TOU32(reg)", size=4)
@isa.pattern("reg", "U8TOU32(reg)", size=4)
@isa.pattern("reg", "U8TOI32(reg)", size=4)
def pattern_8_to_32(context, tree, c0):
    context.emit(Sllis(c0, c0, 24))
    context.emit(Srlis(c0, c0, 24))
    return c0


@isa.pattern("reg", "I16TOU32(reg)", size=4)
@isa.pattern("reg", "U16TOU32(reg)", size=4)
@isa.pattern("reg", "U16TOI32(reg)", size=4)
def pattern_16_to_32(context, tree, c0):
    context.emit(Sllis(c0, c0, 16))
    context.emit(Srlis(c0, c0, 16))
    return c0


@isa.pattern("reg", "I32TOI8(reg)", size=0)
@isa.pattern("reg", "I32TOU8(reg)", size=0)
@isa.pattern("reg", "I32TOI16(reg)", size=0)
@isa.pattern("reg", "I32TOU16(reg)", size=0)
@isa.pattern("reg", "U32TOU8(reg)", size=0)
@isa.pattern("reg", "U32TOI8(reg)", size=0)
@isa.pattern("reg", "U32TOU16(reg)", size=0)
@isa.pattern("reg", "U32TOI16(reg)", size=0)
def pattern_32_to_8_16(context, tree, c0):
    # TODO: do something Liske sign extend or something else?
    return c0


@isa.pattern("reg", "CONSTI32", size=4)
@isa.pattern("reg", "CONSTU32", size=4)
@isa.pattern("reg", "CONSTI16", size=4)
@isa.pattern("reg", "CONSTU16", size=4)
@isa.pattern(
    "reg",
    "CONSTI32",
    size=2,
    condition=lambda t: t.value in range(-2048, 2048),
)
@isa.pattern(
    "reg",
    "CONSTI16",
    size=2,
    condition=lambda t: t.value in range(-2048, 2048),
)
@isa.pattern(
    "reg", "CONSTI8", size=2, condition=lambda t: t.value in range(-128, 128)
)
@isa.pattern("reg", "CONSTU8", size=2, condition=lambda t: t.value < 256)
def pattern_const_i32(context, tree):
    d = context.new_reg(AtallaRegister)
    c0 = tree.value
    context.emit(Lis(d, c0))
    return d


@isa.pattern("reg", "CONSTF32", size=10)
@isa.pattern("reg", "CONSTF64", size=10)
def pattern_const_f32(context, tree):
    float_const = struct.pack("f", tree.value)
    (c0,) = struct.unpack("i", float_const)
    d = context.new_reg(AtallaRegister)
    context.emit(Lis(d, c0))
    return d

# TODO: do branch pseudos
# @isa.pattern("stm", "CJMPI32(reg, reg)", size=4)
# @isa.pattern("stm", "CJMPI16(reg, reg)", size=4)
# @isa.pattern("stm", "CJMPI8(reg, reg)", size=4)
# def pattern_cjmpi(context, tree, c0, c1):
#     op, yes_label, no_label = tree.value
#     opnames = {"<": Blts, ">": Bgts, "==": Beqs, "!=": Bnes, ">=": Bges, "<=": Bles}
#     Bop = opnames[op]
#     jmp_ins = B(no_label.name, jumps=[no_label])
#     context.emit(Bop(c0, c1, yes_label.name, jumps=[yes_label, jmp_ins]))
#     context.emit(jmp_ins)


# @isa.pattern("stm", "CJMPU8(reg, reg)", size=4)
# @isa.pattern("stm", "CJMPU16(reg, reg)", size=4)
# @isa.pattern("stm", "CJMPU32(reg, reg)", size=4)
# def pattern_cjmpu(context, tree, c0, c1):
#     op, yes_label, no_label = tree.value
#     opnames = {
#         "<": Bltu,
#         ">": Bgtu,
#         "==": Beq,
#         "!=": Bne,
#         ">=": Bgeu,
#         "<=": Bleu,
#     }
#     Bop = opnames[op]
#     jmp_ins = B(no_label.name, jumps=[no_label])
#     context.emit(Bop(c0, c1, yes_label.name, jumps=[yes_label, jmp_ins]))
#     context.emit(jmp_ins)


@isa.pattern("reg", "ADDU32(reg, reg)", size=2)
@isa.pattern("reg", "ADDI32(reg, reg)", size=2)
def pattern_add_i32(context, tree, c0, c1):
    d = context.new_reg(AtallaRegister)
    context.emit(Adds(d, c0, c1))
    return d


@isa.pattern("reg", "ADDU16(reg, reg)", size=2)
@isa.pattern("reg", "ADDI16(reg, reg)", size=2)
def pattern_add_i16(context, tree, c0, c1):
    d = context.new_reg(AtallaRegister)
    context.emit(Adds(d, c0, c1))
    return d


@isa.pattern("reg", "ADDI8(reg, reg)", size=2)
@isa.pattern("reg", "ADDU8(reg, reg)", size=2)
def pattern_add8(context, tree, c0, c1):
    d = context.new_reg(AtallaRegister)
    context.emit(Adds(d, c0, c1))
    return d


@isa.pattern(
    "reg",
    "ADDI32(reg, CONSTI32)",
    size=2,
    condition=lambda t: t[1].value < 2048,
)
@isa.pattern(
    "reg",
    "ADDU32(reg, CONSTU32)",
    size=2,
    condition=lambda t: t[1].value < 2048,
)
def pattern_add_i32_reg_const(context, tree, c0):
    d = context.new_reg(AtallaRegister)
    c1 = tree.children[1].value
    context.emit(Addis(d, c0, c1))
    return d


@isa.pattern(
    "reg",
    "ADDI32(CONSTI32, reg)",
    size=2,
    condition=lambda t: t.children[0].value < 2048,
)
@isa.pattern(
    "reg",
    "ADDU32(CONSTU32, reg)",
    size=2,
    condition=lambda t: t.children[0].value < 2048,
)
def pattern_add_i32_const_reg(context, tree, c0):
    d = context.new_reg(AtallaRegister)
    c1 = tree.children[0].value
    context.emit(Addis(d, c0, c1))
    return d


@isa.pattern("reg", "SUBI8(reg, reg)", size=2)
@isa.pattern("reg", "SUBU8(reg, reg)", size=2)
@isa.pattern("reg", "SUBI16(reg, reg)", size=2)
@isa.pattern("reg", "SUBU16(reg, reg)", size=2)
@isa.pattern("reg", "SUBI32(reg, reg)", size=2)
@isa.pattern("reg", "SUBU32(reg, reg)", size=2)
def pattern_sub_i32(context, tree, c0, c1):
    d = context.new_reg(AtallaRegister)
    context.emit(Subs(d, c0, c1))
    return d

# TODO: wtf is this
# @isa.pattern("reg", "LABEL", size=6)
# def pattern_label1(context, tree):
#     d = context.new_reg(AtallaRegister)
#     ln = context.frame.add_constant(tree.value)
#     context.emit(Ands(d, ln))
#     context.emit(Adrl(d, d, ln))
#     context.emit(Lw(d, 0, d))
#     return d


# @isa.pattern("reg", "LABEL", size=4)
# def pattern_label2(context, tree):
#     d = context.new_reg(AtallaRegister)
#     ln = context.frame.add_constant(tree.value)
#     context.emit(Labelrel(d, ln))
#     return d


@isa.pattern(
    "reg",
    "FPRELU32",
    size=4,
    condition=lambda t: t.value.offset in range(-2048, 2048),
)
def pattern_fpreli32(context, tree):
    d = context.new_reg(AtallaRegister)
    offset = tree.value.offset
    Code = Addis(d, FP, offset)
    Code.fprel = True
    context.emit(Code)
    return d


# Memory patterns:
@isa.pattern(
    "mem",
    "FPRELU32",
    size=0,
    condition=lambda t: t.value.offset in range(-2048, 2048),
)
def pattern_mem_fpreli32(context, tree):
    offset = tree.value.offset
    return FP, offset


@isa.pattern("mem", "reg", size=10)
def pattern_mem_reg(context, tree, c0):
    return c0, 0


@isa.pattern("stm", "STRU32(mem, reg)", size=2)
@isa.pattern("stm", "STRI32(mem, reg)", size=2)
@isa.pattern("stm", "STRF32(mem, reg)", size=10)
@isa.pattern("stm", "STRF64(mem, reg)", size=10)
def pattern_sw32(context, tree, c0, c1):
    base_reg, offset = c0
    Code = Sws(c1, offset, base_reg)
    Code.fprel = True
    context.emit(Code)


@isa.pattern("stm", "STRU32(reg, reg)", size=2)
@isa.pattern("stm", "STRI32(reg, reg)", size=2)
@isa.pattern("stm", "STRF32(reg, reg)", size=10)
@isa.pattern("stm", "STRF64(reg, reg)", size=10)
def pattern_sw32_reg(context, tree, c0, c1):
    base_reg = c0
    Code = Sws(c1, 0, base_reg)
    context.emit(Code)


# @isa.pattern("stm", "STRI16(mem, reg)", size=2)
# @isa.pattern("stm", "STRU16(mem, reg)", size=2)
# def pattern_str16_mem(context, tree, c0, c1):
#     base_reg, offset = c0
#     Code = Sh(c1, offset, base_reg)
#     Code.fprel = True
#     context.emit(Code)


# @isa.pattern("stm", "STRI16(reg, reg)", size=2)
# @isa.pattern("stm", "STRU16(reg, reg)", size=2)
# def pattern_str16_reg(context, tree, c0, c1):
#     base_reg = c0
#     Code = Sh(c1, 0, base_reg)
#     context.emit(Code)


# @isa.pattern("stm", "STRU8(mem, reg)", size=2)
# @isa.pattern("stm", "STRI8(mem, reg)", size=2)
# def pattern_sbi8_mem(context, tree, c0, c1):
#     base_reg, offset = c0
#     Code = Sb(c1, offset, base_reg)
#     Code.fprel = True
#     context.emit(Code)


# @isa.pattern("stm", "STRU8(reg, reg)", size=2)
# @isa.pattern("stm", "STRI8(reg, reg)", size=2)
# def pattern_sbi8_reg(context, tree, c0, c1):
#     base_reg = c0
#     Code = Sb(c1, 0, base_reg)
#     context.emit(Code)


# @isa.pattern("reg", "LDRI8(mem)", size=2)
# def pattern_ldri8(context, tree, c0):
#     d = context.new_reg(AtallaRegister)
#     base_reg, offset = c0
#     Code = Lb(d, offset, base_reg)
#     Code.fprel = True
#     context.emit(Code)
#     return d


# @isa.pattern("reg", "LDRI8(reg)", size=2)
# def pattern_ldri8_reg(context, tree, c0):
#     d = context.new_reg(AtallaRegister)
#     base_reg = c0
#     Code = Lb(d, 0, base_reg)
#     context.emit(Code)
#     return d


# @isa.pattern("reg", "LDRU8(mem)", size=2)
# def pattern_ldru8_fprel(context, tree, c0):
#     d = context.new_reg(AtallaRegister)
#     base_reg, offset = c0
#     Code = Lbu(d, offset, base_reg)
#     Code.fprel = True
#     context.emit(Code)
#     return d


# @isa.pattern("reg", "LDRU8(reg)", size=2)
# def pattern_ldru8_reg(context, tree, c0):
#     d = context.new_reg(AtallaRegister)
#     base_reg = c0
#     Code = Lbu(d, 0, base_reg)
#     context.emit(Code)
#     return d


@isa.pattern("reg", "LDRU32(mem)", size=2)
@isa.pattern("reg", "LDRI32(mem)", size=2)
@isa.pattern("reg", "LDRF32(mem)", size=10)
@isa.pattern("reg", "LDRF64(mem)", size=10)
def pattern_ldr32_fprel(context, tree, c0):
    d = context.new_reg(AtallaRegister)
    base_reg, offset = c0
    Code = Lws(d, offset, base_reg)
    Code.fprel = True
    context.emit(Code)
    return d


@isa.pattern("reg", "LDRU32(reg)", size=2)
@isa.pattern("reg", "LDRI32(reg)", size=2)
@isa.pattern("reg", "LDRF32(reg)", size=10)
@isa.pattern("reg", "LDRF64(reg)", size=10)
def pattern_ldr32_reg(context, tree, c0):
    d = context.new_reg(AtallaRegister)
    base_reg = c0
    Code = Lws(d, 0, base_reg)
    context.emit(Code)
    return d


@isa.pattern("reg", "NEGI8(reg)", size=2)
@isa.pattern("reg", "NEGI16(reg)", size=2)
@isa.pattern("reg", "NEGI32(reg)", size=2)
@isa.pattern("reg", "NEGU32(reg)", size=2)
def pattern_negi32(context, tree, c0):
    context.emit(Subs(c0, R0, c0))
    return c0


@isa.pattern("reg", "INVI8(reg)", size=2)
@isa.pattern("reg", "INVU8(reg)", size=2)
@isa.pattern("reg", "INVU32(reg)", size=2)
@isa.pattern("reg", "INVI32(reg)", size=2)
def pattern_inv(context, tree, c0):
    context.emit(Xoris(c0, c0, -1))
    return c0


# @isa.pattern("reg", "LDRU16(reg)", size=2)
# def pattern_ldru16(context, tree, c0):
#     d = context.new_reg(AtallaRegister)
#     context.emit(Lhu(d, 0, c0))
#     return d


# @isa.pattern("reg", "LDRI16(reg)", size=2)
# def pattern_ldri16(context, tree, c0):
#     d = context.new_reg(AtallaRegister)
#     context.emit(Lh(d, 0, c0))
#     return d


@isa.pattern("reg", "LDRU32(reg)", size=2)
@isa.pattern("reg", "LDRI32(reg)", size=2)
def pattern_ldr_i32(context, tree, c0):
    d = context.new_reg(AtallaRegister)
    context.emit(Lws(d, 0, c0))
    return d


@isa.pattern("reg", "ANDI8(reg, reg)", size=2)
@isa.pattern("reg", "ANDU8(reg, reg)", size=2)
@isa.pattern("reg", "ANDI16(reg, reg)", size=2)
@isa.pattern("reg", "ANDU16(reg, reg)", size=2)
@isa.pattern("reg", "ANDI32(reg, reg)", size=2)
@isa.pattern("reg", "ANDU32(reg, reg)", size=2)
def pattern_and_i(context, tree, c0, c1):
    d = context.new_reg(AtallaRegister)
    context.emit(Ands(d, c0, c1))
    return d


@isa.pattern(
    "reg",
    "ANDI32(reg, CONSTI32)",
    size=2,
    condition=lambda t: t.children[1].value < 2048,
)
def pattern_and_i32(context, tree, c0):
    d = context.new_reg(AtallaRegister)
    c1 = tree.children[1].value
    context.emit(Andis(d, c0, c1))
    return d


@isa.pattern(
    "reg",
    "ANDI8(reg, CONSTI8)",
    size=2,
    condition=lambda t: t.children[1].value < 256,
)
@isa.pattern(
    "reg",
    "ANDU8(reg, CONSTU8)",
    size=2,
    condition=lambda t: t.children[1].value < 256,
)
def pattern_and8_reg_const(context, tree, c0):
    d = context.new_reg(AtallaRegister)
    c1 = tree.children[1].value
    context.emit(Andis(d, c0, c1))
    return d


@isa.pattern("reg", "ORU32(reg, reg)", size=2)
@isa.pattern("reg", "ORI32(reg, reg)", size=2)
@isa.pattern("reg", "ORU16(reg, reg)", size=2)
@isa.pattern("reg", "ORI16(reg, reg)", size=2)
@isa.pattern("reg", "ORU8(reg, reg)", size=2)
@isa.pattern("reg", "ORI8(reg, reg)", size=2)
def pattern_or_i32(context, tree, c0, c1):
    d = context.new_reg(AtallaRegister)
    context.emit(Ors(d, c0, c1))
    return d


@isa.pattern(
    "reg",
    "ORI32(reg, CONSTI32)",
    size=2,
    condition=lambda t: t.children[1].value < 2048,
)
def pattern_or_i32_reg_const(context, tree, c0):
    d = context.new_reg(AtallaRegister)
    c1 = tree.children[1].value
    context.emit(Oris(d, c0, c1))
    return d


@isa.pattern(
    "reg",
    "ORI32(CONSTI32, reg)",
    size=2,
    condition=lambda t: t.children[0].value < 2048,
)
def pattern_or_i32_const_reg(context, tree, c0):
    d = context.new_reg(AtallaRegister)
    c1 = tree.children[0].value
    context.emit(Oris(d, c0, c1))
    return d


@isa.pattern("reg", "SHRU8(reg, reg)", size=2)
@isa.pattern("reg", "SHRU16(reg, reg)", size=2)
@isa.pattern("reg", "SHRU32(reg, reg)", size=2)
def pattern_shr_u32(context, tree, c0, c1):
    d = context.new_reg(AtallaRegister)
    context.emit(Srls(d, c0, c1))
    return d


@isa.pattern("reg", "SHRI8(reg, reg)", size=2)
def pattern_shr_i8(context, tree, c0, c1):
    d = context.new_reg(AtallaRegister)
    context.emit(Sllis(c0, c0, 24))
    context.emit(Srais(c0, c0, 24))
    context.emit(Sras(d, c0, c1))
    return d


@isa.pattern("reg", "SHRI16(reg, reg)", size=2)
def pattern_shr_i16(context, tree, c0, c1):
    d = context.new_reg(AtallaRegister)
    context.emit(Sllis(c0, c0, 16))
    context.emit(Srais(c0, c0, 16))
    context.emit(Sras(d, c0, c1))
    return d


@isa.pattern("reg", "SHRI32(reg, reg)", size=2)
def pattern_shr_i32(context, tree, c0, c1):
    d = context.new_reg(AtallaRegister)
    context.emit(Sras(d, c0, c1))
    return d


@isa.pattern(
    "reg",
    "SHRI32(reg, CONSTI32)",
    size=2,
    condition=lambda t: t.children[1].value < 32,
)
def pattern_shr_i32_reg_const(context, tree, c0):
    d = context.new_reg(AtallaRegister)
    c1 = tree.children[1].value
    context.emit(Srais(d, c0, c1))
    return d


@isa.pattern("reg", "SHLU8(reg, reg)", size=2)
@isa.pattern("reg", "SHLI8(reg, reg)", size=2)
@isa.pattern("reg", "SHLU16(reg, reg)", size=2)
@isa.pattern("reg", "SHLI16(reg, reg)", size=2)
@isa.pattern("reg", "SHLU32(reg, reg)", size=2)
@isa.pattern("reg", "SHLI32(reg, reg)", size=2)
def pattern_shl_i32(context, tree, c0, c1):
    d = context.new_reg(AtallaRegister)
    context.emit(Slls(d, c0, c1))
    return d


@isa.pattern(
    "reg",
    "SHLI32(reg, CONSTI32)",
    size=2,
    condition=lambda t: t.children[1].value < 32,
)
def pattern_shl_i32_reg_const(context, tree, c0):
    d = context.new_reg(AtallaRegister)
    c1 = tree.children[1].value
    context.emit(Sllis(d, c0, c1))
    return d


@isa.pattern("reg", "MULI8(reg, reg)", size=10)
@isa.pattern("reg", "MULU8(reg, reg)", size=10)
@isa.pattern("reg", "MULU16(reg, reg)", size=10)
@isa.pattern("reg", "MULI32(reg, reg)", size=10)
@isa.pattern("reg", "MULU32(reg, reg)", size=10)
def pattern_mul_i32(context, tree, c0, c1):
    d = context.new_reg(AtallaRegister)
    context.emit(Muls(d, c0, c1))
    return d


@isa.pattern("reg", "LDRI32(ADDI32(reg, CONSTI32))", size=2)
def pattern_ldr_i32_add(context, tree, c0):
    d = context.new_reg(AtallaRegister)
    c1 = tree.children[0].children[1].value
    assert isinstance(c1, int)
    context.emit(Lws(d, c1, c0))
    return d


@isa.pattern("reg", "DIVI32(reg, reg)", size=10)
def pattern_div_i32(context, tree, c0, c1):
    d = context.new_reg(AtallaRegister)
    context.emit(Divs(d, c0, c1))
    return d


@isa.pattern("reg", "DIVU16(reg, reg)", size=10)
@isa.pattern("reg", "DIVU32(reg, reg)", size=10)
def pattern_div_u32(context, tree, c0, c1):
    d = context.new_reg(AtallaRegister)
    context.emit(Divs(d, c0, c1))
    #could be unsigned
    return d


@isa.pattern("reg", "REMI32(reg, reg)", size=10)
def pattern_rem_i32(context, tree, c0, c1):
    d = context.new_reg(AtallaRegister)
    context.emit(Mods(d, c0, c1))
    return d


@isa.pattern("reg", "REMU16(reg, reg)", size=10)
@isa.pattern("reg", "REMU32(reg, reg)", size=10)
def pattern_rem_u32(context, tree, c0, c1):
    d = context.new_reg(AtallaRegister)
    context.emit(Mods(d, c0, c1))
    #could be unsigned
    return d


@isa.pattern("reg", "XORU8(reg, reg)", size=2)
@isa.pattern("reg", "XORI8(reg, reg)", size=2)
@isa.pattern("reg", "XORU16(reg, reg)", size=2)
@isa.pattern("reg", "XORI16(reg, reg)", size=2)
@isa.pattern("reg", "XORU32(reg, reg)", size=2)
@isa.pattern("reg", "XORI32(reg, reg)", size=2)
def pattern_xor_i32(context, tree, c0, c1):
    d = context.new_reg(AtallaRegister)
    context.emit(Xors(d, c0, c1))
    return d


@isa.pattern(
    "reg",
    "XORI32(reg, CONSTI32)",
    size=2,
    condition=lambda t: t.children[1].value < 2048,
)
def pattern_xor_i32_reg_const(context, tree, c0):
    d = context.new_reg(AtallaRegister)
    c1 = tree.children[1].value
    context.emit(Xoris(d, c0, c1))
    return d


@isa.pattern(
    "reg",
    "XORI32(CONSTI32, reg)",
    size=2,
    condition=lambda t: t.children[0].value < 2048,
)
def pattern_xor_i32_const_reg(context, tree, c0):
    d = context.new_reg(AtallaRegister)
    c1 = tree.children[0].value
    context.emit(Xoris(d, c0, c1))
    return d


# def call_internal2(context, name, a, b, clobbers=()):
#     d = context.new_reg(AtallaRegister)
#     context.move(R12, a)
#     context.move(R13, b)
#     context.emit(RegisterUseDef(uses=(R12, R13)))
#     context.emit(Global(name))
#     context.emit(Bl(LR, name, clobbers=clobbers))
#     context.emit(RegisterUseDef(uses=(R10,)))
#     context.move(d, R10)
#     return d


# def call_internal1(context, name, a, clobbers=()):
#     d = context.new_reg(AtallaRegister)
#     context.move(R12, a)
#     context.emit(RegisterUseDef(uses=(R12,)))
#     context.emit(Global(name))
#     context.emit(Bl(LR, name, clobbers=clobbers))
#     context.emit(RegisterUseDef(uses=(R10,)))
#     context.move(d, R10)
#     return d


# @isa.pattern("reg", "ADDF64(reg, reg)", size=20)
# @isa.pattern("reg", "ADDF32(reg, reg)", size=20)
# def pattern_add_f32(context, tree, c0, c1):
#     return call_internal2(
#         context, "float32_add", c0, c1, clobbers=context.arch.caller_save
#     )


# @isa.pattern("reg", "SUBF64(reg, reg)", size=20)
# @isa.pattern("reg", "SUBF32(reg, reg)", size=20)
# def pattern_sub_f32(context, tree, c0, c1):
#     return call_internal2(
#         context, "float32_sub", c0, c1, clobbers=context.arch.caller_save
#     )


# @isa.pattern("reg", "MULF64(reg, reg)", size=20)
# @isa.pattern("reg", "MULF32(reg, reg)", size=20)
# def pattern_mul_f32(context, tree, c0, c1):
#     return call_internal2(
#         context, "float32_mul", c0, c1, clobbers=context.arch.caller_save
#     )


# @isa.pattern("reg", "DIVF64(reg, reg)", size=20)
# @isa.pattern("reg", "DIVF32(reg, reg)", size=20)
# def pattern_div_f32(context, tree, c0, c1):
#     return call_internal2(
#         context, "float32_div", c0, c1, clobbers=context.arch.caller_save
#     )


# @isa.pattern("reg", "NEGF64(reg)", size=20)
# @isa.pattern("reg", "NEGF32(reg)", size=20)
# def pattern_neg_f32(context, tree, c0):
#     return call_internal1(
#         context, "float32_neg", c0, clobbers=context.arch.caller_save
#     )


# @isa.pattern("reg", "F32TOI32(reg)", size=20)
# @isa.pattern("reg", "F64TOI32(reg)", size=20)
# def pattern_ftoi_f32(context, tree, c0):
#     return call_internal1(
#         context, "float32_to_int32", c0, clobbers=context.arch.caller_save
#     )


# @isa.pattern("reg", "I32TOF32(reg)", size=20)
# @isa.pattern("reg", "I32TOF64(reg)", size=20)
# def pattern_itof_f32(context, tree, c0):
#     return call_internal1(
#         context, "int32_to_float32", c0, clobbers=context.arch.caller_save
#     )


# @isa.pattern("stm", "CJMPF32(reg, reg)", size=20)
# @isa.pattern("stm", "CJMPF64(reg, reg)", size=20)
# def pattern_cjmpf(context, tree, c0, c1):
#     op, yes_label, no_label = tree.value
#     opnames = {
#         "<": "float32_lt",
#         ">": "float32_gt",
#         "==": "float32_eq",
#         "!=": "float32_ne",
#         ">=": "float32_ge",
#         "<=": "float32_le",
#     }
#     Bop = opnames[op]
#     jmp_ins = B(no_label.name, jumps=[no_label])
#     call_internal2(context, Bop, c0, c1, clobbers=context.arch.caller_save)
#     context.emit(Bne(R10, R0, yes_label.name, jumps=[yes_label, jmp_ins]))
#     context.emit(jmp_ins)


def round_up(s):
    return s + (16 - s % 16)
