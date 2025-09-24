from ..token import Token, bit_range

#since our instruction defines imm12 everywhere we will use that in each of the classes.
#we can change later but I'll add a quick fix for it right now

class AmpSDMAToken(Token):
    class Info:
        size = 64

    reserved = bit_range(0, 0)
    opcode   = bit_range(57, 63)
    rd1      = bit_range(49, 56)
    rs1      = bit_range(41, 48)
    rs2      = bit_range(33, 40)
    imm12    = bit_range(15, 32)
    schdImm  = bit_range(0, 14)

class AmpVMToken(Token):
    class Info:
        size = 64

    reserved = bit_range(0, 0)
    opcode   = bit_range(57, 63)
    rd1      = bit_range(49, 56)
    rs1      = bit_range(41, 48)
    rs2      = bit_range(33, 40)
    imm12    = bit_range(15, 32)
    schdImm  = bit_range(0, 14)

class AmpSAMToken(Token):
    class Info:
        size = 64

    reserved = bit_range(0, 0)
    opcode   = bit_range(57, 63)
    rd1      = bit_range(49, 56)
    rs1      = bit_range(41, 48)
    rs2      = bit_range(33, 40)
    imm12    = bit_range(15, 32)
    schdImm  = bit_range(0, 14)

class AmpTCAToken(Token):
    class Info:
        size = 64

    reserved = bit_range(0, 0)
    opcode   = bit_range(57, 63)
    rd1      = bit_range(49, 56)
    rs1      = bit_range(41, 48)
    rs2      = bit_range(33, 40)
    imm12    = bit_range(15, 32)
    schdImm  = bit_range(0, 14)


# Scalar
class AmpRToken(Token):
    class Info:
        size = 64

    reserved = bit_range(0, 0)
    opcode   = bit_range(57, 63)
    rd1      = bit_range(49, 56)
    rs1      = bit_range(41, 48)
    rs2      = bit_range(17, 24)
    imm12    = bit_range(15, 32)
    schdImm  = bit_range(0, 14)

class AmpBRToken(Token):
    class Info:
        size = 64

    reserved = bit_range(0, 0)
    opcode   = bit_range(57, 63)
    rd1      = bit_range(49, 56)
    rs1      = bit_range(41, 48)
    rs2      = bit_range(17, 24)
    imm12    = bit_range(5, 16)
    schdImm  = bit_range(0, 14)

class AmpIToken(Token):
    class Info:
        size = 64

    reserved = bit_range(0, 0)
    opcode   = bit_range(57, 63)
    rd1      = bit_range(49, 56)
    rs1      = bit_range(41, 48)
    rs2      = bit_range(17, 24)
    imm12    = bit_range(5, 16)
    schdImm  = bit_range(0, 14)

class AmpMToken(Token):
    class Info:
        size = 64

    reserved = bit_range(0, 0)
    opcode   = bit_range(57, 63)
    rd1      = bit_range(49, 56)
    rs1      = bit_range(41, 48)
    rs2      = bit_range(17, 24)
    imm12    = bit_range(5, 16)
    schdImm  = bit_range(0, 14)

class AmpMIToken(Token):
    class Info:
        size = 64

    reserved = bit_range(0, 0)
    opcode   = bit_range(57, 63)
    rd1      = bit_range(49, 56)
    imm28    = bit_range(5, 48)
    schdImm  = bit_range(0, 14)

class AmpJToken(Token):
    class Info:
        size = 64

    reserved = bit_range(0, 0)
    opcode   = bit_range(57, 63)
    rd1      = bit_range(49, 56)
    rs1      = bit_range(41, 48)
    imm20    = bit_range(5, 24)
    schdImm  = bit_range(0, 14)

class AmpFenceToken(Token):
    class Info:
        size = 64

    reserved = bit_range(0, 0)
    opcode   = bit_range(57, 63)
    imm      = bit_range(15, 56)
    schdImm  = bit_range(0, 14)

class AmpHaltToken(Token):
    class Info:
        size = 64

    reserved = bit_range(0, 0)
    opcode   = bit_range(57, 63)
    imm      = bit_range(15, 56)
    schdImm  = bit_range(0, 14)

class AmpNOPToken(Token):
    class Info:
        size = 64

    reserved = bit_range(0, 0)
    opcode   = bit_range(57, 63)
    imm      = bit_range(15, 56)
    schdImm  = bit_range(0, 14)
