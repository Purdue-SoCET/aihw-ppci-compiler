from ..encoding import Instruction, Operand, Syntax
from .instructions import isa, Addis, FP, SP, SCPADSP, SCPADFP

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
    isa = isa


class AtallaVSInstruction(Instruction):
    tokens = [AtallaVSToken]
    isa = isa


class AtallaVIInstruction(Instruction):
    tokens = [AtallaVIToken]
    isa = isa


class AtallaVMemInstruction(Instruction):
    tokens = [AtallaVMemToken]
    isa = isa


def make_vv(mnemonic: str, opcode: int, *, default_mask: int = 0, default_sac: int = 0):
    vd  = Operand("vd",  AtallaVectorRegister, write=True)
    vs1 = Operand("vs1", AtallaVectorRegister, read=True)
    vs2 = Operand("vs2", AtallaVectorRegister, read=True)
    syntax   = Syntax([mnemonic, " ", vd, ",", " ", vs1, ",", " ", vs2])
    patterns = {"opcode": opcode, "vd": vd, "vs1": vs1, "vs2": vs2, "mask": default_mask, "sac": default_sac}
    members  = {"syntax": syntax, "vd": vd, "vs1": vs1, "vs2": vs2, "patterns": patterns, "opcode": opcode}
    return type(mnemonic.replace(".", "_"), (AtallaVVInstruction,), members)


def make_vs(mnemonic: str, opcode: int, *, default_mask: int = 0):
    vd  = Operand("vd",  AtallaVectorRegister, write=True)
    vs1 = Operand("vs1", AtallaVectorRegister, read=True)
    rs1 = Operand("rs1", AtallaRegister,       read=True)
    syntax   = Syntax([mnemonic, " ", vd, ",", " ", vs1, ",", " ", rs1])
    patterns = {"opcode": opcode, "vd": vd, "vs1": vs1, "rs1": rs1, "mask": default_mask}
    members  = {"syntax": syntax, "vd": vd, "vs1": vs1, "rs1": rs1, "patterns": patterns, "opcode": opcode}
    return type(mnemonic.replace(".", "_"), (AtallaVSInstruction,), members)


def make_vi(mnemonic: str, opcode: int, *, default_mask: int = 0):
    vd   = Operand("vd",   AtallaVectorRegister, write=True)
    vs1  = Operand("vs1",  AtallaVectorRegister, read=True)
    imm = Operand("imm", int)
    syntax   = Syntax([mnemonic, " ", vd, ",", " ", vs1, ",", " ", imm])
    patterns = {"opcode": opcode, "vd": vd, "vs1": vs1, "imm": imm, "mask": default_mask}
    members  = {"syntax": syntax, "vd": vd, "vs1": vs1, "imm": imm, "patterns": patterns, "opcode": opcode}
    return type(mnemonic.replace(".", "_"), (AtallaVIInstruction,), members)


def make_vm(mnemonic: str, opcode: int, load: bool):
    vd  = Operand("vd",  AtallaVectorRegister, write=load, read=(not load))
    rs1 = Operand("rs1", AtallaRegister, read=True)
    num_cols = Operand("num_cols", int)
    num_rows = Operand("num_rows", int)
    rc = Operand("rc", int)
    sid = Operand("sid", int)
    rc_id = Operand("rc_id", int)
    fprel = False
    syntax   = Syntax([mnemonic, " ", vd, ",", " ", rs1,
                       ",", " ", num_cols,
                       ",", " ", num_rows,
                       ",", " ", rc,
                       ",", " ", rc_id,
                       ",", " ", sid])
    patterns = {
        "opcode": opcode,
        "vd": vd, "rs1": rs1,
        "num_cols": num_cols,
        "rc": rc, "sid": sid,
        "num_rows": num_rows, "rc_id": rc_id,
        "fprel": fprel,
    }
    members  = {"syntax": syntax, "vd": vd, "rs1": rs1, "patterns": patterns, "opcode": opcode,
                "rc": rc, "sid": sid, "num_cols": num_cols, "num_rows": num_rows, "rc_id": rc_id, "fprel": fprel}
    return type(mnemonic.replace(".", "_"), (AtallaVMemInstruction,), members)


# VV
AddVv   = make_vv("add_vv",   0b0101000)
SubVv   = make_vv("sub_vv",   0b0101001)
MulVv   = make_vv("mul_vv",   0b0101010)
DivVv   = make_vv("div_vv",   0b0101011)
AndVv   = make_vv("and_vv",   0b0101100)
OrVv    = make_vv("or_vv",    0b0101101)
XorVv   = make_vv("xor_vv",   0b0101110)
GemmVv  = make_vv("gemm_vv",  0b0101111)
MgtVv   = make_vv("mgt_vv",   0b0110000)
MltVv   = make_vv("mlt_vv",   0b0110001)
MeqVv   = make_vv("meq_vv",   0b0110010)
MneqVv  = make_vv("mneq_vv",  0b0110011)

# VI
AddiVi  = make_vi("addi_vi",  0b0110100)
SubiVi  = make_vi("subi_vi",  0b0110101)
MuliVi  = make_vi("muli_vi",  0b0110110)
DiviVi  = make_vi("divi_vi",  0b0110111)
ExpiVi  = make_vi("expi_vi",  0b0111000)
SqrtiVi = make_vi("sqrti_vi", 0b0111001)
NotVi   = make_vi("not_vi",   0b0111010)
ShiftVi = make_vi("shift_vi", 0b0111011)
LwVi    = make_vi("lw_vi",    0b0111100)
RsumVi  = make_vi("rsum_vi",  0b0111101)
RminVi  = make_vi("rmin_vi",  0b0111110)
RmaxVi  = make_vi("rmax_vi",  0b0111111)

# VS
ShiftVs = make_vs("shift_vs", 0b0111000)

# VM
VregLd = make_vm("vreg_ld", 0b1001101, True)
VregSt = make_vm("vreg_st", 0b1001110, False)

def _new_v(context):
    return context.new_reg(AtallaVectorRegister)

def _new_s(context):
    return context.new_reg(AtallaRegister)

def emit_stackrel_u32(context, base_reg, tree, mark):
    d = context.new_reg(AtallaRegister)
    offset = tree.value.offset
    code = Addis(d, base_reg, offset)
    setattr(code, mark, True)
    context.emit(code)
    return d

@isa.pattern("stm", "STRVEC(mem, vecreg)", size=2)
def pattern_store_vecreg(context, tree, c0, v1):
    Code = VregSt(v1, c0[0], 0, 0, 0, 0, 0)
    Code.fprel = True
    context.emit(Code)

@isa.pattern("vecreg", "LDRVEC(mem)", size=2)
def pattern_load_vecreg(context, tree, c0):
    d = context.new_reg(AtallaVectorRegister)
    Code = VregLd(d, c0[0], 0, 0, 0, 0, 0)
    Code.fprel = True
    context.emit(Code)
    return d

@isa.pattern(
    "reg",
    "SCPADRELU32",
    size=4,
    condition=lambda t: t.value.offset in range(-2048, 2048),
)
def pattern_scpadreli32(context, tree):
    return emit_stackrel_u32(context, SCPADFP, tree, "spadrel")

@isa.pattern(
    "reg",
    "SCPADRELU32",
    size=4,
    condition=lambda t: t.value.offset in range(-2048, 2048),
)
def pattern_scpadrel_vec(context, tree):
    d = context.new_reg(AtallaRegister)
    offset = tree.value.offset
    code = Addis(d, SCPADFP, offset)
    code.spadrel = True
    context.emit(code)
    return d



@isa.pattern("stm", "MOVVEC(vecreg)", size=2)
def pattern_mov32(context, tree, c0):
    context.move(tree.value, c0)
    return tree.value

@isa.pattern("vecreg", "REGVEC(vecreg)", size=1)
def pattern_reg(context, tree):
    return tree.value


# ---------- VV (vector-vector) ----------

@isa.pattern("vecreg", "ADDVEC(vecreg, vecreg)", size=2)
def patt_add_vv(ctx, tree, v0, v1):
    d = _new_v(ctx)
    ctx.emit(AddVv(d, v0, v1))
    return d

@isa.pattern("vecreg", "SUBVEC(vecreg, vecreg)", size=2)
def patt_sub_vv(ctx, tree, v0, v1):
    d = _new_v(ctx)
    ctx.emit(SubVv(d, v0, v1))
    return d

@isa.pattern("vecreg", "MULVEC(vecreg, vecreg)", size=2)
def patt_mul_vv(ctx, tree, v0, v1):
    d = _new_v(ctx)
    ctx.emit(MulVv(d, v0, v1))
    return d

@isa.pattern("vecreg", "DIVVEC(vecreg, vecreg)", size=2)
def patt_div_vv(ctx, tree, v0, v1):
    d = _new_v(ctx)
    ctx.emit(DivVv(d, v0, v1))
    return d

@isa.pattern("vecreg", "ANDVEC(vecreg, vecreg)", size=2)
def patt_and_vv(ctx, tree, v0, v1):
    d = _new_v(ctx)
    ctx.emit(AndVv(d, v0, v1))
    return d

@isa.pattern("vecreg", "ORVEC(vecreg, vecreg)", size=2)
def patt_or_vv(ctx, tree, v0, v1):
    d = _new_v(ctx)
    ctx.emit(OrVv(d, v0, v1))
    return d

@isa.pattern("vecreg", "XORVEC(vecreg, vecreg)", size=2)
def patt_xor_vv(ctx, tree, v0, v1):
    d = _new_v(ctx)
    ctx.emit(XorVv(d, v0, v1))
    return d

@isa.pattern("reg", "GEMMVEC(reg, reg, reg)", size=2)
def patt_gemm_vv(ctx, tree, v0, v1, v2):
    d = _new_v(ctx)
    ctx.emit(GemmVv(d, v0, v1, v2))
    return d

# MVV types. TODO: how do these work?

@isa.pattern("vecreg", "MGTVEC(vecreg, vecreg)", size=2)
def patt_mgt_vv(ctx, tree, v0, v1):
    d = _new_v(ctx)
    ctx.emit(MgtVv(d, v0, v1))
    return d

@isa.pattern("vecreg", "MLTVEC(vecreg, vecreg)", size=2)
def patt_mlt_vv(ctx, tree, v0, v1):
    d = _new_v(ctx)
    ctx.emit(MltVv(d, v0, v1))
    return d

@isa.pattern("vecreg", "MEQVEC(vecreg, vecreg)", size=2)
def patt_meq_vv(ctx, tree, v0, v1):
    d = _new_v(ctx)
    ctx.emit(MeqVv(d, v0, v1))
    return d

@isa.pattern("vecreg", "MNEQVEC(vecreg, vecreg)", size=2)
def patt_mneq_vv(ctx, tree, v0, v1):
    d = _new_v(ctx)
    ctx.emit(MneqVv(d, v0, v1))
    return d

# ---------- VI (vector-immediate) ----------
# TODO: add support for fp immediates


# ADDI
@isa.pattern("vecreg", "ADDVEC(vecreg, CONSTI32)", size=2,
             condition=lambda t: -4096 <= t.children[1].value <= 4095)
# @isa.pattern("vecreg", "ADDVEC(vecreg, CONSTBF16)", size=2,
#              condition=lambda t: -4096 <= t.children[1].value <= 4095)
def patt_add_vi(ctx, tree, vsrc):
    d = _new_v(ctx)
    imm = tree.children[1].value
    ctx.emit(AddiVi(d, vsrc, imm))
    return d

# SUBI
@isa.pattern("vecreg", "SUBVEC(vecreg, CONSTI32)", size=2,
             condition=lambda t: -4096 <= t.children[1].value <= 4095)
def patt_sub_vi(ctx, tree, vsrc):
    d = _new_v(ctx)
    imm = tree.children[1].value
    ctx.emit(SubiVi(d, vsrc, imm))
    return d

# MULI
@isa.pattern("vecreg", "MULVEC(vecreg, CONSTI32)", size=2,
             condition=lambda t: -4096 <= t.children[1].value <= 4095)
def patt_mul_vi(ctx, tree, vsrc):
    d = _new_v(ctx)
    imm = tree.children[1].value
    ctx.emit(MuliVi(d, vsrc, imm))
    return d

# DIVI
@isa.pattern("vecreg", "DIVVEC(vecreg, CONSTI32)", size=2,
             condition=lambda t: -4096 <= t.children[1].value <= 4095)
def patt_div_vi(ctx, tree, vsrc):
    d = _new_v(ctx)
    imm = tree.children[1].value
    ctx.emit(DiviVi(d, vsrc, imm))
    return d

# EXP (immediate exponent)
@isa.pattern("vecreg", "EXPVEC(vecreg, CONSTI32)", size=2,
             condition=lambda t: -4096 <= t.children[1].value <= 4095)
def patt_exp_vi(ctx, tree, vsrc):
    d = _new_v(ctx)
    imm = tree.children[1].value
    ctx.emit(ExpiVi(d, vsrc, imm))
    return d

# SQRT (mode/precision as imm if your ISA uses it)
@isa.pattern("vecreg", "SQRTVEC(vecreg, CONSTI32)", size=2,
             condition=lambda t: -4096 <= t.children[1].value <= 4095)
def patt_sqrt_vi(ctx, tree, vsrc):
    d = _new_v(ctx)
    imm = tree.children[1].value
    ctx.emit(SqrtiVi(d, vsrc, imm))
    return d

# NOT (use imm as a control/mask if required by your ISA; 0 is typical)
@isa.pattern("vecreg", "INVVEC(vecreg, CONSTI32)", size=2,
             condition=lambda t: -4096 <= t.children[1].value <= 4095)
def patt_not_vi(ctx, tree, vsrc):
    d = _new_v(ctx)
    imm = tree.children[1].value
    ctx.emit(NotVi(d, vsrc, imm))
    return d

# SHIFT (vector by immediate)
@isa.pattern("vecreg", "SHLVEC(vecreg, CONSTI32)", size=2,
             condition=lambda t: -4096 <= t.children[1].value <= 4095)
@isa.pattern("vecreg", "SHRVEC(vecreg, CONSTI32)", size=2,
             condition=lambda t: -4096 <= t.children[1].value <= 4095)
def patt_shift_vi(ctx, tree, vsrc):
    d = _new_v(ctx)
    imm = tree.children[1].value
    ctx.emit(ShiftVi(d, vsrc, imm))
    return d
# # ---------- VS (vector-scalar) ----------

# @isa.pattern("vecreg", "SHIFTVS(vecreg, reg)", size=2)
# def patt_shift_vs(ctx, tree, vsrc, sreg):
#     d = _new_v(ctx)
#     ctx.emit(ShiftVs(d, vsrc, sreg))
#     return d
