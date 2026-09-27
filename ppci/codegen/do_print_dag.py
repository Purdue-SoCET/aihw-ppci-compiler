# test_print_dag.py
from print_dag import build_and_print
from irdag import FunctionInfo, prepare_function_info
from selectiongraph import SelectionGraph
from ppci.arch.x86 import X86_64  # example target, adjust to your arch

# Suppose you have an IR function ready to test:
from ppci.lang.c import c_to_ir
import io

source = io.StringIO("""
int main() {
    int x = 3;
    int y = 4;
    return x + y;
}
""")

arch = X86_64()
ir_module = c_to_ir(source, arch)
ir_function = ir_module.functions[0]

# Build a frame for this function
frame = arch.new_frame(ir_function.name, ir_function)

# Print the DAG
build_and_print(ir_function, arch, frame)
