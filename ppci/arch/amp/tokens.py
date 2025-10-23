from ..token import Token, bit_range

class AtallaRToken(Token):
    class Info:
        size = 40
    opcode = bit_range(0, 6)
    rd1    = bit_range(7, 14)
    rs1    = bit_range(15, 22)
    rs2    = bit_range(23, 30)
    reserved = bit_range(31, 39)

class AtallaBRToken(Token):
    class Info:
        size = 40
    opcode     = bit_range(0, 6)
    incr_imm7  = bit_range(7, 13)
    i1         = bit_range(14, 14)
    rs1        = bit_range(15, 22)
    rs2        = bit_range(23, 30)
    imm9       = bit_range(31, 39)

class AtallaIToken(Token):
    class Info:
        size = 40
    opcode = bit_range(0, 6)
    rd1    = bit_range(7, 14)
    rs1    = bit_range(15, 22)
    imm12  = bit_range(23, 34)
    reserved = bit_range(35, 39)

class AtallaMToken(Token):
    class Info:
        size = 40
    opcode = bit_range(0, 6)
    rd1    = bit_range(7, 14)
    rs1    = bit_range(15, 22)
    imm12  = bit_range(23, 34)
    reserved = bit_range(35, 39)

class AtallaMIToken(Token):
    class Info:
        size = 40
    opcode = bit_range(0, 6)
    rd1    = bit_range(7, 14)
    imm25  = bit_range(15, 39)

class AtallaSToken(Token):
    class Info:
        size = 40
    opcode = bit_range(0, 6)
    imm    = bit_range(7, 39)

#vector
class AtallaVVToken(Token):

    class Info:
        size = 40
    opcode = bit_range(0, 6)
    vd     = bit_range(7, 14)
    vs1    = bit_range(15, 22)
    vs2    = bit_range(23, 30)
    mask   = bit_range(31, 34)
    sac    = bit_range(35, 35)
    reserved = bit_range(36, 39)

class AtallaVSToken(Token):
    class Info:
        size = 40
    opcode = bit_range(0, 6)
    vd     = bit_range(7, 14)
    vs1    = bit_range(15, 22)
    rs1    = bit_range(23, 30)
    mask   = bit_range(31, 34)
    reserved = bit_range(35, 39)

class AtallaVIToken(Token):
    class Info:
        size = 40
    opcode = bit_range(0, 6)
    vd     = bit_range(7, 14)
    vs1    = bit_range(15, 22)
    imm8   = bit_range(23, 30)
    mask   = bit_range(31, 34)
    imm5   = bit_range(35, 39)

class AtallaVMemToken(Token):
    class Info:
        size = 40
    opcode = bit_range(0, 6)
    vd     = bit_range(7, 14)
    rs1    = bit_range(15, 22)
    tile_r_c_count = bit_range(23, 27)
    rc         = bit_range(28, 28)
    sp         = bit_range(29, 30)
    mask       = bit_range(31, 34)
    rc_id  = bit_range(35, 39)

#next
class AtallaSDMAToken(Token):
    class Info:
        size = 40
    opcode = bit_range(0, 6)
    rs1_rd1 = bit_range(7, 14)
    rs2      = bit_range(15, 22)
    num_rows = bit_range(23, 27)
    num_cols = bit_range(28, 32)
    sid = bit_range(33, 33)
    reserved = bit_range(34, 39)


class AtallaMTSToken(Token):
    class Info:
        size = 40
    opcode = bit_range(0, 6)
    rd1    = bit_range(7, 14)
    vs1    = bit_range(15, 22)
    reserved = bit_range(23, 39)

class AtallaSTMToken(Token):
    class Info:
        size = 40
    opcode = bit_range(0, 6)
    vd     = bit_range(7, 14)
    rs1    = bit_range(15, 22)
    reserved = bit_range(23, 39)
