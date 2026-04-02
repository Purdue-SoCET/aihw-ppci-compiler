from ...utils.bitfun import wrap_negative, BitView
from ..encoding import Relocation
from .tokens import *

# 6 byte aligned means 48 bits, 5 means 40 bits
ATALLA_INSN_ALIGNMENT = 5

class AtallaBR_Imm10_Relocation(Relocation):
    name = "BR_i10"
    token = AtallaBRToken

    def calc(self, sym_value, reloc_value):
        offset = (sym_value - reloc_value) // ATALLA_INSN_ALIGNMENT
        return wrap_negative(offset, 10)

    # def calc(self, sym_value, reloc_value):
    #     pc_next = reloc_value + ATALLA_INSN_ALIGNMENT
    #     offset = (sym_value - pc_next) // ATALLA_INSN_ALIGNMENT
    #     return wrap_negative(offset, 10)

    def apply(self, sym_value, data, reloc_value):
        imm10 = self.calc(sym_value, reloc_value)
        token = self.token.from_data(data)
        token.imm10 = imm10
        return token.encode()

class AtallaMI_JAL_Imm25_Relocation(Relocation):
    name = "MI_jal_i25"
    token = AtallaMIToken
    field = "imm25"

    def calc(self, sym_value, reloc_value):
        offset = (sym_value - reloc_value) // ATALLA_INSN_ALIGNMENT
        return wrap_negative(offset, 25)

# For if lui uses or loads symbol addresses
class AtallaMI_Abs_Imm25_Relocation(Relocation):
    name = "MI_abs_i25"
    token = AtallaMIToken
    field = "imm25"
    
    def calc(self, sym_value, reloc_value):
        return (sym_value >> 7) & 0x1FFFFFF # Shifts and grabs the upper 25 bits
    
    def apply(self, sym_value, data, reloc_value):
        imm25 = self.calc(sym_value, reloc_value)
        token = self.token.from_data(data)
        token.imm25 = imm25
        return token.encode()

# For addi when used in conjunction with lui
class AtallaI_Abs_Imm7_Relocation(Relocation):
    name = "abs_imm7"
    token = AtallaIToken
    
    def calc(self, sym_value, reloc_value):
        # lower 7 bits for absolute addressing with addresses being 32 bits
        return sym_value & 0x7F
    
    def apply(self, sym_value, data, reloc_value):
        imm7 = self.calc(sym_value, reloc_value)
        token = self.token.from_data(data)
        token.imm12 = imm7
        return token.encode()

# May not need JALR if the offset is always literal and not a symbol value
class AtallaI_JALR_Imm12_Relocation(Relocation):
    name = "I_i12"
    token = AtallaIToken
    field = "imm12"
    def calc(self, sym_value, reloc_value):
        return sym_value & 0xFFF # You need the lower 12 bits absolute for jalr
