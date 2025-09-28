from ..token import Token, bit_range

#since our instruction defines imm12 everywhere we will use that in each of the classes.
#we can change later but I'll add a quick fix for it right now

class AtallaSDMAToken(Token):
    class Info:
        size = 64

    opcode   = bit_range(57, 63)
    rd1      = bit_range(49, 56)
    rs1      = bit_range(41, 48)
    rs2      = bit_range(33, 40)
    imm12    = bit_range(15, 32)
    schdImm  = bit_range(0, 4)

class AtallaVMToken(Token):
    class Info:
        size = 64

    opcode   = bit_range(57, 63)
    rd1      = bit_range(49, 56)
    rs1      = bit_range(41, 48)
    rs2      = bit_range(33, 40)
    imm12    = bit_range(15, 32)
    schdImm  = bit_range(0, 4)

class AtallaSAMToken(Token):
    class Info:
        size = 64

    opcode   = bit_range(57, 63)
    rd1      = bit_range(49, 56)
    rs1      = bit_range(41, 48)
    rs2      = bit_range(33, 40)
    imm12    = bit_range(15, 32)
    schdImm  = bit_range(0, 4)

class AtallaTCAToken(Token):
    class Info:
        size = 64

    opcode   = bit_range(57, 63)
    rd1      = bit_range(49, 56)
    rs1      = bit_range(41, 48)
    rs2      = bit_range(33, 40)
    imm12    = bit_range(15, 32)
    schdImm  = bit_range(0, 4)


# Scalar
class AtallaRToken(Token):
    class Info:
        size = 64

    opcode   = bit_range(57, 63)
    rd1      = bit_range(49, 56)
    rs1      = bit_range(41, 48)
    rs2      = bit_range(17, 24)
    imm12    = bit_range(15, 32)
    schdImm  = bit_range(0, 4)

class AtallaBRToken(Token):
    class Info:
        size = 64

    opcode   = bit_range(57, 63)
    rd1      = bit_range(49, 56)
    rs1      = bit_range(41, 48)
    rs2      = bit_range(17, 24)
    imm12    = bit_range(5, 16)
    schdImm  = bit_range(0, 4)

class AtallaIToken(Token):
    class Info:
        size = 64

    opcode   = bit_range(57, 63)
    rd1      = bit_range(49, 56)
    rs1      = bit_range(41, 48)
    rs2      = bit_range(17, 24)
    imm12    = bit_range(5, 16)
    schdImm  = bit_range(0, 4)

class AtallaMToken(Token):
    class Info:
        size = 64

    opcode   = bit_range(57, 63)
    rd1      = bit_range(49, 56)
    rs1      = bit_range(41, 48)
    rs2      = bit_range(17, 24)
    imm12    = bit_range(5, 16)
    schdImm  = bit_range(0, 4)

class AtallaMIToken(Token):
    class Info:
        size = 64

    opcode   = bit_range(57, 63)
    rd1      = bit_range(49, 56)
    imm28    = bit_range(5, 48)
    schdImm  = bit_range(0, 4)

class AtallaJToken(Token):
    class Info:
        size = 64

    opcode   = bit_range(57, 63)
    rd1      = bit_range(49, 56)
    rs1      = bit_range(41, 48)
    imm20    = bit_range(5, 24)
    schdImm  = bit_range(0, 4)

class AtallaFenceToken(Token):
    class Info:
        size = 64

    opcode   = bit_range(57, 63)
    imm      = bit_range(15, 56)
    schdImm  = bit_range(0, 4)

class AtallaHaltToken(Token):
    class Info:
        size = 64

    opcode   = bit_range(57, 63)
    imm      = bit_range(15, 56)
    schdImm  = bit_range(0, 4)

class AtallaNOPToken(Token):
    class Info:
        size = 64

    opcode   = bit_range(57, 63)
    imm      = bit_range(15, 56)
    schdImm  = bit_range(0, 4)
