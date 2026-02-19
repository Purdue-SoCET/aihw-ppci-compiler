from ... import ir
from ..registers import Register, RegisterClass

class AtallaVectorRegister(Register):
    """Vector register for SIMD operations"""
    bitsize = 32 * 16

    def __repr__(self):
        if self.is_colored:
            return f"v{self.color}"
        else:
            return self.name
    
    @classmethod
    def from_num(cls, num):
        return num2regmap[num]

def get_vec_register(n):
    """Based on a number, get the corresponding register"""
    return num2regmap[n]

def register_range(a, b):
    """Return set of registers from a to b"""
    assert a.num < b.num
    return {get_vec_register(n) for n in range(a.num, b.num + 1)}

V0 = AtallaVectorRegister("v0", num=0)
V1 = AtallaVectorRegister("v1", num=1)
V2 = AtallaVectorRegister("v2", num=2)
V3 = AtallaVectorRegister("v3", num=3)
V4 = AtallaVectorRegister("v4", num=4)
V5 = AtallaVectorRegister("v5", num=5)
V6 = AtallaVectorRegister("v6", num=6)
V7 = AtallaVectorRegister("v7", num=7)
V8 = AtallaVectorRegister("v8", num=8)
V9 = AtallaVectorRegister("v9", num=9)
V10 = AtallaVectorRegister("v10", num=10)
V11 = AtallaVectorRegister("v11", num=11)
V12 = AtallaVectorRegister("v12", num=12)
V13 = AtallaVectorRegister("v13", num=13)
V14 = AtallaVectorRegister("v14", num=14)
V15 = AtallaVectorRegister("v15", num=15)
V16 = AtallaVectorRegister("v16", num=16)
V17 = AtallaVectorRegister("v17", num=17)
V18 = AtallaVectorRegister("v18", num=18)
V19 = AtallaVectorRegister("v19", num=19)
V20 = AtallaVectorRegister("v20", num=20)
V21 = AtallaVectorRegister("v21", num=21)
V22 = AtallaVectorRegister("v22", num=22)
V23 = AtallaVectorRegister("v23", num=23)
V24 = AtallaVectorRegister("v24", num=24)
V25 = AtallaVectorRegister("v25", num=25)
V26 = AtallaVectorRegister("v26", num=26)
V27 = AtallaVectorRegister("v27", num=27)
V28 = AtallaVectorRegister("v28", num=28)
V29 = AtallaVectorRegister("v29", num=29)
V30 = AtallaVectorRegister("v30", num=30)
V31 = AtallaVectorRegister("v31", num=31)

vector_registers = [
    V0, V1, V2, V3, V4, V5, V6, V7,
    V8, V9, V10, V11, V12, V13, V14, V15,
    V16, V17, V18, V19, V20, V21, V22, V23,
    V24, V25, V26, V27, V28, V29, V30, V31
]

AtallaVectorRegister.registers = vector_registers

num2regmap = {r.num: r for r in vector_registers}


vector_register_class = RegisterClass(
    "vecreg",
    [ir.vec],
    AtallaVectorRegister,
    [V1, V2, V3, V4, V5, V6, V7, V8, V9, V10,
     V11, V12, V13, V14, V15, V16, V17, V18, V19, V20,
     V21, V22, V23, V24, V25, V26, V27, V28, V29, V30, V31]
)

vector_register_classes = [vector_register_class]
