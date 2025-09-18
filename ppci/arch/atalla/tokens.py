from ..token import Token, bit, bit_concat, bit_range


class StallaToken(Token):
    class Info:
        size = 64

    opcode = bit_range(57,63)
    rs1 = bit_range(52,56)
    rs2 = bit_range(47,51)
    imm12 = bit_range()
