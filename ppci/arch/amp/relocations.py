from ...utils.bitfun import wrap_negative
from ..encoding import Relocation
from .tokens import *


class BImm12Relocation(Relocation):
    name = "b_imm12"
    token = AmpBRToken
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
    token = AmpJToken
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
