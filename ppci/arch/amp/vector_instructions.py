"""Vector instructions for Atalla architecture (VM, VV, VI, VS, SA only)."""

from ..encoding import Instruction, Operand, Syntax
from .tokens import AtallaVMToken, AtallaSAMToken
from .registers import AtallaRegister, R0
from .instructions import isa  # register on same ISA as scalars

# ---------------- Base classes ----------------
class AtallaVVInstruction(Instruction):
    """Vector-Vector"""
    tokens = [AtallaVMToken]
    isa = isa

class AtallaVIInstruction(Instruction):
    """Vector-Immediate"""
    tokens = [AtallaVMToken]
    isa = isa

class AtallaVSInstruction(Instruction):
    """Vector-Scalar"""
    tokens = [AtallaVMToken]
    isa = isa

# ---------------- Builder helpers (underscore mnemonics) ----------------
def make_vm(mnemonic: str, opcode: int):
    vd  = Operand("vd",  AtallaRegister, write=True)
    rs1 = Operand("rs1", AtallaRegister, read=True)
    rs2 = Operand("rs2", AtallaRegister, read=True)
    imm = Operand("imm", int)
    syntax = Syntax([mnemonic, " ", vd, ",", " ", rs1, ",", " ", rs2, ",", " ", imm])
    patterns = {"opcode": opcode, "rd1": vd, "rs1": rs1, "rs2": rs2, "imm12": imm}
    clsname = mnemonic.title().replace("_", "") + "VM"
    return type(clsname, (Instruction,), {
        "tokens": [AtallaVMToken], "isa": isa,
        "syntax": syntax, "vd": vd, "rs1": rs1, "rs2": rs2, "imm": imm,
        "patterns": patterns, "opcode": opcode
    })

def make_vv(mnemonic: str, opcode: int):
    vd  = Operand("vd",  AtallaRegister, write=True)
    vs1 = Operand("vs1", AtallaRegister, read=True)
    vs2 = Operand("vs2", AtallaRegister, read=True)
    syntax = Syntax([mnemonic, " ", vd, ",", " ", vs1, ",", " ", vs2])
    patterns = {"opcode": opcode, "rd1": vd, "rs1": vs1, "rs2": vs2, "imm12": 0}
    clsname = mnemonic.title().replace("_", "") + "VV"
    return type(clsname, (AtallaVVInstruction,), {
        "syntax": syntax, "vd": vd, "vs1": vs1, "vs2": vs2,
        "patterns": patterns, "opcode": opcode
    })

def make_vi(mnemonic: str, opcode: int):
    vd  = Operand("vd",  AtallaRegister, write=True)
    vs1 = Operand("vs1", AtallaRegister, read=True)
    imm = Operand("imm", int)
    syntax = Syntax([mnemonic, " ", vd, ",", " ", vs1, ",", " ", imm])
    patterns = {"opcode": opcode, "rd1": vd, "rs1": vs1, "rs2": R0, "imm12": imm}
    clsname = mnemonic.title().replace("_", "") + "VI"
    return type(clsname, (AtallaVIInstruction,), {
        "syntax": syntax, "vd": vd, "vs1": vs1, "imm": imm,
        "patterns": patterns, "opcode": opcode
    })

def make_vs(mnemonic: str, opcode: int):
    vd   = Operand("vd",  AtallaRegister, write=True)
    vs1  = Operand("vs1", AtallaRegister, read=True)
    rs1s = Operand("rs1s", AtallaRegister, read=True)
    syntax = Syntax([mnemonic, " ", vd, ",", " ", vs1, ",", " ", rs1s])
    patterns = {"opcode": opcode, "rd1": vd, "rs1": vs1, "rs2": rs1s, "imm12": 0}
    clsname = mnemonic.title().replace("_", "") + "VS"
    return type(clsname, (AtallaVSInstruction,), {
        "syntax": syntax, "vd": vd, "vs1": vs1, "rs1s": rs1s,
        "patterns": patterns, "opcode": opcode
    })

# ---------------- Concrete instructions ----------------
# VM (Vector Memory)
VregLd = make_vm("vreg_ld", 0b0100111)  # 39
VregSt = make_vm("vreg_st", 0b0101000)  # 40

# VV (Vector-Vector)
DivVV  = make_vv("div_vv",  0b0101001)  # 41
MulVV  = make_vv("mul_vv",  0b0101010)  # 42
AddVV  = make_vv("add_vv",  0b0101011)  # 43
AndVV  = make_vv("and_vv",  0b0101100)  # 44
OrVV   = make_vv("or_vv",   0b0101101)  # 45
XorVV  = make_vv("xor_vv",  0b0101110)  # 46
MgtiVV = make_vv("mgti_vv", 0b0101111)  # 47 (writes v0 mask conceptually)
MltiVV = make_vv("mlti_vv", 0b0110000)  # 48
MeqiVV = make_vv("meqi_vv", 0b0110001)  # 49

# VI (Vector-Immediate)
MsetVI  = make_vi("mset_vi",  0b0110110)  # 54
RsumVI  = make_vi("rsum_vi",  0b0110111)  # 55
RminVI  = make_vi("rmin_vi",  0b0111000)  # 56
RmaxVI  = make_vi("rmax_vi",  0b0111001)  # 57
AddiVI  = make_vi("addi_vi",  0b0111010)  # 58
SubiVI  = make_vi("subi_vi",  0b0111011)  # 59
MuliVI  = make_vi("muli_vi",  0b0111100)  # 60
DiviVI  = make_vi("divi_vi",  0b0111101)  # 61
ExpiVI  = make_vi("expi_vi",  0b0111110)  # 62
SqrtiVI = make_vi("sqrti_vi", 0b0111111)  # 63
VshrVI  = make_vi("vshr_vi",  0b1001000)  # 75

# VS (Vector-Scalar)
# vmov_vs: rd = vs1[imm]
class VmovVS(AtallaVSInstruction):
    rd  = Operand("rd",  AtallaRegister, write=True)
    vs1 = Operand("vs1", AtallaRegister, read=True)
    imm = Operand("imm", int)  # lane index
    syntax = Syntax(["vmov_vs", " ", rd, ",", " ", vs1, ",", " ", imm])
    patterns = {"opcode": 0b1000000, "rd1": rd, "rs1": vs1, "rs2": R0, "imm12": imm}

# smov_vs: vd[imm] = rs1
class SmovVS(AtallaVSInstruction):
    vd  = Operand("vd",  AtallaRegister, write=True)
    rs1 = Operand("rs1", AtallaRegister, read=True)
    imm = Operand("imm", int)  # lane index
    syntax = Syntax(["smov_vs", " ", vd, ",", " ", imm, ",", " ", rs1])
    patterns = {"opcode": 0b1000001, "rd1": vd, "rs1": R0, "rs2": rs1, "imm12": imm}

AddVS   = make_vs("add_vs",   0b1000010)  # 66
SubVS   = make_vs("sub_vs",   0b1000011)  # 67
MulVS   = make_vs("mul_vs",   0b1000100)  # 68
DivVS   = make_vs("div_vs",   0b1000101)  # 69
MgtiVS  = make_vs("mgti_vs",  0b1000110)  # 70
MltiVS  = make_vs("mlti_vs",  0b1000111)  # 71
MeqiVS  = make_vs("meqi_vs",  0b1001000)  # 72
MneqiVS = make_vs("mneqi_vs", 0b1001001)  # 73

# SA (Systolic Array)
class GemmSA(Instruction):
    """Store input & PSUM/Kernel to Systolic Array (imm controls loading weights)"""
    tokens = [AtallaSAMToken]
    isa = isa
    vdst = Operand("vdst", AtallaRegister, write=True)
    vs1  = Operand("vs1",  AtallaRegister, read=True)
    imm  = Operand("imm", int)
    syntax = Syntax(["gemm_sa", " ", vdst, ",", " ", vs1, ",", " ", imm])
    patterns = {"opcode": 0b1000111, "rd1": vdst, "rs1": vs1, "rs2": R0, "imm12": imm}

vector_instructions = [
    # VM
    VregLd, VregSt,
    # VV
    DivVV, MulVV, AddVV, AndVV, OrVV, XorVV, MgtiVV, MltiVV, MeqiVV,
    # VI
    MsetVI, RsumVI, RminVI, RmaxVI, AddiVI, SubiVI, MuliVI, DiviVI, ExpiVI, SqrtiVI, VshrVI,
    # VS
    VmovVS, SmovVS, AddVS, SubVS, MulVS, DivVS, MgtiVS, MltiVS, MeqiVS, MneqiVS,
    # SA
    GemmSA,
]
