from ppci.api import cc, link, ir_to_assembly
from ppci.lang.c import c_to_ir
from ppci.ir import Module
from ppci.binutils.objectfile import print_object
from ppci.arch.amp.asm_printer import AtallaAsmPrinter

def main():
    with open("sample.c", "r") as f:
        reporter = AtallaAsmPrinter()
        reporter.print_instruction(cc(f, "atalla"))


if __name__ == "__main__":
    main()
