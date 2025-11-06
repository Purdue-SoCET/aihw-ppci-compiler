from ..token import Token, bit_range

class AtallaRToken(Token):
    class Info:
        size = 40
    opcode = bit_range(0, 7)
    rd1    = bit_range(7, 15)
    rs1    = bit_range(15, 23)
    rs2    = bit_range(23, 31)
    reserved = bit_range(31, 40)

class AtallaBRToken(Token):
    class Info:
        size = 40
    opcode     = bit_range(0, 7)
    incr_imm7  = bit_range(7, 14)
    i1         = bit_range(14, 15)
    rs1        = bit_range(15, 23)
    rs2        = bit_range(23, 31)
    imm9       = bit_range(31, 40)

class AtallaIToken(Token):
    class Info:
        size = 40
    opcode = bit_range(0, 7)
    rd1    = bit_range(7, 15)
    rs1    = bit_range(15, 23)
    imm12  = bit_range(23, 35)
    reserved = bit_range(35, 40)

class AtallaMToken(Token):
    class Info:
        size = 40
    opcode = bit_range(0, 7)
    rd1    = bit_range(7, 15)
    rs1    = bit_range(15, 23)
    imm12  = bit_range(23, 35)
    reserved = bit_range(35, 40)
class AtallaMIToken(Token):
    class Info:
        size = 40
    opcode = bit_range(0, 7)
    rd1    = bit_range(7, 15)
    imm25  = bit_range(15, 40)

class AtallaSToken(Token):
    class Info:
        size = 40
    opcode = bit_range(0, 7)
    imm    = bit_range(7, 40)

#vector
class AtallaVVToken(Token):

    class Info:
        size = 40
    opcode = bit_range(0, 7)
    vd     = bit_range(7, 15)
    vs1    = bit_range(15, 23)
    vs2    = bit_range(23, 31)
    mask   = bit_range(31, 35)
    sac    = bit_range(35, 36)
    reserved = bit_range(36, 40)
class AtallaVSToken(Token):
    class Info:
        size = 40
    opcode = bit_range(0, 7)
    vd     = bit_range(7, 15)
    vs1    = bit_range(15, 23)
    rs1    = bit_range(23, 31)
    mask   = bit_range(31, 35)
    reserved = bit_range(35, 40)

class AtallaVIToken(Token):
    class Info:
        size = 40
    opcode = bit_range(0, 7)
    vd     = bit_range(7, 15)
    vs1    = bit_range(15, 23)
    imm8   = bit_range(23, 31)
    mask   = bit_range(31, 35)
    imm5   = bit_range(35, 40)

class AtallaVMemToken(Token):
    class Info:
        size = 40
    opcode = bit_range(0, 7)
    vd     = bit_range(7, 15)
    rs1    = bit_range(15, 23)
    tile_r_c_count = bit_range(23, 28)
    rc         = bit_range(28, 29)
    sp         = bit_range(29, 31)
    mask       = bit_range(31, 35)
    rc_id  = bit_range(35, 40)

#next
class AtallaSDMAToken(Token):
    class Info:
        size = 40
    opcode = bit_range(0, 7)
    rs1_rd1 = bit_range(7, 15)
    rs2      = bit_range(15, 23)
    num_rows = bit_range(23, 28)
    num_cols = bit_range(28, 33)
    sid = bit_range(33, 34)
    reserved = bit_range(34, 40)


class AtallaMTSToken(Token):
    class Info:
        size = 40
    opcode = bit_range(0, 7)
    rd1    = bit_range(7, 15)
    vs1    = bit_range(15, 23)
    reserved = bit_range(23, 40)

class AtallaSTMToken(Token):
    class Info:
        size = 40
    opcode = bit_range(0, 7)
    vd     = bit_range(7, 15)
    rs1    = bit_range(15, 23)
    reserved = bit_range(23, 40)
