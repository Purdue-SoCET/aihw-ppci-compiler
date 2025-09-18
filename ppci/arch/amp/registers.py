from ... import ir
from ..registers import Register, RegisterClass

class AmpRegister(Register):
    bitsize = 64

    def __repr__(self):
        if self.is_colored:
            return get_register(self.color).name
            return f"{self.name}={self.color}"
        else:
            return self.name

class AmpProgramCounterRegister(Register):
    bitsize = 32


def get_register(n):
    """Based on a number, get the corresponding register"""
    return num2regmap[n]

def register_range(a, b):
    """Return set of registers from a to b"""
    assert a.num < b.num
    return {get_register(n) for n in range(a.num, b.num + 1)}


R0 = AmpRegister("x0", num=0, aka=("zero",))
LR = AmpRegister("x1", num=1, aka=("ra",))
SP = AmpRegister("x2", num=2, aka=("sp",))
R3 = AmpRegister("x3", num=3, aka=("gp",))
R4 = AmpRegister("x4", num=4, aka=("tp",))
R5 = AmpRegister("x5", num=5, aka=("t0",))
R6 = AmpRegister("x6", num=6, aka=("t1",))
R7 = AmpRegister("x7", num=7, aka=("t2",))
FP = AmpRegister("x8", num=8, aka=("s0", "fp"))
R9 = AmpRegister("x9", num=9, aka=("s1",))
R10 = AmpRegister("x10", num=10, aka=("a0",))
R11 = AmpRegister("x11", num=11, aka=("a1",))
R12 = AmpRegister("x12", num=12, aka=("a2",))
R13 = AmpRegister("x13", num=13, aka=("a3",))
R14 = AmpRegister("x14", num=14, aka=("a4",))
R15 = AmpRegister("x15", num=15, aka=("a5",))
R16 = AmpRegister("x16", num=16, aka=("a6",))
R17 = AmpRegister("x17", num=17, aka=("a7",))
R18 = AmpRegister("x18", num=18, aka=("s2",))
R19 = AmpRegister("x19", num=19, aka=("s3",))
R20 = AmpRegister("x20", num=20, aka=("s4",))
R21 = AmpRegister("x21", num=21, aka=("s5",))
R22 = AmpRegister("x22", num=22, aka=("s6",))
R23 = AmpRegister("x23", num=23, aka=("s7",))
R24 = AmpRegister("x24", num=24, aka=("s8",))
R25 = AmpRegister("x25", num=25, aka=("s9",))
R26 = AmpRegister("x26", num=26, aka=("s10",))
R27 = AmpRegister("x27", num=27, aka=("s11",))
R28 = AmpRegister("x28", num=28, aka=("t3",))
R29 = AmpRegister("x29", num=29, aka=("t4",))
R30 = AmpRegister("x30", num=30, aka=("t5",))
R31 = AmpRegister("x31", num=31, aka=("t6",))

PC = AmpProgramCounterRegister("PC", num=32)

registers = [
    R0,
    LR,
    SP,
    R3,
    R4,
    R5,
    R6,
    R7,
    FP,
    R9,
    R10,
    R11,
    R12,
    R13,
    R14,
    R15,
    R16,
    R17,
    R18,
    R19,
    R20,
    R21,
    R22,
    R23,
    R24,
    R25,
    R26,
    R27,
    R28,
    R29,
    R30,
    R31,
]
AmpRegister.registers = registers


num2regmap = {r.num: r for r in registers}

gdb_registers = registers + [PC]


# register_classes_hwfp = [
#     RegisterClass(
#         "reg",
#         [ir.i8, ir.i16, ir.i32, ir.ptr, ir.u8, ir.u16, ir.u32],
#         RiscvRegister,
#         [
#             R9,
#             R10,
#             R11,
#             R12,
#             R13,
#             R14,
#             R15,
#             R16,
#             R17,
#             R18,
#             R19,
#             R20,
#             R21,
#             R22,
#             R23,
#             R24,
#             R25,
#             R26,
#             R27,
#         ],
#     ),
#     RegisterClass("freg", [ir.f32, ir.f64], AmpRegister, fregisters),
# ]

register_classes_swfp = [
    RegisterClass(
        "reg",
        [ir.i8, ir.i16, ir.i32, ir.ptr, ir.u8, ir.u16, ir.u32, ir.f32, ir.f64],
        AmpRegister,
        [
            R9,
            R10,
            R11,
            R12,
            R13,
            R14,
            R15,
            R16,
            R17,
            R18,
            R19,
            R20,
            R21,
            R22,
            R23,
            R24,
            R25,
            R26,
            R27,
        ],
    )
]
