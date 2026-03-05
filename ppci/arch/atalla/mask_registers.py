from ... import ir
from ..registers import Register, RegisterClass

class AtallaMaskRegister(Register):
    """mask register for SIMD operations"""
    bitsize = 32

    def __repr__(self):
        if self.is_colored:
            return f"m{self.color}"
        else:
            return self.name
    
    @classmethod
    def from_num(cls, num):
        return num2regmap[num]

def get_mask_register(n):
    """Based on a number, get the corresponding register"""
    return num2regmap[n]

def register_range(a, b):
    """Return set of registers from a to b"""
    assert a.num < b.num
    return {get_mask_register(n) for n in range(a.num, b.num + 1)}

M0 = AtallaMaskRegister("m0", num=0)
M1 = AtallaMaskRegister("m1", num=1)
M2 = AtallaMaskRegister("m2", num=2)
M3 = AtallaMaskRegister("m3", num=3)
M4 = AtallaMaskRegister("m4", num=4)
M5 = AtallaMaskRegister("m5", num=5)
M6 = AtallaMaskRegister("m6", num=6)
M7 = AtallaMaskRegister("m7", num=7)
M8 = AtallaMaskRegister("m8", num=8)
M9 = AtallaMaskRegister("m9", num=9)
M10 = AtallaMaskRegister("m10", num=10)
M11 = AtallaMaskRegister("m11", num=11)
M12 = AtallaMaskRegister("m12", num=12)
M13 = AtallaMaskRegister("m13", num=13)
M14 = AtallaMaskRegister("m14", num=14)
M15 = AtallaMaskRegister("m15", num=15)
M16 = AtallaMaskRegister("m16", num=16)
# m17 = AtallaMaskRegister("m17", num=17)
# m18 = AtallaMaskRegister("m18", num=18)
# m19 = AtallaMaskRegister("m19", num=19)
# m20 = AtallaMaskRegister("m20", num=20)
# m21 = AtallaMaskRegister("m21", num=21)
# m22 = AtallaMaskRegister("m22", num=22)
# m23 = AtallaMaskRegister("m23", num=23)
# m24 = AtallaMaskRegister("m24", num=24)
# m25 = AtallaMaskRegister("m25", num=25)
# m26 = AtallaMaskRegister("m26", num=26)
# m27 = AtallaMaskRegister("m27", num=27)
# m28 = AtallaMaskRegister("m28", num=28)
# m29 = AtallaMaskRegister("m29", num=29)
# m30 = AtallaMaskRegister("m30", num=30)
# m31 = AtallaMaskRegister("m31", num=31)

mask_registers = [
    M0, M1, M2, M3, M4, M5, M6, M7,
    M8, M9, M10, M11, M12, M13, M14, M15,
    M16
]

AtallaMaskRegister.registers = mask_registers

num2regmap = {r.num: r for r in mask_registers}


mask_register_class = RegisterClass(
    "maskreg",
    [ir.mask],
    AtallaMaskRegister,
    [M1, M2, M3, M4, M5, M6, M7, M8, M9,
     M10, M11, M12, M13, M14, M15, M16]
)

mask_register_classes = [mask_register_class]
