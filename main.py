from ppci.api import cc

def main():
    with open("custom_compiler/sample.c", "r") as f:
        cc(f, "myriscv", debug=True)

if __name__ == "__main__":
    main()
