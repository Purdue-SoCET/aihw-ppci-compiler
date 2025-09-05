from ppci.arch.riscv.arch import RiscvArch
from ppci.arch.myriscv.instructions import isa as myisa
from ppci.arch.riscv.instructions import isa as riscv_isa
from ppci.arch.myriscv import registers as my_registers
from ppci.arch.registers import RegisterClass

class MyRiscvArch(RiscvArch):
    name = 'myriscv'

    def __init__(self, options=None):
        super().__init__(options)
        # Add the Theta instruction to the instruction set
        self.isa = riscv_isa + myisa

        # Override with our custom register bank
        self.registers = my_registers.register_bank

        # Define register classes properly
        self.info.register_classes = [
            RegisterClass(
                'reg',
                [reg for reg in self.registers if reg.num >= 1 and reg.num <= 31],  # x1 to x31
                self.registers[1]  # x1 as default
            )
        ]

    def get_register(self, name):
        """Get register by name from our custom bank"""
        for reg in self.registers:
            if reg.name == name:
                return reg
        raise KeyError(f"Register {name} not found")
