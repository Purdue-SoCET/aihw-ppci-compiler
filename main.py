from ppci.api import cc, link, ir_to_assembly
from ppci.cli.atalla_cc import atalla_cc
from ppci.lang.c import c_to_ir
from ppci.ir import Module
from ppci.binutils.objectfile import print_object
from ppci.utils.reporting import TextReportGenerator
import sys


'''
Do not use this file. Run the compiler via makefile.
'''

def main():
    with open("sample.c", "r") as source:
        #cc(source, "atalla")

        with open("amps.s", "w") as f:
            reporter = TextReportGenerator(f)
            # Atalla compiler
            atalla_cc()

            # Uncomment for riscv
            # cc(source, "riscv", reporter=reporter)

if __name__ == "__main__":
    main()
