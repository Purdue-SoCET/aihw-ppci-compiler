from ..isa import Isa
from ..encoding import Instruction, Operand, Syntax
from .tokens import AmpToken, AmpMIToken
from .registers import (
    AmpRegister
)

isa = Isa()

class AmpInstruction(Instruction):
    tokens = [AmpToken]
    isa = isa

def make_r(mnemonic, opcode):
    rd = Operand("rd", AmpRegister, write=True)
    rn = Operand("rn", AmpRegister, read=True)
    rm = Operand("rm", AmpRegister, read=True)
    syntax = Syntax([mnemonic, " ", rd, ",", " ", rn, ",", " ", rm])
    tokens = [AmpToken]
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
    return type(name, (AmpInstruction,), members)

# R-types:
Adds = make_r("add.s", 0b0000001)
Subs = make_r("sub.s", 0b0000010)
Muls = make_r("mul.s", 0b0000011)
Divs = make_r("div.s", 0b0000100)
Mods = make_r("mod.s", 0b0000101)
Ors = make_r("or.s", 0b0000110)
Ands = make_r("and.s", 0b0000111)
Xors = make_r("xor.s", 0b0001000)
Slls = make_r("sll.s", 0b0001001)
Srls = make_r("srl.s", 0b0001010)
Sras = make_r("sra.s", 0b0001011)
Slts = make_r("slt.s", 0b0001100)
Sltus = make_r("sltu.s", 0b0001101)

