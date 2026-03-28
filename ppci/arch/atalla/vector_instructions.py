from ppci.wasm.execution.runtime import _f32_to_f16_bits
from ..encoding import Instruction, Operand, Syntax
from .instructions import isa, Addis, FP, SP, SCPADSP, SCPADFP, Lws, Sws

from .tokens import (
    AtallaMVVToken,
    AtallaMVSToken,
    AtallaSDMAToken,
    AtallaSTMToken,
    AtallaMTSToken,
    AtallaVTSToken,
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

class AtallaMVVInstruction(Instruction):
    tokens = [AtallaMVVToken]
    isa = isa

class AtallaMVSInstruction(Instruction):
    tokens = [AtallaMVSToken]
    isa = isa


def make_vv(mnemonic: str, opcode: int):
    vd  = Operand("vd",  AtallaVectorRegister, write=True)
    vs1 = Operand("vs1", AtallaVectorRegister, read=True)
    vs2 = Operand("vs2", AtallaVectorRegister, read=True)
    mask_reg = Operand("mask_reg", AtallaMaskRegister, read=True)
    sac = Operand("sac", int)
    syntax   = Syntax([mnemonic, " ", vd, ",", " ", vs1, ",", " ", vs2, ",", " ", mask_reg, ",", " ", sac])
    patterns = {"opcode": opcode, "vd": vd, "vs1": vs1, "vs2": vs2, "mask_reg": mask_reg, "sac": sac}
    members  = {"syntax": syntax, "vd": vd, "vs1": vs1, "vs2": vs2, "patterns": patterns, "opcode": opcode, "mask_reg": mask_reg, "sac": sac}
    return type(mnemonic.replace(".", "_"), (AtallaVVInstruction,), members)


def make_vs(mnemonic: str, opcode: int):
    vd  = Operand("vd",  AtallaVectorRegister, write=True)
    vs1 = Operand("vs1", AtallaVectorRegister, read=True)
    rs1 = Operand("rs1", AtallaRegister,       read=True)
    mask_reg = Operand("mask_reg", AtallaMaskRegister, read=True)
    syntax   = Syntax([mnemonic, " ", vd, ",", " ", vs1, ",", " ", rs1, ",", " ", mask_reg])
    patterns = {"opcode": opcode, "vd": vd, "vs1": vs1, "rs1": rs1, "mask_reg": mask_reg}
    members  = {"syntax": syntax, "vd": vd, "vs1": vs1, "rs1": rs1, "patterns": patterns, "opcode": opcode, "mask_reg": mask_reg}
    return type(mnemonic.replace(".", "_"), (AtallaVSInstruction,), members)


def make_vi(mnemonic: str, opcode: int):
    vd   = Operand("vd",   AtallaVectorRegister, write=True)
    vs1  = Operand("vs1",  AtallaVectorRegister, read=True)
    imm = Operand("imm", int)
    mask_reg = Operand("mask_reg", AtallaMaskRegister, read=True)
    syntax   = Syntax([mnemonic, " ", vd, ",", " ", vs1, ",", " ", imm, ",", " ", mask_reg])
    patterns = {"opcode": opcode, "vd": vd, "vs1": vs1, "imm": imm, "mask_reg": mask_reg}
    members  = {"syntax": syntax, "vd": vd, "vs1": vs1, "imm": imm, "patterns": patterns, "opcode": opcode, "mask_reg": mask_reg}
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
    }
    members  = {"syntax": syntax, "vd": vd, "rs1": rs1, "patterns": patterns, "opcode": opcode,
                "rc": rc, "sid": sid, "num_cols": num_cols, "num_rows": num_rows, "rc_id": rc_id, "fprel": fprel}
    return type(mnemonic.replace(".", "_"), (AtallaVMemInstruction,), members)

def make_mvv(mnemonic: str, opcode: int):
    vs1  = Operand("vs1",  AtallaVectorRegister, read=True)
    vs2 = Operand("vs2", AtallaVectorRegister,       read=True)
    vmd = Operand("vmd", AtallaMaskRegister, write=True)
    mask_reg = Operand("mask_reg", AtallaMaskRegister, read=True)
    syntax   = Syntax([mnemonic, " ", vmd, ",", " ", vs1, ",", " ", vs2, ",", " ", mask_reg])
    patterns = {"opcode": opcode, "vs1": vs1, "vs2": vs2, "vmd": vmd, "mask_reg": mask_reg}
    members  = {"syntax": syntax, "vs1": vs1, "vs2": vs2, "patterns": patterns, "opcode": opcode, "vmd": vmd, "mask_reg": mask_reg}
    return type(mnemonic.replace(".", "_"), (AtallaMVVInstruction,), members)

def make_mvs(mnemonic: str, opcode: int):
    vs1  = Operand("vs1",  AtallaVectorRegister, read=True)
    rs1 = Operand("rs1", AtallaRegister,       read=True)
    vmd = Operand("vmd", AtallaMaskRegister, write=True)
    mask_reg = Operand("mask_reg", AtallaMaskRegister, read=True)
    syntax   = Syntax([mnemonic, " ", vmd, ",", " ", vs1, ",", " ", rs1, ",", " ", mask_reg])
    patterns = {"opcode": opcode, "vs1": vs1, "rs1": rs1, "vmd": vmd, "mask_reg": mask_reg}
    members  = {"syntax": syntax, "vs1": vs1, "rs1": rs1, "patterns": patterns, "opcode": opcode, "vmd": vmd, "mask_reg": mask_reg}
    return type(mnemonic.replace(".", "_"), (AtallaMVSInstruction,), members)

# VV
AddVv   = make_vv("add_vv",   0b0110010)
SubVv   = make_vv("sub_vv",   0b0110011)
MulVv   = make_vv("mul_vv",   0b0110100)
#DivVv   = make_vv("div_vv",   0b0110101)

# Not in the ISA anymore:
# AndVv   = make_vv("and_vv",   0b0110110)
# OrVv    = make_vv("or_vv",    0b0110111)
# XorVv   = make_vv("xor_vv",   0b0111000)

GemmVv  = make_vv("gemm_vv",  0b0111001)

# MVV
MgtMvv = make_mvv("mgt_mvv", 0b0111010)
MltMvv = make_mvv("mlt_mvv", 0b0111011)
MeqMvv = make_mvv("meq_mvv", 0b0111100)
MneqMvv = make_mvv("mneq_mvv", 0b0111101)

# VI
AddiVi  = make_vi("addi_vi",  0b0111110)
SubiVi  = make_vi("subi_vi",  0b0111111)
MuliVi  = make_vi("muli_vi",  0b1000000)
DiviVi  = make_vi("divi_vi",  0b1000001)

ExpiVi  = make_vi("expi_vi",  0b1000010)
SqrtiVi = make_vi("sqrti_vi", 0b1000011)
NotVi   = make_vi("not_vi",   0b1000100)
ShiftVi = make_vi("shift_vi", 0b1000101)
LwVi    = make_vi("lw_vi",    0b1000110)
RsumVi  = make_vi("rsum_vi",  0b1000111)
RminVi  = make_vi("rmin_vi",  0b1001000)
RmaxVi  = make_vi("rmax_vi",  0b1001001)

AddVs   = make_vs("add_vs",   0b1010000)
SubVs   = make_vs("sub_vs",   0b1010001)
MulVs   = make_vs("mul_vs",   0b1010010)
# DivVs   = make_vs("div_vs",   0b1010011)
ShiftVs = make_vs("shift_vs", 0b0111000)

# MVS
MgtMvs = make_mvs("mgt_mvs", 0b1010100)
MltMvs = make_mvs("mlt_mvs", 0b1010101)
MeqMvs = make_mvs("meq_mvs", 0b1010110)
MneqMvs = make_mvs("mneq_mvs", 0b1010111)

# VM
VregLd = make_vm("vreg_ld", 0b1001101, True)
VregSt = make_vm("vreg_st", 0b1001110, False)

# ========== Mask Instructions ==========

class AtallaSTMInstruction(Instruction):
    tokens = [AtallaSTMToken]
    isa = isa

class AtallaMTSInstruction(Instruction):
    tokens = [AtallaMTSToken]
    isa = isa

def make_stm(mnemonic: str, opcode: int):
    rs1 = Operand("rs1", AtallaRegister, read=True)
    vmd = Operand("vmd", AtallaMaskRegister, write=True)
    syntax = Syntax([mnemonic, " ", vmd, ",", " ", rs1])
    patterns = {"opcode": opcode, "vmd": vmd, "rs1": rs1}
    members = {"syntax": syntax, "vmd": vmd, "rs1": rs1, "patterns": patterns, "opcode": opcode}
    return type(mnemonic.replace(".", "_"), (AtallaSTMInstruction,), members)

def make_mts(mnemonic: str, opcode: int):
    rd = Operand("rd", AtallaRegister, write=True)
    vms = Operand("vms", AtallaMaskRegister, read=True)
    syntax = Syntax([mnemonic, " ", rd, ",", " ", vms])
    patterns = {"opcode": opcode, "rd": rd, "vms": vms}
    members = {"syntax": syntax, "rd": rd, "vms": vms, "patterns": patterns, "opcode": opcode}
    return type(mnemonic.replace(".", "_"), (AtallaMTSInstruction,), members)

MvStm = make_stm("mv_stm", 0b1001100)
MvMts = make_mts("mv_mts", 0b1001011)

# TODO: MTS Usecase

@isa.pattern("maskreg", "REGMASK(maskreg)", size=1)
def pattern_maskreg(context, tree):
    return tree.value

@isa.pattern("stm", "MOVMASK(maskreg)", size=3)
def pattern_movmask(context, tree, c0):
    tmp = context.new_reg(AtallaRegister)
    context.emit(MvMts(tmp, c0))
    context.emit(MvStm(tree.value, tmp))
    return tree.value

@isa.pattern("stm", "STRMASK(mem, maskreg)", size=4)
def pattern_store_maskreg(context, tree, c0, m1):
    base_reg, offset = c0
    tmp = context.new_reg(AtallaRegister)
    context.emit(MvMts(tmp, m1))
    code = Sws(tmp, offset, base_reg)
    code.fprel = True
    context.emit(code)

@isa.pattern("maskreg", "LDRMASK(mem)", size=4)
def pattern_load_maskreg(context, tree, c0):
    base_reg, offset = c0
    tmp = context.new_reg(AtallaRegister)
    code = Lws(tmp, offset, base_reg)
    code.fprel = True
    context.emit(code)
    d = context.new_reg(AtallaMaskRegister)
    context.emit(MvStm(d, tmp))
    return d

@isa.pattern("reg", "MASKTOI32(maskreg)", size=1)
def pattern_masktoi32(context, tree, c0):
    d = context.new_reg(AtallaRegister)
    context.emit(MvMts(d, c0))
    return d

@isa.pattern("maskreg", "MVSTMMASK(reg)", size=2)
def pattern_mvstmmask(context, tree, rs1):
    d = context.new_reg(AtallaMaskRegister)
    context.emit(MvStm(d, rs1))
    return d

@isa.pattern("maskreg", "MLTMASK(vecreg, vecreg, maskreg)", size=2)
def pattern_mkmskltvec(context, tree, v0, v1, mask):
    d = context.new_reg(AtallaMaskRegister)
    context.emit(MltMvv(d, v0, v1, mask))
    return d

@isa.pattern("maskreg", "MGTMASK(vecreg, vecreg, maskreg)", size=2)
def pattern_mkmskgtvec(context, tree, v0, v1, mask):
    d = context.new_reg(AtallaMaskRegister)
    context.emit(MgtMvv(d, v0, v1, mask))
    return d

@isa.pattern("maskreg", "MEQMASK(vecreg, vecreg, maskreg)", size=2)
def pattern_mkmskeqvec(context, tree, v0, v1, mask):
    d = context.new_reg(AtallaMaskRegister)
    context.emit(MeqMvv(d, v0, v1, mask))
    return d

@isa.pattern("maskreg", "MNEQMASK(vecreg, vecreg, maskreg)", size=2)
def pattern_mkmskneqvec(context, tree, v0, v1, mask):
    d = context.new_reg(AtallaMaskRegister)
    context.emit(MneqMvv(d, v0, v1, mask))
    return d

@isa.pattern("maskreg", "MLTMASK(vecreg, reg, maskreg)", size=2)
def pattern_mkmskltvec_scalar(context, tree, v0, rs1, mask):
    d = context.new_reg(AtallaMaskRegister)
    context.emit(MltMvs(d, v0, rs1, mask))
    return d

@isa.pattern("maskreg", "MGTMASK(vecreg, reg, maskreg)", size=2)
def pattern_mkmskgtvec_scalar(context, tree, v0, rs1, mask):
    d = context.new_reg(AtallaMaskRegister)
    context.emit(MgtMvs(d, v0, rs1, mask))
    return d

@isa.pattern("maskreg", "MEQMASK(vecreg, reg, maskreg)", size=2)
def pattern_mkmskeqvec_scalar(context, tree, v0, rs1, mask):
    d = context.new_reg(AtallaMaskRegister)
    context.emit(MeqMvs(d, v0, rs1, mask))
    return d

@isa.pattern("maskreg", "MNEQMASK(vecreg, reg, maskreg)", size=2)
def pattern_mkmskneqvec_scalar(context, tree, v0, rs1, mask):
    d = context.new_reg(AtallaMaskRegister)
    context.emit(MneqMvs(d, v0, rs1, mask))
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

@isa.pattern("vecreg", "ADDVEC(vecreg, vecreg, maskreg)", size=2)
def patt_add_vv(ctx, tree, v0, v1, mask = M0):
    d = _new_v(ctx)
    ctx.emit(AddVv(d, v0, v1, mask, 0))
    return d

@isa.pattern("vecreg", "SUBVEC(vecreg, vecreg, maskreg)", size=2)
def patt_sub_vv(ctx, tree, v0, v1, mask = M0):
    d = _new_v(ctx)
    ctx.emit(SubVv(d, v0, v1, mask, 0))
    return d

@isa.pattern("vecreg", "MULVEC(vecreg, vecreg, maskreg)", size=2)
def patt_mul_vv(ctx, tree, v0, v1, mask = M0):
    d = _new_v(ctx)
    ctx.emit(MulVv(d, v0, v1, mask, 0))
    return d

# @isa.pattern("vecreg", "DIVVEC(vecreg, vecreg, stm)", size=2)
# def patt_div_vv(ctx, tree, v0, v1, mask = M0):
#     d = _new_v(ctx)
#     ctx.emit(DivVv(d, v0, v1, mask))
#     return d


# Not in the ISA anymore:
# @isa.pattern("vecreg", "ANDVEC(vecreg, vecreg, maskreg)", size=2)
# def patt_and_vv(ctx, tree, v0, v1, mask = M0):
#     d = _new_v(ctx)
#     ctx.emit(AndVv(d, v0, v1, mask))
#     return d

# @isa.pattern("vecreg", "ORVEC(vecreg, vecreg, maskreg)", size=2)
# def patt_or_vv(ctx, tree, v0, v1, mask = M0):
#     d = _new_v(ctx)
#     ctx.emit(OrVv(d, v0, v1, mask))
#     return d

# @isa.pattern("vecreg", "XORVEC(vecreg, vecreg, maskreg)", size=2)
# def patt_xor_vv(ctx, tree, v0, v1, mask = M0):
#     d = _new_v(ctx)
#     ctx.emit(XorVv(d, v0, v1, mask))
#     return d

@isa.pattern("vecreg", "GEMMVEC(vecreg, vecreg, maskreg)", size=2)
def patt_gemm_vv(ctx, tree, v0, v1, mask):
    d = _new_v(ctx)
    ctx.emit(GemmVv(d, v0, v1, mask, 0))
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
@isa.pattern("vecreg", "ADDVEC(vecreg, CONSTBF16, maskreg)", size=2,
             condition=lambda t: -4096 <= t.children[1].value <= 4095)
# @isa.pattern("vecreg", "ADDVEC(vecreg, CONSTBF16)", size=2,
#              condition=lambda t: -4096 <= t.children[1].value <= 4095)
def patt_add_vi(ctx, tree, vsrc, mask = M0):
    d = _new_v(ctx)
    assert isinstance(tree.children[1].value, float), "Expected a float immediate"
    imm = _f32_to_f16_bits(tree.children[1].value)  # returns an int 0–65535
    ctx.emit(AddiVi(d, vsrc, imm, mask))
    return d

@isa.pattern("vecreg", "ADDVEC(CONSTBF16, vecreg, maskreg)", size=2,
             condition=lambda t: -4096 <= t.children[0].value <= 4095)
def patt_add_vi_comm(ctx, tree, vsrc, mask = M0):
    d = _new_v(ctx)
    assert isinstance(tree.children[0].value, float), "Expected a float immediate"
    imm = _f32_to_f16_bits(tree.children[0].value)  # returns an int 0–65535
    ctx.emit(AddiVi(d, vsrc, imm, mask))
    return d

# SUBI
@isa.pattern("vecreg", "SUBVEC(vecreg, CONSTBF16, maskreg)", size=2,
             condition=lambda t: -4096 <= t.children[1].value <= 4095)
def patt_sub_vi(ctx, tree, vsrc, mask = M0):
    d = _new_v(ctx)
    assert isinstance(tree.children[1].value, float), "Expected a float immediate"
    imm = _f32_to_f16_bits(tree.children[1].value)
    ctx.emit(SubiVi(d, vsrc, imm, mask))
    return d

# @isa.pattern("vecreg", "SUBVEC(CONSTBF16, vecreg, maskreg)", size=2,
#                 condition=lambda t: -4096 <= t.children[0].value <= 4095
#             )
# def patt_sub_vi_comm(ctx, tree, vsrc, mask = M0):
#     d = _new_v(ctx)
#     imm = tree.children[0].value
#     ctx.emit(SubiVi(d, vsrc, str(-imm), mask))  # Negate imm for commuted form
#     return d

# MULI
@isa.pattern("vecreg", "MULVEC(vecreg, CONSTBF16, maskreg)", size=2,
             condition=lambda t: -4096 <= t.children[1].value <= 4095)
def patt_mul_vi(ctx, tree, vsrc, mask = M0):
    d = _new_v(ctx)
    assert isinstance(tree.children[1].value, float), "Expected a float immediate"
    imm = _f32_to_f16_bits(tree.children[1].value)
    ctx.emit(MuliVi(d, vsrc, imm, mask))
    return d

@isa.pattern("vecreg", "MULVEC(CONSTBF16, vecreg, maskreg)", size=2,
             condition=lambda t: -4096 <= t.children[0].value <= 4095)
def patt_mul_vi_comm(ctx, tree, vsrc, mask = M0):
    d = _new_v(ctx)
    assert isinstance(tree.children[0].value, float), "Expected a float immediate"
    imm = _f32_to_f16_bits(tree.children[0].value)
    ctx.emit(MuliVi(d, vsrc, imm, mask))  # Same imm for commuted form
    return d

# # DIVI
# @isa.pattern("vecreg", "DIVVEC(vecreg, CONSTBF16, stm)", size=2,
#              condition=lambda t: -4096 <= t.children[1].value <= 4095)
# def patt_div_vi(ctx, tree, vsrc, mask = M0):
#     d = _new_v(ctx)
#     assert isinstance(tree.children[1].value, float), "Expected a float immediate"
#     imm = _f32_to_f16_bits(tree.children[1].value)
#     ctx.emit(DiviVi(d, vsrc, imm, mask))
#     return d

# @isa.pattern("vecreg", "DIVVEC(CONSTBF16, vecreg, maskreg)", size=2,
#                 condition=lambda t: -4096 <= t.children[0].value <= 4095
#             )
# def patt_div_vi_comm(ctx, tree, vsrc, mask = M0):
#     d = _new_v(ctx)
#     imm = tree.children[0].value
#     ctx.emit(DiviVi(d, vsrc, str(1/imm), mask))  # Use reciprocal for commuted form
#     return d

# EXP (immediate exponent)
@isa.pattern("vecreg", "EXPVEC(vecreg, CONSTBF16, maskreg)", size=2,
             condition=lambda t: -4096 <= t.children[1].value <= 4095)
def patt_exp_vi(ctx, tree, vsrc, mask = M0):
    d = _new_v(ctx)
    ctx.emit(ExpiVi(d, vsrc, 0, mask))
    return d

# SQRT (mode/precision as imm if your ISA uses it)
@isa.pattern("vecreg", "SQRTVEC(vecreg, CONSTBF16, maskreg)", size=2,
             condition=lambda t: -4096 <= t.children[1].value <= 4095)
def patt_sqrt_vi(ctx, tree, vsrc, mask = M0):
    d = _new_v(ctx)
    ctx.emit(SqrtiVi(d, vsrc, 0, mask))
    return d

# NOT (use imm as a control/mask if required by your ISA; 0 is typical)
@isa.pattern("vecreg", "INVVEC(vecreg, CONSTBF16, maskreg)", size=2)
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

@isa.pattern("vecreg", "RSUMVEC(vecreg, CONSTBF16, maskreg)", size=2)
def patt_rsum_vi(ctx, tree, vsrc, mask = M0):
    d = _new_v(ctx)
    assert isinstance(tree.children[1].value, float), "Expected a float immediate"
    imm = _f32_to_f16_bits(tree.children[1].value)
    ctx.emit(RsumVi(d, vsrc, imm, mask))
    return d

@isa.pattern("vecreg", "RMINVEC(vecreg, CONSTBF16, maskreg)", size=2)
def patt_rmin_vi(ctx, tree, vsrc, mask = M0):
    d = _new_v(ctx)
    assert isinstance(tree.children[1].value, float), "Expected a float immediate"
    imm = _f32_to_f16_bits(tree.children[1].value)
    ctx.emit(RminVi(d, vsrc, imm, mask))
    return d

@isa.pattern("vecreg", "RMAXVEC(vecreg, CONSTBF16, maskreg)", size=2)
def patt_rmax_vi(ctx, tree, vsrc, mask = M0):
    d = _new_v(ctx)
    assert isinstance(tree.children[1].value, float), "Expected a float immediate"
    imm = _f32_to_f16_bits(tree.children[1].value)
    ctx.emit(RmaxVi(d, vsrc, imm, mask))
    return d
# # ---------- VS (vector-scalar) ----------

@isa.pattern("vecreg", "ADDVEC(vecreg, reg, maskreg)", size=2)
def patt_add_vs(ctx, tree, vsrc, rs1, mask = M0):
    d = _new_v(ctx)
    ctx.emit(AddVs(d, vsrc, rs1, mask))
    return d

@isa.pattern("vecreg", "SUBVEC(vecreg, reg, maskreg)", size=2)
def patt_sub_vs(ctx, tree, vsrc, rs1, mask = M0):
    d = _new_v(ctx)
    ctx.emit(SubVs(d, vsrc, rs1, mask))
    return d

@isa.pattern("vecreg", "MULVEC(vecreg, reg, maskreg)", size=2)
def patt_mul_vs(ctx, tree, vsrc, rs1, mask = M0):
    d = _new_v(ctx)
    ctx.emit(MulVs(d, vsrc, rs1, mask))
    return d

# @isa.pattern("vecreg", "DIVVEC(vecreg, reg, stm)", size=2)
# def patt_div_vs(ctx, tree, vsrc, rs1, mask = M0):
#     d = _new_v(ctx)
#     ctx.emit(DivVs(d, vsrc, rs1, mask))
#     return d


class AtallaSDMAInstruction(Instruction):
    tokens = [AtallaSDMAToken]
    isa = isa


def make_sdma(mnemonic: str, opcode: int):
    rs2  = Operand("rs2",  AtallaRegister, read=True)
    rs1_rd1 = Operand("rs1_rd1", AtallaRegister, read=True)
    num_cols = Operand("num_cols", int)
    num_rows = Operand("num_rows", int)
    sid = Operand("sid", int)
    syntax   = Syntax([mnemonic, " ", rs2, ",", " ", rs1_rd1,
                       ",", " ", num_cols,
                       ",", " ", num_rows,
                       ",", " ", sid])
    fprel = False
    patterns = {
        "opcode": opcode,
        "rs2": rs2, "rs1_rd1": rs1_rd1,
        "num_cols": num_cols,
        "sid": sid,
        "num_rows": num_rows
        }
    members  = {"syntax": syntax, "rs2": rs2, "rs1_rd1": rs1_rd1, "patterns": patterns, "opcode": opcode,
                "sid": sid, "num_cols": num_cols, "num_rows": num_rows, "fprel": fprel}
    return type(mnemonic.replace(".", "_"), (AtallaSDMAInstruction,), members)

ScpadLd = make_sdma("scpad_ld", 0b1011000)
ScpadSt = make_sdma("scpad_st", 0b1011001)

class AtallaVTSInstruction(Instruction):
    tokens = [AtallaVTSToken]
    isa = isa

def make_vts(mnemonic: str, opcode: int):
    rd  = Operand("rd",  AtallaRegister, write=True)
    vs1 = Operand("vs1", AtallaVectorRegister, read=True)
    imm8 = Operand("imm8", int)
    syntax   = Syntax([mnemonic, " ", rd, ",", " ", vs1, ",", " ", imm8])
    patterns = {"opcode": opcode, "rd": rd, "vs1": vs1, "imm8": imm8}
    members  = {"syntax": syntax, "rd": rd, "vs1": vs1, "imm8": imm8, "patterns": patterns, "opcode": opcode}
    return type(mnemonic.replace(".", "_"), (AtallaVTSInstruction,), members)

VecIdx = make_vts("vmov_vts", 0b1001111)

@isa.pattern("reg", "VECIDXBF16(vecreg, CONSTI32)", size=2)
def pattern_vecidx(context, tree, vsrc):
    d = context.new_reg(AtallaRegister)
    context.emit(VecIdx(d, vsrc, tree.children[1].value))
    return d