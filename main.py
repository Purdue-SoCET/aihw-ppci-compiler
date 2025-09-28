from ppci.api import cc, link, ir_to_assembly
from ppci.lang.c import c_to_ir
from ppci.ir import Module
from ppci.binutils.objectfile import print_object

def main():
    with open("sample.c", "r") as f:
        c_to_ir(f, "AMP").display()


if __name__ == "__main__":
    main()
