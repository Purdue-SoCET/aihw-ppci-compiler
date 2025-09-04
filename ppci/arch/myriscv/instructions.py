from ppci.arch.encoding import Instruction, Syntax, Operand, token
from ppci.arch.riscv.registers import RiscvRegister
from ppci.arch.riscv.instructions import RiscvInstruction, RiscvRInstruction

# Define operands for our instruction: destination register (rd), source registers (rs1, rs2)
reg = Operand('reg', RiscvRegister)

# We create a custom opcode and funct7 code for our instruction.
# Let's choose a custom funct7 that isn't used by standard RISC-V.
# Standard RISC-V uses opcode 0b0110011 for R-type instructions.
class ThetaInstruction(RiscvRInstruction):
    # Syntax: theta rd, rs1, rs2
    syntax = Syntax(['theta', ' ', reg, ',', ' ', reg, ',', ' ', reg])

    # Define the tokens for encoding. We use the standard R-type opcode.
    # We need to define a custom funct7 to make it unique.
    # Let's assume opcode is 0b0110011 (R-type) and funct3 is 0b000.
    # We'll invent a new funct7: 0b0000001 (This is a placeholder, must be unique!)
    tokens = [token('funct7', 7), token('rs2', 5), token('rs1', 5), token('funct3', 3), token('rd', 5), token('opcode', 7)]
    opcode = 0b0110011  # Standard R-type opcode
    funct3 = 0b000      # We can choose a funct3, let's use 0
    funct7 = 0b0000001  # Our custom function code to identify 'theta'

    def __init__(self, rd, rs1, rs2):
        super().__init__(rd, rs1, rs2)
        # The parent class handles the encoding based on the tokens and patterns

    def __repr__(self):
        return f"Theta {self.rd}, {self.rs1}, {self.rs2}"

# It's crucial to add our new instruction to this list.
# The assembler and code generator will use this.
instruction_classes = [ThetaInstruction]
