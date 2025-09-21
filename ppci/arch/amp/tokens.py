from ..token import Token, bit_range

class AmpSDMAToken(Token):
    class Info:
        size = 64

    reserved = bit_range(48, 63)
    opcode = bit_range(41, 47)
    rd1 = bit_range(33, 40)
    rs1 = bit_range(25, 32)
    rs2 = bit_range(17, 24)
    imm12 = bit_range(5, 16)
    schdImm = bit_range(0, 4)

class AmpVMToken(Token):
    class Info:
        size = 64

    reserved = bit_range(48, 63)
    opcode = bit_range(41, 47)
    rd1 = bit_range(33, 40)
    rs1 = bit_range(25, 32)
    rs2 = bit_range(17, 24)
    imm12 = bit_range(5, 16)
    schdImm = bit_range(0, 4)

class AmpSAMToken(Token):
    class Info:
        size = 64

    reserved = bit_range(48, 63)
    opcode = bit_range(41, 47)
    rd1 = bit_range(33, 40)
    rs1 = bit_range(25, 32)
    rs2 = bit_range(17, 24)
    imm12 = bit_range(5, 16)
    schdImm = bit_range(0, 4)

class AmpTCAToken(Token):
    class Info:
        size = 64

    reserved = bit_range(48, 63)
    opcode = bit_range(41, 47)
    rd1 = bit_range(33, 40)
    rs1 = bit_range(25, 32)
    rs2 = bit_range(17, 24)
    imm12 = bit_range(5, 16)
    schdImm = bit_range(0, 4)


# Scalar
class AmpRToken(Token):
    class Info:
        size = 64

    reserved = bit_range(48, 63)
    opcode = bit_range(41, 47)
    rd1 = bit_range(33, 40)
    rs1 = bit_range(25, 32)
    rs2 = bit_range(17, 24)
    imm12 = bit_range(5, 16)
    schdImm = bit_range(0, 4)

class AmpBRToken(Token):
    class Info:
        size = 64

    reserved = bit_range(48, 63)
    opcode = bit_range(41, 47)
    rd1 = bit_range(33, 40)
    rs1 = bit_range(25, 32)
    rs2 = bit_range(17, 24)
    imm12 = bit_range(5, 16)
    schdImm = bit_range(0, 4)

class AmpIToken(Token):
    class Info:
        size = 64

    reserved = bit_range(48, 63)
    opcode = bit_range(41, 47)
    rd1 = bit_range(33, 40)
    rs1 = bit_range(25, 32)
    rs2 = bit_range(17, 24)
    imm12 = bit_range(5, 16)
    schdImm = bit_range(0, 4)

class AmpMToken(Token):
    class Info:
        size = 64

    reserved = bit_range(48, 63)
    opcode = bit_range(41, 47)
    rd1 = bit_range(33, 40)
    rs1 = bit_range(25, 32)
    rs2 = bit_range(17, 24)
    imm12 = bit_range(5, 16)
    schdImm = bit_range(0, 4)

class AmpMIToken(Token):
    class Info:
        size = 64

    reserved = bit_range(48, 63)
    opcode = bit_range(41, 47)
    rd1 = bit_range(33, 40)
    imm28 = bit_range(5, 32)
    schdImm = bit_range(0, 4)

class AmpJToken(Token):
    class Info:
        size = 64

    reserved = bit_range(48, 63)
    opcode = bit_range(41, 47)
    rd1 = bit_range(33, 40)
    rs1 = bit_range(25, 32)
    imm20 = bit_range(5, 24)
    schdImm = bit_range(0, 4)

class AmpFenceToken(Token):
    class Info:
        size = 64

    reserved = bit_range(48, 63)
    opcode = bit_range(41, 47)
    #WIP
    imm = bit_range(5, 40)
    schdImm = bit_range(0, 4)

class AmpHaltToken(Token):
    class Info:
        size = 64

    reserved = bit_range(48, 63)
    opcode = bit_range(41, 47)
    #WIP
    imm = bit_range(5, 40)
    schdImm = bit_range(0, 4)

class AmpNOPToken(Token):
    class Info:
        size = 64

    reserved = bit_range(48, 63)
    opcode = bit_range(41, 47)
    #WIP
    imm = bit_range(5, 40)
    schdImm = bit_range(0, 4)
