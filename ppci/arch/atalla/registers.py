from ... import ir
from ..registers import Register, RegisterClass

class AtallaRegister(Register):
    bitsize = 64

    def __repr__(self):
        if self.is_colored:
            return get_register(self.color).name
            return f"{self.name}={self.color}"
        else:
            return self.name

    def from_num(cls, num):
        """Retrieve the singleton instance of the given
        register number."""
        return num2regmap[num]

class AtallaProgramCounterRegister(Register):
    bitsize = 32


def get_register(n):
    """Based on a number, get the corresponding register"""
    return num2regmap[n]

def register_range(a, b):
    """Return set of registers from a to b"""
    assert a.num < b.num
    return {get_register(n) for n in range(a.num, b.num + 1)}


R0 = AtallaRegister("x0", num=0, aka=("zero",))
LR = AtallaRegister("x1", num=1, aka=("ra",))
SP = AtallaRegister("x2", num=2, aka=("sp",))
R3 = AtallaRegister("x3", num=3, aka=("gp",))
R4 = AtallaRegister("x4", num=4, aka=("tp",))
R5 = AtallaRegister("x5", num=5, aka=("t0",))
R6 = AtallaRegister("x6", num=6, aka=("t1",))
R7 = AtallaRegister("x7", num=7, aka=("t2",))
FP = AtallaRegister("x8", num=8, aka=("s0", "fp"))
R9 = AtallaRegister("x9", num=9, aka=("s1",))
R10 = AtallaRegister("x10", num=10, aka=("a0",))
R11 = AtallaRegister("x11", num=11, aka=("a1",))
R12 = AtallaRegister("x12", num=12, aka=("a2",))
R13 = AtallaRegister("x13", num=13, aka=("a3",))
R14 = AtallaRegister("x14", num=14, aka=("a4",))
R15 = AtallaRegister("x15", num=15, aka=("a5",))
R16 = AtallaRegister("x16", num=16, aka=("a6",))
R17 = AtallaRegister("x17", num=17, aka=("a7",))
R18 = AtallaRegister("x18", num=18, aka=("s2",))
R19 = AtallaRegister("x19", num=19, aka=("s3",))
R20 = AtallaRegister("x20", num=20, aka=("s4",))
R21 = AtallaRegister("x21", num=21, aka=("s5",))
R22 = AtallaRegister("x22", num=22, aka=("s6",))
R23 = AtallaRegister("x23", num=23, aka=("s7",))
R24 = AtallaRegister("x24", num=24, aka=("s8",))
R25 = AtallaRegister("x25", num=25, aka=("s9",))
R26 = AtallaRegister("x26", num=26, aka=("s10",))
R27 = AtallaRegister("x27", num=27, aka=("s11",))
R28 = AtallaRegister("x28", num=28, aka=("t3",))
R29 = AtallaRegister("x29", num=29, aka=("t4",))
R30 = AtallaRegister("x30", num=30, aka=("t5",))
R31 = AtallaRegister("x31", num=31, aka=("t6",))

SCPADSP = AtallaRegister("x32", num=32, aka=("scpadsp"))
SCPADFP = AtallaRegister("x33", num=33, aka=("scpadfp"))

PC = AtallaProgramCounterRegister("PC", num=34)

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
    SCPADFP,
    SCPADSP,
]
AtallaRegister.registers = registers


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
#     RegisterClass("freg", [ir.f32, ir.f64], AtallaRegister, fregisters),
# ]

register_classes_swfp = [
    RegisterClass(
        "reg",
        [ir.i8, ir.i16, ir.i32, ir.ptr, ir.u8, ir.u16, ir.u32, ir.bf16],
        AtallaRegister,
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
