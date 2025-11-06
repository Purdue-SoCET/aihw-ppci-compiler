from ..encoding import Instruction, Operand, Syntax
from ..isa import Isa

from .tokens import (
    AtallaVVToken,
    AtallaVSToken,
    AtallaVIToken,
    AtallaVMemToken,
)
from .vector_registers import AtallaVectorRegister
from .registers import AtallaRegister

isa = Isa()


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
    imm8 = Operand("imm8", int)
    imm5 = Operand("imm5", int)
    syntax   = Syntax([mnemonic, " ", vd, ",", " ", vs1, ",", " ", imm8, ",", " ", imm5])
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
# VregLd = make_vm("vreg_ld", <opcode>)
# VregSt = make_vm("vreg_st", <opcode>)

def _new_v(context):
    return context.new_reg(AtallaVectorRegister)

def _new_s(context):
    return context.new_reg(AtallaRegister)

def _split_imm13_signed(val: int):
    # 13-bit signed: range [-4096, 4095]
    if val < -4096 or val > 4095:
        raise ValueError("imm13 out of range")
    # two's complement form in 13 bits
    u = val & 0x1FFF
    imm8 = (u >> 5) & 0xFF
    imm5 = u & 0x1F
    return imm8, imm5

# ---------- VV (vector-vector) ----------

@isa.pattern("vreg", "ADDVV(vreg, vreg)", size=2)
def patt_add_vv(ctx, tree, v0, v1):
    d = _new_v(ctx)
    ctx.emit(AddVv(d, v0, v1))
    return d

@isa.pattern("vreg", "SUBVV(vreg, vreg)", size=2)
def patt_sub_vv(ctx, tree, v0, v1):
    d = _new_v(ctx)
    ctx.emit(SubVv(d, v0, v1))
    return d

@isa.pattern("vreg", "MULVV(vreg, vreg)", size=2)
def patt_mul_vv(ctx, tree, v0, v1):
    d = _new_v(ctx)
    ctx.emit(MulVv(d, v0, v1))
    return d

@isa.pattern("vreg", "DIVVV(vreg, vreg)", size=2)
def patt_div_vv(ctx, tree, v0, v1):
    d = _new_v(ctx)
    ctx.emit(DivVv(d, v0, v1))
    return d

@isa.pattern("vreg", "ANDVV(vreg, vreg)", size=2)
def patt_and_vv(ctx, tree, v0, v1):
    d = _new_v(ctx)
    ctx.emit(AndVv(d, v0, v1))
    return d

@isa.pattern("vreg", "ORVV(vreg, vreg)", size=2)
def patt_or_vv(ctx, tree, v0, v1):
    d = _new_v(ctx)
    ctx.emit(OrVv(d, v0, v1))
    return d

@isa.pattern("vreg", "XORVV(vreg, vreg)", size=2)
def patt_xor_vv(ctx, tree, v0, v1):
    d = _new_v(ctx)
    ctx.emit(XorVv(d, v0, v1))
    return d

@isa.pattern("vreg", "GEMMVV(vreg, vreg, vreg)", size=2)
def patt_gemm_vv(ctx, tree, v0, v1, v2):
    d = _new_v(ctx)
    ctx.emit(GemmVv(d, v0, v1, v2))
    return d

@isa.pattern("vreg", "MGTVV(vreg, vreg)", size=2)
def patt_mgt_vv(ctx, tree, v0, v1):
    d = _new_v(ctx)
    ctx.emit(MgtVv(d, v0, v1))
    return d

@isa.pattern("vreg", "MLTVV(vreg, vreg)", size=2)
def patt_mlt_vv(ctx, tree, v0, v1):
    d = _new_v(ctx)
    ctx.emit(MltVv(d, v0, v1))
    return d

@isa.pattern("vreg", "MEQVV(vreg, vreg)", size=2)
def patt_meq_vv(ctx, tree, v0, v1):
    d = _new_v(ctx)
    ctx.emit(MeqVv(d, v0, v1))
    return d

@isa.pattern("vreg", "MNEQVV(vreg, vreg)", size=2)
def patt_mneq_vv(ctx, tree, v0, v1):
    d = _new_v(ctx)
    ctx.emit(MneqVv(d, v0, v1))
    return d

# ---------- VI (vector-immediate; 13-bit signed immediate) ----------

def _emit_vi_binop(ctx, d, vsrc, imm, InsnClass):
    imm8, imm5 = _split_imm13_signed(imm)
    ctx.emit(InsnClass(d, vsrc, imm8, imm5))

# ADDI
@isa.pattern("vreg", "ADDVI(vreg, CONSTI32)", size=2,
             condition=lambda t: -4096 <= t.children[1].value <= 4095)
def patt_add_vi(ctx, tree, vsrc):
    d = _new_v(ctx)
    imm = tree.children[1].value
    _emit_vi_binop(ctx, d, vsrc, imm, AddiVi)
    return d

# SUBI
@isa.pattern("vreg", "SUBVI(vreg, CONSTI32)", size=2,
             condition=lambda t: -4096 <= t.children[1].value <= 4095)
def patt_sub_vi(ctx, tree, vsrc):
    d = _new_v(ctx)
    imm = tree.children[1].value
    _emit_vi_binop(ctx, d, vsrc, imm, SubiVi)
    return d

# MULI
@isa.pattern("vreg", "MULVI(vreg, CONSTI32)", size=2,
             condition=lambda t: -4096 <= t.children[1].value <= 4095)
def patt_mul_vi(ctx, tree, vsrc):
    d = _new_v(ctx)
    imm = tree.children[1].value
    _emit_vi_binop(ctx, d, vsrc, imm, MuliVi)
    return d

# DIVI
@isa.pattern("vreg", "DIVVI(vreg, CONSTI32)", size=2,
             condition=lambda t: -4096 <= t.children[1].value <= 4095)
def patt_div_vi(ctx, tree, vsrc):
    d = _new_v(ctx)
    imm = tree.children[1].value
    _emit_vi_binop(ctx, d, vsrc, imm, DiviVi)
    return d

# EXP (immediate exponent)
@isa.pattern("vreg", "EXPVI(vreg, CONSTI32)", size=2,
             condition=lambda t: -4096 <= t.children[1].value <= 4095)
def patt_exp_vi(ctx, tree, vsrc):
    d = _new_v(ctx)
    imm = tree.children[1].value
    _emit_vi_binop(ctx, d, vsrc, imm, ExpiVi)
    return d

# SQRT (mode/precision as imm if your ISA uses it)
@isa.pattern("vreg", "SQRTVI(vreg, CONSTI32)", size=2,
             condition=lambda t: -4096 <= t.children[1].value <= 4095)
def patt_sqrt_vi(ctx, tree, vsrc):
    d = _new_v(ctx)
    imm = tree.children[1].value
    _emit_vi_binop(ctx, d, vsrc, imm, SqrtiVi)
    return d

# NOT (use imm as a control/mask if required by your ISA; 0 is typical)
@isa.pattern("vreg", "NOTVI(vreg, CONSTI32)", size=2,
             condition=lambda t: -4096 <= t.children[1].value <= 4095)
def patt_not_vi(ctx, tree, vsrc):
    d = _new_v(ctx)
    imm = tree.children[1].value
    _emit_vi_binop(ctx, d, vsrc, imm, NotVi)
    return d

# SHIFT (vector by immediate)
@isa.pattern("vreg", "SHIFTVI(vreg, CONSTI32)", size=2,
             condition=lambda t: -4096 <= t.children[1].value <= 4095)
def patt_shift_vi(ctx, tree, vsrc):
    d = _new_v(ctx)
    imm = tree.children[1].value
    _emit_vi_binop(ctx, d, vsrc, imm, ShiftVi)
    return d

# Fallback for VI when imm doesn't fit: lift to VS by materializing scalar
def _materialize_scalar_const(ctx, val: int):
    s = _new_s(ctx)
    # Reuse your existing scalar constant pattern helpers; if not available, emit li_s/addi_s etc.
    # Here we assume context has a utility to place an immediate into a scalar reg.
    ctx.emit_li(s, val)  # If you don't have ctx.emit_li, replace with your scalar sequence.
    return s

@isa.pattern("vreg", "ADDVI(vreg, CONSTI32)", size=4,
             condition=lambda t: not (-4096 <= t.children[1].value <= 4095))
def patt_add_vi_wide(ctx, tree, vsrc):
    d = _new_v(ctx)
    val = tree.children[1].value
    s = _materialize_scalar_const(ctx, val)
    ctx.emit(ShiftVs(d, vsrc, s))  # Replace with AddVs if/when you add the VS add opcode
    return d

# ---------- VS (vector-scalar) ----------

@isa.pattern("vreg", "SHIFTVS(vreg, reg)", size=2)
def patt_shift_vs(ctx, tree, vsrc, sreg):
    d = _new_v(ctx)
    ctx.emit(ShiftVs(d, vsrc, sreg))
    return d
