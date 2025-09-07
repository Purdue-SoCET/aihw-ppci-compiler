from ppci.api import cc
from ppci.lang.c import c_to_ir
from ppci.ir import Module

def main():
    with open("sample.c", "r") as f:
        c_to_ir(f, "riscv").display()

if __name__ == "__main__":
    main()
