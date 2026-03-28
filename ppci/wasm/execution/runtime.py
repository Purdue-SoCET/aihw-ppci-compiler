"""Wasm runtime functions."""

import math
import struct

from ... import ir
from ...utils.bitfun import (
    clz,
    ctz,
    popcnt,
    rotl,
    rotr,
    sign_extend,
    to_signed,
    to_unsigned,
)
from ..util import make_int


class Unreachable(RuntimeError):
    """WASM kernel panic. Having an exception for this allows catching it
    in tests.
    """

    pass


def f16_sqrt(v: ir.bf16) -> ir.bf16:
    """Square root (half precision semantics approximated by Python float)"""
    return math.sqrt(v)


def i32_rotr(v: ir.i32, cnt: ir.i32) -> ir.i32:
    """Rotate right"""
    return to_signed(rotr(to_unsigned(v, 32), cnt, 32), 32)


def i64_rotr(v: ir.i64, cnt: ir.i64) -> ir.i64:
    """Rotate right"""
    return to_signed(rotr(to_unsigned(v, 64), cnt, 64), 64)


def i32_rotl(v: ir.i32, cnt: ir.i32) -> ir.i32:
    """Rotate left"""
    return to_signed(rotl(to_unsigned(v, 32), cnt, 32), 32)


def i64_rotl(v: ir.i64, cnt: ir.i64) -> ir.i64:
    """Rotate left"""
    return to_signed(rotl(to_unsigned(v, 64), cnt, 64), 64)


# Bit counting:
def i32_clz(v: ir.i32) -> ir.i32:
    return clz(v, 32)


def i64_clz(v: ir.i64) -> ir.i64:
    return clz(v, 64)


def i32_ctz(v: ir.i32) -> ir.i32:
    return ctz(v, 32)


def i64_ctz(v: ir.i64) -> ir.i64:
    return ctz(v, 64)


def i32_popcnt(v: ir.i32) -> ir.i32:
    return popcnt(v, 32)


def i64_popcnt(v: ir.i64) -> ir.i64:
    return popcnt(v, 64)


# Conversions: trunc from bf16 to integers
def i32_trunc_f16_s(value: ir.bf16) -> ir.i32:
    if math.isinf(value):
        return 0  # undefined
    else:
        return int(value)


def i32_trunc_f16_u(value: ir.bf16) -> ir.i32:
    if math.isinf(value):
        return 0  # undefined
    else:
        return make_int(value, 32)


def i64_trunc_f16_s(value: ir.bf16) -> ir.i64:
    if math.isinf(value):
        return 0  # undefined
    else:
        return int(value)


def i64_trunc_f16_u(value: ir.bf16) -> ir.i64:
    if math.isinf(value):
        return 0  # undefined
    else:
        return make_int(value, 64)


# saturated trunc


def satured_truncate(value: float, lower_limit, upper_limit) -> int:
    if math.isinf(value):
        if value > 0:
            return upper_limit
        else:
            return lower_limit
    if value > upper_limit:
        return upper_limit
    elif value < lower_limit:
        return lower_limit
    else:
        return int(value)


MAX_I32 = 2**31 - 1
MIN_I32 = -(2**31)
MAX_U32 = 2**32 - 1
MIN_U32 = 0


def i32_trunc_sat_f16_s(v: ir.bf16) -> ir.i32:
    return satured_truncate(v, MIN_I32, MAX_I32)


def i32_trunc_sat_f16_u(v: ir.bf16) -> ir.i32:
    return make_int(satured_truncate(v, MIN_U32, MAX_U32), 32)


MAX_I64 = 2**63 - 1
MIN_I64 = -(2**63)
MAX_U64 = 2**64 - 1
MIN_U64 = 0


def i64_trunc_sat_f16_s(v: ir.bf16) -> ir.i64:
    return satured_truncate(v, MIN_I64, MAX_I64)


def i64_trunc_sat_f16_u(v: ir.bf16) -> ir.i64:
    return make_int(satured_truncate(v, MIN_U64, MAX_U64), 64)


# Promote / demote (for bf16 only there is no larger/smaller pair here)
def f16_promote_f16(v: ir.bf16) -> ir.bf16:
    return v


def f16_demote_f16(v: ir.bf16) -> ir.bf16:
    return v


# Reinterpret: implement half-precision (bf16) <-> i16 bitcasts.
# helper conversions between Python float and IEEE-754 binary16 bitpattern


def _f32_to_f16_bits(f32: float) -> int:
    # Pack float32 into bytes (native endian)
    f32_bytes = struct.pack('>f', f32)  # big-endian ensures MSB is first
    # Unpack as unsigned 32-bit int
    u32 = struct.unpack('>I', f32_bytes)[0]
    # Take the top 16 bits as bf16
    bf16 = u32 >> 16
    return bf16



def _f16_bits_to_float(b16: int) -> float:
    if not (0 <= b16 <= 0xFFFF):
        raise ValueError("Input must be a 16-bit integer")

    # bfloat16 uses the top 16 bits of a float32:
    u32 = b16 << 16  # shift to high half of 32-bit float

    # reinterpret as float
    import struct
    return struct.unpack(">f", struct.pack(">I", u32))[0]


def f16_reinterpret_i16(v: ir.bf16) -> ir.i16:
    # reinterpret the half-float v as signed 16-bit integer preserving bits
    bits = _f32_to_f16_bits(float(v))
    # convert to signed 16
    if bits & 0x8000:
        return bits - (1 << 16)
    return bits


def i16_reinterpret_f16(v: ir.i16) -> ir.bf16:
    bits = v & 0xFFFF
    return _f16_bits_to_float(bits)


def f16_copysign(x: ir.bf16, y: ir.bf16) -> ir.bf16:
    return math.copysign(x, y)


def f16_min(x: ir.bf16, y: ir.bf16) -> ir.bf16:
    return min(x, y)


def f16_max(x: ir.bf16, y: ir.bf16) -> ir.bf16:
    return max(x, y)


def f16_abs(x: ir.bf16) -> ir.bf16:
    return math.fabs(x)


def f16_floor(x: ir.bf16) -> ir.bf16:
    if math.isinf(x):
        return x
    else:
        return float(math.floor(x))


def f16_ceil(x: ir.bf16) -> ir.bf16:
    if math.isinf(x):
        return x
    else:
        return float(math.ceil(x))


def f16_nearest(x: ir.bf16) -> ir.bf16:
    if math.isinf(x):
        return x
    else:
        return float(round(x))


def f16_trunc(x: ir.bf16) -> ir.bf16:
    if math.isinf(x):
        return x
    else:
        return float(math.trunc(x))


def unreachable() -> None:
    raise Unreachable("WASM KERNEL panic!")


def i32_extend8_s(x: ir.i32) -> ir.i32:
    return sign_extend(x, 8)


def i32_extend16_s(x: ir.i32) -> ir.i32:
    return sign_extend(x, 16)


def i64_extend8_s(x: ir.i64) -> ir.i64:
    return sign_extend(x, 8)


def i64_extend16_s(x: ir.i64) -> ir.i64:
    return sign_extend(x, 16)


def i64_extend32_s(x: ir.i64) -> ir.i64:
    return sign_extend(x, 32)


# See also:
# https://github.com/kanaka/warpy/blob/master/warpy.py
def create_runtime():
    """Create runtime functions.

    These are functions required by some wasm instructions which cannot
    be code generated directly or are too complex.
    """

    runtime = {
        "f16_sqrt": f16_sqrt,
        "i32_rotl": i32_rotl,
        "i64_rotl": i64_rotl,
        "i32_rotr": i32_rotr,
        "i64_rotr": i64_rotr,
        "i32_clz": i32_clz,
        "i64_clz": i64_clz,
        "i32_ctz": i32_ctz,
        "i64_ctz": i64_ctz,
        "i32_popcnt": i32_popcnt,
        "i64_popcnt": i64_popcnt,
        "i32_trunc_f16_s": i32_trunc_f16_s,
        "i32_trunc_f16_u": i32_trunc_f16_u,
        "i64_trunc_f16_s": i64_trunc_f16_s,
        "i64_trunc_f16_u": i64_trunc_f16_u,
        "f16_promote_f16": f16_promote_f16,
        "f16_demote_f16": f16_demote_f16,
        "f16_reinterpret_i16": f16_reinterpret_i16,
        "i16_reinterpret_f16": i16_reinterpret_f16,
        "f16_copysign": f16_copysign,
        "f16_min": f16_min,
        "f16_max": f16_max,
        "f16_abs": f16_abs,
        "f16_floor": f16_floor,
        "f16_nearest": f16_nearest,
        "f16_ceil": f16_ceil,
        "f16_trunc": f16_trunc,
        "unreachable": unreachable,
        "i32_extend8_s": i32_extend8_s,
        "i32_extend16_s": i32_extend16_s,
        "i64_extend8_s": i64_extend8_s,
        "i64_extend16_s": i64_extend16_s,
        "i64_extend32_s": i64_extend32_s,
        "i32_trunc_sat_f16_s": i32_trunc_sat_f16_s,
        "i32_trunc_sat_f16_u": i32_trunc_sat_f16_u,
        "i64_trunc_sat_f16_s": i64_trunc_sat_f16_s,
        "i64_trunc_sat_f16_u": i64_trunc_sat_f16_u,
    }

    return runtime
