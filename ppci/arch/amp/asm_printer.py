from ..asm_printer import AsmPrinter
from ..generic_instructions import SectionInstruction


class AtallaAsmPrinter(AsmPrinter):
    """Riscv specific assembly printer"""

    def print_instruction(self, instruction):
        if isinstance(instruction, SectionInstruction):
            return f".section {instruction.name}"
        else:
            return str(instruction)
