from ppci.arch.riscv.registers import RiscvRegister, RiscvRegisterBank
from ppci.arch.riscv.registers import X0, X1, X2, X3, X4, X5, X6, X7, X8, X9, X10, X11
from ppci.arch.riscv.registers import X12, X13, X14, X15, X16, X17, X18, X19, X20, X21
from ppci.arch.riscv.registers import X22, X23, X24, X25, X26, X27, X28, X29, X30, X31


register_bank = RiscvRegisterBank
MyRiscvRegister = RiscvRegister

__all__ = ['register_bank', 'MyRiscvRegister',
           'X0', 'X1', 'X2', 'X3', 'X4', 'X5', 'X6', 'X7', 'X8', 'X9', 'X10', 'X11',
           'X12', 'X13', 'X14', 'X15', 'X16', 'X17', 'X18', 'X19', 'X20', 'X21',
           'X22', 'X23', 'X24', 'X25', 'X26', 'X27', 'X28', 'X29', 'X30', 'X31']
