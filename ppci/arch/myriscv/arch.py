from ppci.arch.riscv.arch import RiscvArch
from ppci.arch.myriscv.instructions import isa as myisa
from ppci.arch.riscv.instructions import isa as riscv_isa
from ppci.arch.riscv.registers import register_classes_hwfp

class MyRiscvArch(RiscvArch):
    name = 'myriscv'

    def __init__(self, options=None):
        super().__init__(options)
        # Add the Theta instruction to the instruction set
        self.isa = riscv_isa + myisa
        self.regclass = register_classes_hwfp
