from ...utils.bitfun import wrap_negative, BitView
from ..encoding import Relocation
from .tokens import *

# Important!:  The names for these must match what the assembler generates, they cannot just be whatever you want!
#the instructions are 5 or 6 byte aligned 40-48 bits
ATALLA_INSN_ALIGNMENT = 5

# 40 bits: BR imm9 9 bits, rs2 8 bits, rs1 8 bits, imm1 1 bit, incr-imm7 7 bits, opcode - 7 bits
# Note: the accum fields are so that we can do a loop increment and compare in 1 cycle. also imm1 + imm9 = imm10
class AtallaBR_Imm10_Relocation(Relocation):
    name = "BR_i10"
    token = AtallaBRToken

    def calc(self, sym_value, reloc_value):
        assert sym_value % ATALLA_INSN_ALIGNMENT == 0
        assert reloc_value % ATALLA_INSN_ALIGNMENT == 0
        offset = (sym_value - reloc_value) // ATALLA_INSN_ALIGNMENT
        return wrap_negative(offset, 10)

    def apply(self, sym_value, data, reloc_value):
        imm10 = self.calc(sym_value, reloc_value)
        # Assuming encoding is {imm9, i1} = {bits[9:1], bit[0]}
        imm9 = (imm10 >> 1) & 0x1FF #upper 9 bits
        i1 = imm10 & 0x1 #lower 1 bit
        token = self.token.from_data(data)
        token.imm9 = imm9
        token.i1 = i1
        return token.encode()

# 40 bits: MI imm25 25 bits, rd 8 bits, opcode - 7 bits
# Note: load immediates (only 25 bits not a full 32, sign extend)
# This shit has to be wrong in the ISA because we are not working with 32 bits are we?
# li.s	0101101	load immediate	MI	to do a li, do a lui for the top 25 bits, then an addi on the same reg for the bottom 7 bits	45	Pseudo instructions
# lui.s	0101110	load upper immediate	MI	rd[31:7] =imm[24:0]	46	
# Does addi sign extend the immediate?  Because then we would have to add by 1 to combine it with the immediate from the lui
# I need to know the datapath width, is it 32 or is it 40??
# I also need to know what the width of the pc is because that determines the number of bits we are using to index our memory space
# I am guessing that instructions are 40 bits but that the address space is still encoded by the RISC-V 32 bits I think
class AtallaMI_Abs_Imm25_Relocation(Relocation): # I assumed it was just for loading in number calculated elsewhere since the ISA did not care
    name = "MI_abs_i25"
    token = AtallaMIToken
    field = "imm25"
    
    def calc(self, sym_value, reloc_value):
        return sym_value & 0x1FFFFFF #for masking to 25 bits

class AtallaMI_JAL_Imm25_Relocation(Relocation): #had to split this instruction up because it has different addressing modes!!
    name = "MI_jal_i25"
    token = AtallaMIToken
    field = "imm25"

    def calc(self, sym_value, reloc_value):
        # had to comment these out to make it not error
        # assert sym_value % ATALLA_INSN_ALIGNMENT == 0
        # assert reloc_value % ATALLA_INSN_ALIGNMENT == 0
        offset = (sym_value - reloc_value) // ATALLA_INSN_ALIGNMENT
        return wrap_negative(offset, 25) # for the 25 bit immediate

# 40 bits: M imm12 12 bits, rs1 8 bits, rd 8 bits, opcode - 7 bits, indexed from 0, padded to 40 bits with 5 bits
# It looks like M types are register relative, not absolute or pc relative, so if sign extension is done in the hardware, then this should be good
class AtallaM_Imm12_Relocation(Relocation):
    name = "M_i12"
    token = AtallaMToken
    field = "imm12"
    
    def calc(self, sym_value, reloc_value):
        return sym_value & 0xFFF #just the lower 12 bits

# 40 bits: I imm12 12 bits, rs1 8 bits, rd 8 bits, opcode - 7 bits, same as m, padded to 40 bits
# Note: jalr will use this formatting.
# Question: Do we have an auipc that loads in the upper 20 in RISC-V, or 28 in atalla to x1 for jalr? I don't see an auipc in the excel sheet
# Since rs1 + imm could be any address, does it need to be aligned? I have it commented out for now
class AtallaI_JALR_Imm12_Relocation(Relocation): # May need multiple this only works for an atalla jalr, but that is the only one that is I type that has addressing
    name = "I_i12"
    token = AtallaIToken #Need this one
    field = "imm12"
    def calc(self, sym_value, reloc_value):
        # assert sym_value % ATALLA_INSN_ALIGNMENT == 0
        return sym_value & 0xFFF # You need the lower 12 bits absolute for jalr

#AtallaVIToken  need relocation class for this token as well
# 40 bits: VI imm8_2 8 bits, mask 4 bits, imm8_1 8 bits, vs1 8 bits, vd 8 bits, opcode - 7 bits
# Note: Vector Immediate, imm[15:0] = {imm8_2, imm8_1} -> for arithmetic stuff | also used for Systolic Array
# Note: In the latest version of the isa, it has two 8-bit immediate fields, imm = 16, but in this branch it
# is using the most recent version and that is imm8 + imm5 = imm13, the upper immediate field is 5 not 8
# Okay, question does it concatenate in hardware because if so then I don't need to do anything here
# class AtallaVI_Imm13_Relocation(Relocation):
#     name = "VI_i13"
#     token = AtallaVIToken
#     field = "imm13"