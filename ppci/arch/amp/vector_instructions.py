from ..encoding import Instruction, Operand, Syntax
from .tokens import (
    AtallaVVToken,
    AtallaVSToken,
    AtallaVIToken,
    AtallaVMemToken,
)
from .vector_registers import AtallaVectorRegister
from .registers import AtallaRegister


class AtallaVVInstruction(Instruction):
    tokens = [AtallaVVToken]


class AtallaVSInstruction(Instruction):
    tokens = [AtallaVSToken]


class AtallaVIInstruction(Instruction):
    tokens = [AtallaVIToken]


class AtallaVMemInstruction(Instruction):
    tokens = [AtallaVMemToken]


def make_vv(mnemonic: str, opcode: int, *, default_mask: int = 0, default_sac: int = 0):
    vd  = Operand("vd",  AtallaVectorRegister, write=True)
    vs1 = Operand("vs1", AtallaVectorRegister, read=True)
    vs2 = Operand("vs2", AtallaVectorRegister, read=True)
    syntax   = Syntax([mnemonic, " ", vd, ", ", vs1, ", ", vs2])
    patterns = {"opcode": opcode, "vd": vd, "vs1": vs1, "vs2": vs2, "mask": default_mask, "sac": default_sac}
    members  = {"syntax": syntax, "vd": vd, "vs1": vs1, "vs2": vs2, "patterns": patterns, "opcode": opcode}
    return type(mnemonic.replace(".", "_"), (AtallaVVInstruction,), members)


def make_vs(mnemonic: str, opcode: int, *, default_mask: int = 0):
    vd  = Operand("vd",  AtallaVectorRegister, write=True)
    vs1 = Operand("vs1", AtallaVectorRegister, read=True)
    rs1 = Operand("rs1", AtallaRegister,       read=True)
    syntax   = Syntax([mnemonic, " ", vd, ", ", vs1, ", ", rs1])
    patterns = {"opcode": opcode, "vd": vd, "vs1": vs1, "rs1": rs1, "mask": default_mask}
    members  = {"syntax": syntax, "vd": vd, "vs1": vs1, "rs1": rs1, "patterns": patterns, "opcode": opcode}
    return type(mnemonic.replace(".", "_"), (AtallaVSInstruction,), members)


def make_vi(mnemonic: str, opcode: int, *, default_mask: int = 0):
    vd   = Operand("vd",   AtallaVectorRegister, write=True)
    vs1  = Operand("vs1",  AtallaVectorRegister, read=True)
    imm8 = Operand("imm8", int)
    imm5 = Operand("imm5", int)
    syntax   = Syntax([mnemonic, " ", vd, ", ", vs1, ", ", imm8, ", ", imm5])
    patterns = {"opcode": opcode, "vd": vd, "vs1": vs1, "imm8": imm8, "imm5": imm5, "mask": default_mask}
    members  = {"syntax": syntax, "vd": vd, "vs1": vs1, "imm8": imm8, "imm5": imm5, "patterns": patterns, "opcode": opcode}
    return type(mnemonic.replace(".", "_"), (AtallaVIInstruction,), members)


def make_vm(mnemonic: str, opcode: int, *,
            default_tile_r_c_count: int = 0, default_rc: int = 0, default_sp: int = 0,
            default_mask: int = 0, default_rc_id: int = 0):
    vd  = Operand("vd",  AtallaVectorRegister, write=True)
    rs1 = Operand("rs1", AtallaRegister,       read=True)
    syntax   = Syntax([mnemonic, " ", vd, ", ", rs1])
    patterns = {
        "opcode": opcode,
        "vd": vd, "rs1": rs1,
        "tile_r_c_count": default_tile_r_c_count,
        "rc": default_rc, "sp": default_sp,
        "mask": default_mask, "rc_id": default_rc_id,
    }
    members  = {"syntax": syntax, "vd": vd, "rs1": rs1, "patterns": patterns, "opcode": opcode}
    return type(mnemonic.replace(".", "_"), (AtallaVMemInstruction,), members)


# VV
AddVv   = make_vv("add.vv",   0b0101000)
SubVv   = make_vv("sub.vv",   0b0101001)
MulVv   = make_vv("mul.vv",   0b0101010)
DivVv   = make_vv("div.vv",   0b0101011)
AndVv   = make_vv("and.vv",   0b0101100)
OrVv    = make_vv("or.vv",    0b0101101)
XorVv   = make_vv("xor.vv",   0b0101110)
GemmVv  = make_vv("gemm.vv",  0b0101111)
MgtVv   = make_vv("mgt.vv",   0b0110000)
MltVv   = make_vv("mlt.vv",   0b0110001)
MeqVv   = make_vv("meq.vv",   0b0110010)
MneqVv  = make_vv("mneq.vv",  0b0110011)

# VI
AddiVi  = make_vi("addi.vi",  0b0110100)
SubiVi  = make_vi("subi.vi",  0b0110101)
MuliVi  = make_vi("muli.vi",  0b0110110)
DiviVi  = make_vi("divi.vi",  0b0110111)
ExpiVi  = make_vi("expi.vi",  0b0111000)
SqrtiVi = make_vi("sqrti.vi", 0b0111001)
NotVi   = make_vi("not.vi",   0b0111010)
ShiftVi = make_vi("shift.vi", 0b0111011)
LwVi    = make_vi("lw.vi",    0b0111100)
RsumVi  = make_vi("rsum.vi",  0b0111101)
RminVi  = make_vi("rmin.vi",  0b0111110)
RmaxVi  = make_vi("rmax.vi",  0b0111111)

# VS
ShiftVs = make_vs("shift.vs", 0b0111000)

# VM
# VregLd = make_vm("vreg.ld", <opcode>)
# VregSt = make_vm("vreg.st", <opcode>)
