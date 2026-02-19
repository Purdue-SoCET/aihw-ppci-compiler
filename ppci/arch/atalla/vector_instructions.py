from ppci.wasm.execution.runtime import _f32_to_f16_bits, f16_reinterpret_i16
from ..encoding import Instruction, Operand, Syntax
from .instructions import isa, Addis, FP, SP, SCPADSP, SCPADFP

from .tokens import (
    AtallaSDMAToken,
    AtallaSTMToken,
    AtallaVVToken,
    AtallaVSToken,
    AtallaVIToken,
    AtallaVMemToken,
)
from .vector_registers import AtallaVectorRegister
from .mask_registers import M0, AtallaMaskRegister
from .registers import AtallaRegister
from .instructions import Lis

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


def make_vv(mnemonic: str, opcode: int):
    vd  = Operand("vd",  AtallaVectorRegister, write=True)
    vs1 = Operand("vs1", AtallaVectorRegister, read=True)
    vs2 = Operand("vs2", AtallaVectorRegister, read=True)
    mask = Operand("mask", AtallaMaskRegister, read=True)
    syntax   = Syntax([mnemonic, " ", vd, ",", " ", vs1, ",", " ", vs2, ",", " ", mask])
    patterns = {"opcode": opcode, "vd": vd, "vs1": vs1, "vs2": vs2, "mask": mask}
    members  = {"syntax": syntax, "vd": vd, "vs1": vs1, "vs2": vs2, "patterns": patterns, "opcode": opcode, "mask": mask}
    return type(mnemonic.replace(".", "_"), (AtallaVVInstruction,), members)


def make_vs(mnemonic: str, opcode: int):
    vd  = Operand("vd",  AtallaVectorRegister, write=True)
    vs1 = Operand("vs1", AtallaVectorRegister, read=True)
    rs1 = Operand("rs1", AtallaRegister,       read=True)
    mask = Operand("mask", AtallaMaskRegister, read=True)
    syntax   = Syntax([mnemonic, " ", vd, ",", " ", vs1, ",", " ", rs1, ",", " ", mask])
    patterns = {"opcode": opcode, "vd": vd, "vs1": vs1, "rs1": rs1, "mask": mask}
    members  = {"syntax": syntax, "vd": vd, "vs1": vs1, "rs1": rs1, "patterns": patterns, "opcode": opcode, "mask": mask}
    return type(mnemonic.replace(".", "_"), (AtallaVSInstruction,), members)


def make_vi(mnemonic: str, opcode: int):
    vd   = Operand("vd",   AtallaVectorRegister, write=True)
    vs1  = Operand("vs1",  AtallaVectorRegister, read=True)
    imm = Operand("imm", int)
    mask = Operand("mask", AtallaMaskRegister, read=True)
    syntax   = Syntax([mnemonic, " ", vd, ",", " ", vs1, ",", " ", imm, ",", " ", mask])
    patterns = {"opcode": opcode, "vd": vd, "vs1": vs1, "imm": imm, "mask": mask}
    members  = {"syntax": syntax, "vd": vd, "vs1": vs1, "imm": imm, "patterns": patterns, "opcode": opcode, "mask": mask}
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
AddVv   = make_vv("add_vv",   0b0110010)
SubVv   = make_vv("sub_vv",   0b0110011)
MulVv   = make_vv("mul_vv",   0b0110100)
DivVv   = make_vv("div_vv",   0b0110101)
AndVv   = make_vv("and_vv",   0b0110110)
OrVv    = make_vv("or_vv",    0b0110111)
XorVv   = make_vv("xor_vv",   0b0111000)
GemmVv  = make_vv("gemm_vv",  0b0111001)
# MgtVv   = make_vv("mgt_vv",   0b0110000)
# MltVv   = make_vv("mlt_vv",   0b0110001)
# MeqVv   = make_vv("meq_vv",   0b0110010)
# MneqVv  = make_vv("mneq_vv",  0b0110011)

# VI
AddiVi  = make_vi("addi_vi",  0b0111110) # Binop
SubiVi  = make_vi("subi_vi",  0b0111111) # Binop
MuliVi  = make_vi("muli_vi",  0b1000000) # Binop
DiviVi  = make_vi("divi_vi",  0b1000001) # Binop

ExpiVi  = make_vi("expi_vi",  0b1000010) # Intrinsic
SqrtiVi = make_vi("sqrti_vi", 0b1000011) # Intrinsic
NotVi   = make_vi("not_vi",   0b1000100) # Unop
ShiftVi = make_vi("shift_vi", 0b1000101) # Binop
LwVi    = make_vi("lw_vi",    0b1000110) # TODO: weights?
RsumVi  = make_vi("rsum_vi",  0b1000111)
RminVi  = make_vi("rmin_vi",  0b1001000)
RmaxVi  = make_vi("rmax_vi",  0b1001001)

AddVs   = make_vs("add_vs",   0b1010000)
SubVs   = make_vs("sub_vs",   0b1010001)
MulVs   = make_vs("mul_vs",   0b1010010)
DivVs   = make_vs("div_vs",   0b1010011)
ShiftVs = make_vs("shift_vs", 0b0111000)

# VM
VregLd = make_vm("vreg_ld", 0b1001101, True)
VregSt = make_vm("vreg_st", 0b1001110, False)

# ========== Mask Instructions ==========

class AtallaSTMInstruction(Instruction):
    tokens = [AtallaSTMToken]
    isa = isa

def make_stm(mnemonic: str, opcode: int):
    rs1 = Operand("rs1", AtallaRegister, read=True)
    vmd = Operand("vmd", AtallaMaskRegister, write=True)
    syntax = Syntax([mnemonic, " ", vmd, ",", " ", rs1])
    patterns = {"opcode": opcode, "vmd": vmd, "rs1": rs1}
    members = {"syntax": syntax, "vmd": vmd, "rs1": rs1, "patterns": patterns, "opcode": opcode}
    return type(mnemonic.replace(".", "_"), (AtallaSTMInstruction,), members)

MvStm = make_stm("mv_stm", 0b1001100)

# TODO: MTS Usecase

@isa.pattern("maskreg", "REGMASK(maskreg)", size=1)
def pattern_maskreg(context, tree):
    return tree.value

# @isa.pattern("stm", "MOVMASK(maskreg)", size=1)
# def pattern_movmask(context, tree, c0):
#     context.move(tree.value, c0)
#     return tree.value

@isa.pattern("stm", "MVSTMMASK(reg)", size=2)
def pattern_mvstmmask(context, tree, rs1):
    d = context.new_reg(AtallaMaskRegister)
    context.emit(MvStm(d, rs1))
    return d

# ========== Vector Instructions' Patterns ============

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

@isa.pattern("vecreg", "ADDVEC(vecreg, vecreg, stm)", size=2)
def patt_add_vv(ctx, tree, v0, v1, mask = M0):
    d = _new_v(ctx)
    ctx.emit(AddVv(d, v0, v1, mask))
    return d

@isa.pattern("vecreg", "SUBVEC(vecreg, vecreg, stm)", size=2)
def patt_sub_vv(ctx, tree, v0, v1, mask = M0):
    d = _new_v(ctx)
    ctx.emit(SubVv(d, v0, v1, mask))
    return d

@isa.pattern("vecreg", "MULVEC(vecreg, vecreg, stm)", size=2)
def patt_mul_vv(ctx, tree, v0, v1, mask = M0):
    d = _new_v(ctx)
    ctx.emit(MulVv(d, v0, v1, mask))
    return d

@isa.pattern("vecreg", "DIVVEC(vecreg, vecreg, stm)", size=2)
def patt_div_vv(ctx, tree, v0, v1, mask = M0):
    d = _new_v(ctx)
    ctx.emit(DivVv(d, v0, v1, mask))
    return d

@isa.pattern("vecreg", "ANDVEC(vecreg, vecreg, stm)", size=2)
def patt_and_vv(ctx, tree, v0, v1, mask = M0):
    d = _new_v(ctx)
    ctx.emit(AndVv(d, v0, v1, mask))
    return d

@isa.pattern("vecreg", "ORVEC(vecreg, vecreg, stm)", size=2)
def patt_or_vv(ctx, tree, v0, v1, mask = M0):
    d = _new_v(ctx)
    ctx.emit(OrVv(d, v0, v1, mask))
    return d

@isa.pattern("vecreg", "XORVEC(vecreg, vecreg, stm)", size=2)
def patt_xor_vv(ctx, tree, v0, v1, mask = M0):
    d = _new_v(ctx)
    ctx.emit(XorVv(d, v0, v1, mask))
    return d

@isa.pattern("vecreg", "GEMMVEC(vecreg, vecreg, stm)", size=2)
def patt_gemm_vv(ctx, tree, v0, v1, mask):
    d = _new_v(ctx)
    ctx.emit(GemmVv(d, v0, v1, mask))
    return d

# TODO: MVV types

# @isa.pattern("vecreg", "MGTVEC(vecreg, vecreg, stm)", size=2)
# def patt_mgt_vv(ctx, tree, v0, v1, mask = M0):
#     d = _new_v(ctx)
#     ctx.emit(MgtVv(d, v0, v1, mask))
#     return d

# @isa.pattern("vecreg", "MLTVEC(vecreg, vecreg, stm)", size=2)
# def patt_mlt_vv(ctx, tree, v0, v1, mask = M0):
#     d = _new_v(ctx)
#     ctx.emit(MltVv(d, v0, v1, mask))
#     return d

# @isa.pattern("vecreg", "MEQVEC(vecreg, vecreg, stm)", size=2)
# def patt_meq_vv(ctx, tree, v0, v1, mask = M0):
#     d = _new_v(ctx)
#     ctx.emit(MeqVv(d, v0, v1, mask))
#     return d

# @isa.pattern("vecreg", "MNEQVEC(vecreg, vecreg, stm)", size=2)
# def patt_mneq_vv(ctx, tree, v0, v1, mask = M0):
#     d = _new_v(ctx)
#     ctx.emit(MneqVv(d, v0, v1, mask))
#     return d

# ---------- VI (vector-immediate) ----------

# ADDI
@isa.pattern("vecreg", "ADDVEC(vecreg, CONSTBF16, stm)", size=2,
             condition=lambda t: -4096 <= t.children[1].value <= 4095)
# @isa.pattern("vecreg", "ADDVEC(vecreg, CONSTBF16)", size=2,
#              condition=lambda t: -4096 <= t.children[1].value <= 4095)
def patt_add_vi(ctx, tree, vsrc, mask = M0):
    d = _new_v(ctx)
    assert isinstance(tree.children[1].value, float), "Expected a float immediate"
    imm = _f32_to_f16_bits(tree.children[1].value)  # returns an int 0–65535
    ctx.emit(AddiVi(d, vsrc, imm, mask))
    return d

@isa.pattern("vecreg", "ADDVEC(CONSTBF16, vecreg, stm)", size=2,
             condition=lambda t: -4096 <= t.children[0].value <= 4095)
def patt_add_vi_comm(ctx, tree, vsrc, mask = M0):
    d = _new_v(ctx)
    assert isinstance(tree.children[0].value, float), "Expected a float immediate"
    imm = _f32_to_f16_bits(tree.children[0].value)  # returns an int 0–65535
    ctx.emit(AddiVi(d, vsrc, imm, mask))
    return d

# SUBI
@isa.pattern("vecreg", "SUBVEC(vecreg, CONSTBF16, stm)", size=2,
             condition=lambda t: -4096 <= t.children[1].value <= 4095)
def patt_sub_vi(ctx, tree, vsrc, mask = M0):
    d = _new_v(ctx)
    assert isinstance(tree.children[1].value, float), "Expected a float immediate"
    imm = _f32_to_f16_bits(tree.children[1].value)
    ctx.emit(SubiVi(d, vsrc, imm, mask))
    return d

# @isa.pattern("vecreg", "SUBVEC(CONSTBF16, vecreg, stm)", size=2,
#                 condition=lambda t: -4096 <= t.children[0].value <= 4095
#             )
# def patt_sub_vi_comm(ctx, tree, vsrc, mask = M0):
#     d = _new_v(ctx)
#     imm = tree.children[0].value
#     ctx.emit(SubiVi(d, vsrc, str(-imm), mask))  # Negate imm for commuted form
#     return d

# MULI
@isa.pattern("vecreg", "MULVEC(vecreg, CONSTBF16, stm)", size=2,
             condition=lambda t: -4096 <= t.children[1].value <= 4095)
def patt_mul_vi(ctx, tree, vsrc, mask = M0):
    d = _new_v(ctx)
    assert isinstance(tree.children[1].value, float), "Expected a float immediate"
    imm = _f32_to_f16_bits(tree.children[1].value)
    ctx.emit(MuliVi(d, vsrc, imm, mask))
    return d

@isa.pattern("vecreg", "MULVEC(CONSTBF16, vecreg, stm)", size=2,
             condition=lambda t: -4096 <= t.children[0].value <= 4095)
def patt_mul_vi_comm(ctx, tree, vsrc, mask = M0):
    d = _new_v(ctx)
    assert isinstance(tree.children[0].value, float), "Expected a float immediate"
    imm = _f32_to_f16_bits(tree.children[0].value)
    ctx.emit(MuliVi(d, vsrc, imm, mask))  # Same imm for commuted form
    return d

# DIVI
@isa.pattern("vecreg", "DIVVEC(vecreg, CONSTBF16, stm)", size=2,
             condition=lambda t: -4096 <= t.children[1].value <= 4095)
def patt_div_vi(ctx, tree, vsrc, mask = M0):
    d = _new_v(ctx)
    assert isinstance(tree.children[1].value, float), "Expected a float immediate"
    imm = _f32_to_f16_bits(tree.children[1].value)
    ctx.emit(DiviVi(d, vsrc, imm, mask))
    return d

# @isa.pattern("vecreg", "DIVVEC(CONSTBF16, vecreg, stm)", size=2,
#                 condition=lambda t: -4096 <= t.children[0].value <= 4095
#             )
# def patt_div_vi_comm(ctx, tree, vsrc, mask = M0):
#     d = _new_v(ctx)
#     imm = tree.children[0].value
#     ctx.emit(DiviVi(d, vsrc, str(1/imm), mask))  # Use reciprocal for commuted form
#     return d

# EXP (immediate exponent)
@isa.pattern("vecreg", "EXPVEC(vecreg, CONSTBF16, stm)", size=2,
             condition=lambda t: -4096 <= t.children[1].value <= 4095)
def patt_exp_vi(ctx, tree, vsrc, mask = M0):
    d = _new_v(ctx)
    ctx.emit(ExpiVi(d, vsrc, 0, mask))
    return d

# SQRT (mode/precision as imm if your ISA uses it)
@isa.pattern("vecreg", "SQRTVEC(vecreg, CONSTBF16, stm)", size=2,
             condition=lambda t: -4096 <= t.children[1].value <= 4095)
def patt_sqrt_vi(ctx, tree, vsrc, mask = M0):
    d = _new_v(ctx)
    ctx.emit(SqrtiVi(d, vsrc, 0, mask))
    return d

# NOT (use imm as a control/mask if required by your ISA; 0 is typical)
@isa.pattern("vecreg", "INVVEC(vecreg, CONSTBF16, stm)", size=2)
def patt_not_vi(ctx, tree, vsrc, mask = M0):
    d = _new_v(ctx)
    ctx.emit(NotVi(d, vsrc, 0, mask))
    return d

# SHIFT (vector by immediate) 
# Not used in the ISA
# @isa.pattern("vecreg", "SHLVEC(vecreg, CONSTBF16, stm)", size=2,
#              condition=lambda t: -4096 <= t.children[1].value <= 4095)
# @isa.pattern("vecreg", "SHRVEC(vecreg, CONSTBF16, stm)", size=2,
#              condition=lambda t: -4096 <= t.children[1].value <= 4095)
# def patt_shift_vi(ctx, tree, vsrc, mask = M0):
#     d = _new_v(ctx)
#     imm = tree.children[1].value
#     ctx.emit(ShiftVi(d, vsrc, imm, mask))
#     return d

@isa.pattern("vecreg", "RSUMVEC(vecreg, CONSTBF16, stm)", size=2)
def patt_rsum_vi(ctx, tree, vsrc, mask = M0):
    d = _new_v(ctx)
    assert isinstance(tree.children[1].value, float), "Expected a float immediate"
    imm = _f32_to_f16_bits(tree.children[1].value)
    ctx.emit(RsumVi(d, vsrc, imm, mask))
    return d

@isa.pattern("vecreg", "RMINVEC(vecreg, CONSTBF16, stm)", size=2)
def patt_rmin_vi(ctx, tree, vsrc, mask = M0):
    d = _new_v(ctx)
    assert isinstance(tree.children[1].value, float), "Expected a float immediate"
    imm = _f32_to_f16_bits(tree.children[1].value)
    ctx.emit(RminVi(d, vsrc, imm, mask))
    return d

@isa.pattern("vecreg", "RMAXVEC(vecreg, CONSTBF16, stm)", size=2)
def patt_rmax_vi(ctx, tree, vsrc, mask = M0):
    d = _new_v(ctx)
    assert isinstance(tree.children[1].value, float), "Expected a float immediate"
    imm = _f32_to_f16_bits(tree.children[1].value)
    ctx.emit(RmaxVi(d, vsrc, imm, mask))
    return d
# # ---------- VS (vector-scalar) ----------

@isa.pattern("vecreg", "ADDVEC(vecreg, reg, stm)", size=2)
def patt_add_vs(ctx, tree, vsrc, rs1, mask = M0):
    d = _new_v(ctx)
    ctx.emit(AddVs(d, vsrc, rs1, mask))
    return d

@isa.pattern("vecreg", "SUBVEC(vecreg, reg, stm)", size=2)
def patt_sub_vs(ctx, tree, vsrc, rs1, mask = M0):
    d = _new_v(ctx)
    ctx.emit(SubVs(d, vsrc, rs1, mask))
    return d

@isa.pattern("vecreg", "MULVEC(vecreg, reg, stm)", size=2)
def patt_mul_vs(ctx, tree, vsrc, rs1, mask = M0):
    d = _new_v(ctx)
    ctx.emit(MulVs(d, vsrc, rs1, mask))
    return d

@isa.pattern("vecreg", "DIVVEC(vecreg, reg, stm)", size=2)
def patt_div_vs(ctx, tree, vsrc, rs1, mask = M0):
    d = _new_v(ctx)
    ctx.emit(DivVs(d, vsrc, rs1, mask))
    return d


class AtallaSDMAInstruction(Instruction):
    tokens = [AtallaSDMAToken]
    isa = isa


def make_sdma(mnemonic: str, opcode: int):
    rs2  = Operand("rs2",  AtallaRegister, read=True)
    rs1_rd1 = Operand("rs1_rd1", AtallaRegister, read=True)
    num_cols = Operand("num_cols", int)
    num_rows = Operand("num_rows", int)
    sid = Operand("sid", int)
    fprel = False
    syntax   = Syntax([mnemonic, " ", rs2, ",", " ", rs1_rd1,
                       ",", " ", num_cols,
                       ",", " ", num_rows,
                       ",", " ", sid])
    patterns = {
        "opcode": opcode,
        "rs2": rs2, "rs1_rd1": rs1_rd1,
        "num_cols": num_cols,
        "sid": sid,
        "num_rows": num_rows,
        "fprel": fprel,
    }
    members  = {"syntax": syntax, "rs2": rs2, "rs1_rd1": rs1_rd1, "patterns": patterns, "opcode": opcode,
                "sid": sid, "num_cols": num_cols, "num_rows": num_rows, "fprel": fprel}
    return type(mnemonic.replace(".", "_"), (AtallaSDMAInstruction,), members)

ScpadLd = make_sdma("scpad_ld", 0b1011000)
ScpadSt = make_sdma("scpad_st", 0b1011001)