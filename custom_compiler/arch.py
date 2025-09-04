# ppci/arch/myarch/arch.py
from ppci.arch.arch import Architecture, Label
from ppci.arch import generic_instructions
from ppci.arch.myarch import instructions as my_instructions
from ppci.arch.myarch.registers import MyCpuRegister, R0, R1, R2, R3, register_bank
from ppci.ir import ir_to_arch

class MyCpuArch(Architecture):
    name = 'mycpu'

    # 1. Define the bitness of the target
    ir_type = ir_to_arch('ptr16') # Our fictional CPU is 16-bit

    # 2. Define the register bank
    register_classes = [register_bank]

    # 3. This tells the compiler which instructions are available
    instruction_classes = [
        my_instructions.Theta,
        generic_instructions.Jump, # Re-use generic instructions like Jump
        generic_instructions.Call,
        # ... add all your instructions
    ]

    # 4. Define the calling convention (crucial for function calls)
    # This specifies which registers are for arguments, return values, etc.
    def determine_calling_convention(self, function):
        return MyCpuCallingConvention(self)

    # 5. THE CORE FUNCTION: How to lower IR to machine instructions.
    def gen_instructions(self, ir_instruction):
        """This generator function is called for every IR instruction.
        It must yield one or more machine instructions."""
        if isinstance(ir_instruction, ir.Binop):
            # Lower a binary operation (e.g., addition)
            if ir_instruction.operation == '+':
                # Yield instructions to put operands in registers and perform the ADD
                yield my_instructions.Mov(R0, ir_instruction.a) # Mock code
                yield my_instructions.Mov(R1, ir_instruction.b)
                yield my_instructions.Add(R2, R0, R1) # R2 = R0 + R1
                # You would also need to handle moving the result to the right location
        elif isinstance(ir_instruction, ir.Const):
            # Lower a constant value
            yield my_instructions.Mov(R0, ir_instruction.value)
        elif isinstance(ir_instruction, ir.Store):
            # Lower a store operation to a STR instruction
            # ... complex logic for address calculation
            pass
        # ... you must handle ALL IR instruction types your frontends might generate.
        # This is the most complex and labor-intensive part.

class MyCpuCallingConvention(CallingConvention):
    # ... define how arguments are passed (stack vs registers),
    # how the return address is stored, and how the stack is managed.
    pass
