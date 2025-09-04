from ppci.arch.arch import Architecture
from ppci.arch.riscv.arch import RiscvArch
from ppci.arch.myriscv import registers as my_registers
from ppci.arch.myriscv.instructions import ThetaInstruction, instruction_classes
from ppci.arch.riscv.instructions import RiscvInstruction

class MyRiscvArch(RiscvArch):  # Inherit from standard RiscvArch
    name = 'myriscv'

    # Use our custom register bank
    register_classes = [my_registers.register_bank]

    # Combine standard RISC-V instructions with our custom one
    # We get all the parent's instructions and add our new one
    def __init__(self, options=None):
        super().__init__(options)
        # Add the Theta instruction to the instruction set recognized by this arch
        self.isa.instruction_classes.extend(instruction_classes)

    # This is a placeholder for a more advanced integration.
    # A future step would be to modify 'gen_instructions' to select the 'theta'
    # instruction for a specific operation (like an intrinsic).
    # For now, the instruction can only be used via inline assembly.
