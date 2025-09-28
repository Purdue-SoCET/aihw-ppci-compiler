from ..isa import Isa
from ..encoding import Instruction, Operand, Syntax
from .tokens import *
from .registers import (
    AtallaRegister
)

isa = Isa()

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
Mulis = make_i("muli_s", 0b0010100)
Divis = make_i("divi_s", 0b0010101)
Modis = make_i("modi_s", 0b0010110)
Oris = make_i("ori_s", 0b0010111)
Andis = make_i("andi_s", 0b0011000)
Xoris = make_i("xori_s", 0b0011001)
Sllis = make_i("slli_s", 0b0011010)
Srlis = make_i("srli_s", 0b0011011)
Srais = make_i("srai_s", 0b0011100)
Sltis = make_i("slti_s", 0b0011101)
Sltuis = make_i("sltui_s", 0b0011110)


class AtallaBRInstruction(Instruction):
    tokens = [AtallaBRToken]
    isa = isa

    def relocations(self):
        # TODO: Fill in
        pass

def make_br(mnemonic, opcode):
    rs1 = Operand("rs1", AtallaRegister, read=True)
    rs2 = Operand("rs2", AtallaRegister, read=True)
    imm12 = Operand("offset", int)
    fprel = False
    syntax = Syntax([mnemonic, " ", rs1, ",", " ", rs2, ",", " ", imm12])
    tokens = [AtallaBRToken]
    patterns = {
        "opcode": opcode,
        "rs1": rs1,
        "rs2": rs2,
        "imm12": imm12
    }
    members = {
        "syntax": syntax,
        "fprel": fprel,
        "rs1": rs1,
        "rs2": rs2,
        "imm12": imm12,
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
    offset = Operand("offset", int)
    fprel = False
    syntax = Syntax([mnemonic, " ", rd, ",", " ", offset, "(", rs1, ")"])
    tokens = [AtallaMToken]
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

Halt = make_nop("halt", 0b1111111)
Fence = make_nop("fence", 0b0100100)
