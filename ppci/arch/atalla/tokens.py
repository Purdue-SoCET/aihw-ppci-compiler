from ..token import Token, bit_concat, bit_range

class AtallaRToken(Token):
    class Info:
        size = 40
    opcode = bit_range(0, 7)
    rd     = bit_range(7, 15)
    rs1    = bit_range(15, 23)
    rs2    = bit_range(23, 31)

class AtallaBRToken(Token):
    class Info:
        size = 40
    opcode    = bit_range(0, 7)
    incr_imm7 = bit_range(7, 14)
    rs1_rd    = bit_range(15, 23)
    rs2       = bit_range(23, 31)
    imm10     = bit_concat(bit_range(31, 40), bit_range(14,15))

class AtallaIToken(Token):
    class Info:
        size = 40
    opcode = bit_range(0, 7)
    rd     = bit_range(7, 15)
    rs1    = bit_range(15, 23)
    imm12  = bit_range(23, 35)

class AtallaMToken(Token):
    class Info:
        size = 40
    opcode = bit_range(0, 7)
    rd     = bit_range(7, 15)
    rs1    = bit_range(15, 23)
    imm12  = bit_range(23, 35)

class AtallaMIToken(Token):
    class Info:
        size = 40
    opcode = bit_range(0, 7)
    rd     = bit_range(7, 15)
    imm25  = bit_range(15, 40)

class AtallaSToken(Token):
    class Info:
        size = 40
    opcode = bit_range(0, 7)

# Vector Instructions
class AtallaVVToken(Token):
    class Info:
        size = 40
    opcode = bit_range(0, 7)
    vd     = bit_range(7, 15)
    vs1    = bit_range(15, 23)
    vs2    = bit_range(23, 31)
    mask_reg   = bit_range(31, 35)

class AtallaVSToken(Token):
    class Info:
        size = 40
    opcode = bit_range(0, 7)
    vd     = bit_range(7, 15)
    vs1    = bit_range(15, 23)
    rs1    = bit_range(23, 31)
    mask_reg   = bit_range(31, 35)

class AtallaVIToken(Token):
    class Info:
        size = 40
    opcode   = bit_range(0, 7)
    vd       = bit_range(7, 15)
    vs1      = bit_range(15, 23)
    imm8     = bit_range(23, 31)
    mask_reg = bit_range(31, 35)

class AtallaVMemToken(Token):
    class Info:
        size = 40
    opcode   = bit_range(0, 7)
    vd       = bit_range(7, 15)
    rs1      = bit_range(15, 23)
    rs2      = bit_range(23, 31)
    num_cols = bit_range(31, 36)
    sid      = bit_range(36, 38)
class AtallaSDMAToken(Token):
    class Info:
        size = 40
    opcode   = bit_range(0, 7)
    rs1_rd1  = bit_range(7, 15)
    rs2      = bit_range(15, 23)
    rs3     = bit_range(23, 31)

class AtallaMTSToken(Token):
    class Info:
        size = 40
    opcode = bit_range(0, 7)
    rd     = bit_range(7, 15)
    vms    = bit_range(15, 19)


class AtallaSTMToken(Token):
    class Info:
        size = 40
    opcode = bit_range(0, 7)
    vmd    = bit_range(7, 11)
    rs1    = bit_range(15, 23)

class AtallaVTSToken(Token):
    class Info:
        size = 40
    opcode = bit_range(0, 7)
    rd     = bit_range(7, 15)
    vs1    = bit_range(15, 23)
    imm8   = bit_range(23, 31)

class AtallaVMVToken(Token):
    class Info:
        size = 40
    opcode = bit_range(0, 7)
    vmd    = bit_range(7, 11)
    vs1    = bit_range(15, 23)
    vs2    = bit_range(23, 31)
    mask_reg   = bit_range(31, 35)

class AtallaVMSToken(Token):
    class Info:
        size = 40
    opcode = bit_range(0, 7)
    vmd    = bit_range(7, 11)
    vs1    = bit_range(15, 23)
    rs1    = bit_range(23, 31)
    mask_reg   = bit_range(31, 35)