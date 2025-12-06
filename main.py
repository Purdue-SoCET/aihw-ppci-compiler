from ppci.api import atalla_cc, cc, link, ir_to_assembly
from ppci.lang.c import c_to_ir
from ppci.ir import Module
from ppci.binutils.objectfile import print_object
from ppci.utils.reporting import TextReportGenerator
import sys

def main():
    with open("sample.c", "r") as source:
        #cc(source, "atalla")

        with open("amps.s", "w") as f:
            reporter = TextReportGenerator(f)
            atalla_cc(source, "atalla", reporter=reporter)

if __name__ == "__main__":
    main()
