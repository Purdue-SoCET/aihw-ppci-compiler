from ppci.arch.encoding import Instruction, Syntax, Operand
from ppci.arch.riscv.registers import RiscvRegister
from ppci.arch.riscv.instructions import RiscvInstruction, make_regregreg
from ppci.arch.riscv.tokens import RiscvIToken, RiscvToken
from ..isa import Isa

isa = Isa()

Theta = make_regregreg("theta", 0b0000001, 0b101)

@isa.pattern("reg", "ADDU32(reg, reg)", size=2)
@isa.pattern("reg", "ADDI32(reg, reg)", size=2)
def pattern_add_i32(context, tree, c0, c1):
    d = context.new_reg(RiscvRegister)
    context.emit(Theta(d, c0, c1))
    return d
