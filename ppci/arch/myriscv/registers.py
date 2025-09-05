from ppci.arch.riscv.registers import RiscvRegister

# Create a custom register class that properly implements from_num
class MyRiscvRegister(RiscvRegister):
    def from_num(self, num):
        """Map register number to actual register name - THIS FIXES THE ERROR"""
        if 0 <= num <= 31:
            return f'x{num}'
        elif num == 32:
            return 'pc'
        else:
            # For any custom registers you might add later
            raise ValueError(f"Invalid register number: {num}")

    def get_real(self):
        """Override get_real to use our from_num implementation"""
        return self.from_num(self._color)

# Use the standard RISC-V register bank but with our custom class
# We need to recreate the registers using our custom class
register_bank = [
    MyRiscvRegister(f'x{i}', i) for i in range(32)
] + [MyRiscvRegister('pc', 32)]

# Create individual register variables for easy access
X0, X1, X2, X3, X4, X5, X6, X7, X8, X9, X10, X11, \
X12, X13, X14, X15, X16, X17, X18, X19, X20, X21, \
X22, X23, X24, X25, X26, X27, X28, X29, X30, X31 = register_bank[:32]

__all__ = ['register_bank', 'MyRiscvRegister',
           'X0', 'X1', 'X2', 'X3', 'X4', 'X5', 'X6', 'X7', 'X8', 'X9', 'X10', 'X11',
           'X12', 'X13', 'X14', 'X15', 'X16', 'X17', 'X18', 'X19', 'X20', 'X21',
           'X22', 'X23', 'X24', 'X25', 'X26', 'X27', 'X28', 'X29', 'X30', 'X31']
