# ppci/arch/myarch/instructions.py
from ppci.arch.encoding import Instruction, Syntax, Operand
from ppci.arch import registers
from ppci.arch.riscv.instructions import RiscvInstruction

# Define operands first. These are the "types" of arguments an instruction can take.
reg = Operand('reg', MyCpuRegister) # A register operand
imm = Operand('imm', int)           # An immediate (constant) operand

# Define a simple theta instruction
class Theta(RiscvInstruction):
    regs = (reg, reg, reg)  # Syntax: THETA dest, src1, src2
    syntax = Syntax(['add', ' ', reg, ',', ' ', reg, ',', ' ', reg])
    tokens = [('add_op', 0b0001)]  # The opcode in binary/hex
    patterns = {'add_op': 0b0001, 'reg': reg} # How to encode the operands

    def encode(self):
        # This function uses the patterns to pack operands into the opcode
        return self.add_op << 12 | self.reg[0].num << 8 | self.reg[1].num << 4 | self.reg[2].num

# ... define other core instructions: SUB, JMP, LOAD, STORE, CALL, RET, etc.
