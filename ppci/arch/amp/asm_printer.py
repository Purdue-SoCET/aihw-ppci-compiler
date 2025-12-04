from ..asm_printer import AsmPrinter
from ..generic_instructions import SectionInstruction
from .instructions import Nop


class AtallaAsmPrinter(AsmPrinter):
    """Riscv specific assembly printer"""

    def print_instruction(self, instruction):
        if isinstance(instruction, SectionInstruction):
            sec = getattr(instruction, "name", None) \
                  or getattr(instruction, "section", None) \
                  or getattr(instruction, "sec", None)
            return f".section {sec}"
        if isinstance(instruction, Nop):
            return "nop"
        return str(instruction)
