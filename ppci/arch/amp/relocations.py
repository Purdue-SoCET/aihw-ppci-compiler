from ...utils.bitfun import wrap_negative, BitView
from ..encoding import Relocation
from .tokens import *


class BImm12Relocation(Relocation):
    name = "b_imm12"
    token = AtallaBRToken
    field = "imm"

    def calc(self, sym_value, reloc_value):
        assert sym_value % 8 == 0
        assert reloc_value % 8 == 0
        offset = (sym_value - reloc_value) // 8
        return wrap_negative(offset, 12)

    def apply(self, sym_value, data, reloc_value):
        assert self.token is not None
        token = self.token.from_data(data)
        assert self.field is not None
        assert hasattr(token, self.field)
        setattr(token, self.field, self.calc(sym_value, reloc_value))
        return token.encode()


class BImm20Relocation(Relocation):
    name = "b_imm20"
    token = AtallaJToken
    field = "imm"

    def calc(self, sym_value, reloc_value):
        assert sym_value % 8 == 0
        assert reloc_value % 8 == 0
        offset = (sym_value - reloc_value) // 8
        return wrap_negative(offset, 20)

    def apply(self, sym_value, data, reloc_value):
        assert self.token is not None
        token = self.token.from_data(data)
        assert self.field is not None
        assert hasattr(token, self.field)
        setattr(token, self.field, self.calc(sym_value, reloc_value))
        return token.encode()

class AbsAddr32Relocation(Relocation):
    name = "absaddr32"
    token = AtallaRToken

    def apply(self, sym_value, data, reloc_value):
        offset = sym_value
        bv = BitView(data, 0, 4)
        bv[0:32] = offset
        return data

class Abs32Imm12Relocation(Relocation):
    name = "abs32_imm12"
    token = AtallaIToken
    field = "imm12"

    def calc(self, sym_value, reloc_value):
        assert sym_value % 2 == 0
        return sym_value & 0xFFF

    def apply(self, sym_value, data, reloc_value):
        """Apply this relocation type given some parameters.

        This is the default implementation which stores the outcome of
        the calculate function into the proper token."""
        assert self.token is not None
        token = self.token.from_data(data)
        assert self.field is not None
        assert hasattr(token, self.field)
        setattr(token, self.field, self.calc(sym_value, reloc_value))
        return token.encode()
