"""Atalla architecture."""

#so far we are only implementing scalar operations not including store and laod
#operation. Store and Load require more implementation so for now lets get normal
#scalar operations implemented in this architecture.


import io

from ... import ir
from ...binutils.assembler import BaseAssembler
from ..arch import Architecture
from ..arch_info import ArchInfo, TypeInfo
from ..data_instructions import DByte, DZero, data_isa
from ..generic_instructions import Label, RegisterUseDef
from ..stack import FramePointerLocation, StackLocation
from . import instructions
from .asm_printer import AtallaAsmPrinter
from .instructions import (
    #R-types
    Adds,
    Subs,
    Muls,
    Divs,
    Mods,
    Ors,
    Ands,
    Xors,
    Slls,
    Srls,
    Sras,
    Slts,
    Sltus,
    #I-types
    Addis,
    Subis,
    Mulis,
    Divis,
    Modis,
    Oris,
    Andis,
    Xoris,
    Sllis,
    Srlis,
    Srais,
    Sltis,
    Sltuis,
    #Branch-types
    Beqs,
    Bnes,
    Blts,
    Bges,
    # Load, store
    Lws,
    Sws,
    # Jumps
    Jal,
    Jalr,
    #isa
    isa,
    Align,
    Section,
    dcd,
    Nop
)

from .vector_instructions import (
    # Vector-Vector
    # DivVv,
    MulVv,
    AddVv,
    # AndVv,
    # OrVv,
    # XorVv,
    # MgtVv,
    # MltVv,
    # MeqVv,
    # Vector-Unary
    NotVi,
    ExpiVi,
    SqrtiVi,
    # Vector-Immediate
    RsumVi,
    RminVi,
    RmaxVi,
    AddiVi,
    SubiVi,
    MuliVi,
    DiviVi,
    ExpiVi,
    SqrtiVi,
    VregLd,
    VregSt,
    isa as vec_isa,
)

from .vector_registers import (
    V0, V1, V2, V3, V4, V5, V6, V7,
    V8, V9, V10, V11, V12, V13, V14, V15,
    V16, V17, V18, V19, V20, V21, V22, V23,
    V24, V25, V26, V27, V28, V29, V30, V31,
    AtallaVectorRegister,
    vector_registers,
    vector_register_classes,
)

from .mask_registers import (
    M0, M1, M2, M3, M4, M5, M6, M7,
    M8, M9, M10, M11, M12, M13, M14, M15,
    M16,
    AtallaMaskRegister,
    mask_registers,
    mask_register_classes,
)

from .registers import (
    R0,
    LR,
    SP,
    R3,
    R4,
    R5,
    R6,
    R7,
    FP,
    R9,
    R10,
    R11,
    R12,
    R13,
    R14,
    R15,
    R16,
    R17,
    R18,
    R19,
    R20,
    R21,
    R22,
    R23,
    R24,
    R25,
    R26,
    R27,
    R28,
    R29,
    R30,
    R31,
    Register,
    #AtallaFRegister,
    AtallaRegister as AtallaRegister,
    gdb_registers,
    #register_classes_hwfp,
    register_classes_swfp,
)

# I am only adding in scalar operation so anything that requires
# memory such as the functions in the normal riscv arch file will
# be left out for now. When we add memory and call/ret instructions
# to the ISA we can extend (stack args, gen_call, etx.)

def isinsrange(bits, val) -> bool:
    msb = 1 << (bits - 1)
    ll = -msb
    return bool(val <= (msb - 1) and (val >= ll))



class AtallaAssembler(BaseAssembler):
    def __init__(self):
        super().__init__()
        self.lit_pool = []
        self.lit_counter = 0

    def flush(self):
        if self.in_macro:
            raise Exception()
        while self.lit_pool:
            i = self.lit_pool.pop(0)
            self.emit(i)

    def add_literal(self, v):
        """For use in the pseudo instruction LDR r0, =SOMESYM"""
        # Invent some label for the literal and store it.
        assert type(v) is str
        self.lit_counter += 1
        label_name = f"_lit_{self.lit_counter}"
        self.lit_pool.append(Label(label_name))
        self.lit_pool.append(dcd(v))
        return label_name


class AtallaArch(Architecture):
    name = "atalla"

    def __init__(self, options=None):
        super().__init__()
        self.isa = isa + data_isa
        self.store = Sws
        self.load = Lws
        # self.vec_store = VregSt
        # self.vec_load = VregLd
        self.regclass = register_classes_swfp + vector_register_classes + mask_register_classes
        self.fp_location = FramePointerLocation.TOP
        self.fp = FP
        # self.isa.sectinst = Section
        # self.isa.dbinst = DByte
        # self.isa.dsinst = DZero
        self.gdb_registers = gdb_registers
        # self.gdb_pc = PC

        if AtallaAsmPrinter:
            self.asm_printer = AtallaAsmPrinter()


        self.assembler = AtallaAssembler()
        self.assembler.gen_asm_parser(self.isa)

        self.info = ArchInfo(
            type_infos={
                ir.i8: TypeInfo(1, 1),
                ir.u8: TypeInfo(1, 1),
                ir.i16: TypeInfo(2, 2),
                ir.u16: TypeInfo(2, 2),
                ir.i32: TypeInfo(4, 4),
                ir.u32: TypeInfo(4, 4),
                ir.vec: TypeInfo(64, 64),
                # ir.f32: TypeInfo(4, 4),
                # ir.f64: TypeInfo(4, 4),
                ir.bf16: TypeInfo(2, 2),
                "int": ir.i32,
                "long": ir.i32,
                "ptr": ir.u32,
                "vec": ir.vec,
                "float": ir.bf16,
                ir.ptr: ir.u32,
                ir.mask: TypeInfo(4, 4),
                "mask": ir.mask,
            },
            register_classes=self.regclass,
        )
        self._arg_regs = [R12, R13, R14, R15, R16, R17]
        self._ret_reg = R10

        self.callee_save = tuple()
        self.caller_save = (R10, R12, R13, R14, R15, R16, R17)

    def make_nop(self):
        """
        Return a real, encodable NOP for padding VLIW packets.
        Using ADDI r0, r0, 0 (Addis) assumes R0 is the zero register.
        If R0 is not hard-wired to zero in your ISA, define a true NOP opcode instead.
        """
        ins = Nop()
        return ins

    def branch(self, reg, lab):
        if isinstance(lab, AtallaRegister):
            return Jalr(reg, lab, 0, clobbers=self.caller_save)
        else:
            return Jal(reg, lab, clobbers=self.caller_save)

    # def get_runtime(self):
    #     """Implement compiler runtime functions"""
    #     from ...api import asm

    #     asm_src = """
    #     __sdiv:
    #     ; Divide x12 by x13
    #     ; x14 is a work register.
    #     ; x10 is the quotient

    #     mv x10, x0     ; Initialize the result
    #     li x14, 1      ; mov divisor into temporary register.

    #     ; Blow up part: blow up divisor until it is larger than the divident.
    #     __shiftl:
    #     bge x13, x12, __cont1
    #     slli x13, x13, 1
    #     slli x14, x14, 1
    #     j __shiftl

    #     ; Repeatedly substract shifted versions of divisor
    #     __cont1:
    #     beq x14, x0, __exit
    #     blt x12, x13, __skip
    #     sub x12, x12, x13
    #     or x10, x10, x14
    #     __skip:
    #     srli x13, x13, 1
    #     srli x14, x14, 1
    #     j __cont1

    #     __exit:
    #     jalr x0,ra,0
    #     """
    #     return asm(io.StringIO(asm_src), self)

    def move(self, dst, src):
        """Generate a move from src to dst"""
        if V0 in src.registers or V0 in dst.registers:
            return AddiVi(dst, src, 0, M0)
        return Addis(dst, src, 0)

    # don't need until implement memory
    def gen_Atalla_memcpy(self, dst, src, tmp, size):
        # Called before register allocation
        # Major crappy memcpy, can be improved!
        for idx in range(size):
            yield Lws(tmp, idx, src)
            yield Sws(tmp, idx, dst)

    def gen_prologue(self, frame):
        """
        we need block/branches to anchor.
        We will adjust SP, save LR and LP, save callee-saves
        We will impliment load/store/stack later
        when we have the MEM operations.
        """
        # Label indication function:
        yield Label(frame.name)
        ssize = round_up(frame.stacksize + 8)
        # if self.has_option("rvc") and isinsrange(10, -ssize):
        #     yield CAddi16sp(-ssize)  # Reserve stack space
        # else:
        yield Addis(SP, SP, -ssize)  # Reserve stack space

        # if self.has_option("rvc"):
        #     yield CSwsp(LR, 4)
        #     yield CSwsp(FP, 0)
        # else:
        yield Sws(LR, 4, SP)
        yield Sws(FP, 0, SP)

        # if self.has_option("rvc"):
        #     yield CAddi4spn(FP, 8)  # Setup frame pointer
        # else:
        yield Addis(FP, SP, 8)  # Setup frame pointer
        # yield Addi(FP, SP, 8)  # Setup frame pointer

        saved_registers = self.get_callee_saved(frame)
        rsize = 4 * len(saved_registers)
        rsize = round_up(rsize)

        # if self.has_option("rvc") and isinsrange(10, rsize):
        #     yield CAddi16sp(-rsize)  # Reserve stack space
        # else:
        yield Addis(SP, SP, -rsize)  # Reserve stack space

        i = 0
        for register in saved_registers:
            i -= 4
            # if self.has_option("rvc"):
            #     yield CSwsp(register, i + rsize)
            # else:
            yield Sws(register, i + rsize, SP)

        # Allocate space for outgoing calls:
        extras = max(frame.out_calls) if frame.out_calls else 0
        if extras:
            ssize = round_up(extras)
            # if self.has_option("rvc") and isinsrange(10, ssize):
            #     yield CAddi16sp(-ssize)  # Reserve stack space
            # else:
            yield Addis(SP, SP, -ssize)  # Reserve stack space

    def gen_epilogue(self, frame):
        """
        later we restore callee-saves, reload LR and FP, deallocate the stack
        """
        extras = max(frame.out_calls) if frame.out_calls else 0
        if extras:
            ssize = round_up(extras)
            # if self.has_option("rvc") and isinsrange(10, ssize):
            #     yield CAddi16sp(ssize)  # Reserve stack space
            # else:
            yield Addis(SP, SP, ssize)  # Reserve stack space

        # Callee saved registers:
        saved_registers = self.get_callee_saved(frame)
        rsize = 4 * len(saved_registers)
        rsize = round_up(rsize)

        i = 0
        for register in saved_registers:
            i -= 4
            # if self.has_option("rvc"):
            #     yield CLwsp(register, i + rsize)
            # else:
            yield Lws(register, i + rsize, SP)

        # if self.has_option("rvc") and isinsrange(10, rsize):
        #     yield CAddi16sp(rsize)  # Reserve stack space
        # else:
        yield Addis(SP, SP, rsize)  # Reserve stack space

        # if self.has_option("rvc"):
        #     yield CLwsp(LR, 4)
        #     yield CLwsp(FP, 0)
        # else:
        yield Lws(LR, 4, SP)
        yield Lws(FP, 0, SP)

        ssize = round_up(frame.stacksize + 8)
        # if self.has_option("rvc") and isinsrange(10, ssize):
        #     yield CAddi16sp(ssize)  # Free stack space
        # else:
        yield Addis(SP, SP, ssize)  # Free stack space

        # Return
        # if self.has_option("rvc"):
        #     yield CJr(LR)
        # else:
        yield Jalr(R0, LR, 0)

        # Add final literal pool:
        yield from self.litpool(frame)
        yield Align(4)  # Align at 4 bytes

    def peephole(self, frame):
        removed = set()
        newinstructions = []
        for ins in frame.instructions:
            # idk if this causes a problem with vreg ld/st TODO: investigate
            # identify during testing phase and fix if needed
            if hasattr(ins, "fprel") and ins.fprel and not isinstance(ins, (VregLd, VregSt)):
                ins.imm12 += round_up(frame.stacksize + 8) - 8
            # Remove redundant addi_s rd, rs, 0 when rd == rs (no MOV in ISA)
            if isinstance(ins, instructions.Addis) and ins.imm12 == 0:
                rd_real = ins.rd.get_real() if ins.rd.is_colored else ins.rd
                rs1_real = ins.rs1.get_real() if ins.rs1.is_colored else ins.rs1
                if rd_real is rs1_real or rd_real == rs1_real:
                    removed.add(ins)
                    continue  # identity move, drop instruction
            newinstructions.append(ins)
        # Atalla emits from frame.buckets_by_block, so drop removed instructions there too
        if removed and getattr(frame, "buckets_by_block", None):
            for depth_list in frame.buckets_by_block.values():
                for i, chunk in enumerate(depth_list):
                    depth_list[i] = [inst for inst in chunk if inst not in removed]
        return newinstructions

    def gen_call(self, frame, label, args, rv):
        """Implement actual call and save / restore live registers"""

        arg_types = [a[0] for a in args]
        arg_locs = self.determine_arg_locations(arg_types)
        stack_size = 0
        # Setup parameters:
        for arg_loc, arg2 in zip(arg_locs, args):
            arg = arg2[1]
            if isinstance(arg_loc, (AtallaRegister)):
                yield self.move(arg_loc, arg)
            elif isinstance(arg_loc, StackLocation):
                stack_size += arg_loc.size
                if isinstance(arg, AtallaRegister):
                    yield Sws(arg, arg_loc.offset, SP)
                elif isinstance(arg, StackLocation):
                    p1 = frame.new_reg(AtallaRegister)
                    p2 = frame.new_reg(AtallaRegister)
                    v3 = frame.new_reg(AtallaRegister)

                    # Destination location:
                    # Remember that the LR and FP are pushed in between
                    # So hence -8:
                    yield instructions.Addis(p1, SP, arg_loc.offset)
                    # Source location:
                    yield instructions.Addis(
                        p2,
                        self.fp,
                        arg.offset + round_up(frame.stacksize + 8) - 8,
                    )
                    yield from self.gen_Atalla_memcpy(p1, p2, v3, arg.size)
            else:  # pragma: no cover
                raise NotImplementedError("Parameters in memory not impl")

        # Record that certain amount of stack is required:
        frame.add_out_call(stack_size)

        arg_regs = {
            arg_loc for arg_loc in arg_locs if isinstance(arg_loc, Register)
        }
        yield RegisterUseDef(uses=arg_regs)

        yield self.branch(LR, label)

        if rv:
            retval_loc = self.determine_rv_location(rv[0])
            yield RegisterUseDef(defs=(retval_loc,))
            yield self.move(rv[1], retval_loc)


    def gen_function_enter(self, args):
        arg_types = [a[0] for a in args]
        arg_locs = self.determine_arg_locations(arg_types)

        arg_regs = {
            arg_loc for arg_loc in arg_locs if isinstance(arg_loc, Register)
        }
        yield RegisterUseDef(defs=arg_regs)

        for arg_loc, arg2 in zip(arg_locs, args):
            arg = arg2[1]
            if isinstance(arg_loc, Register):
                yield self.move(arg, arg_loc)
            elif isinstance(arg_loc, StackLocation):
                if isinstance(arg, AtallaRegister):
                    Code = Lws(arg, arg_loc.offset, FP)
                    Code.fprel = True
                    yield Code
                else:
                    pass
            else:  # pragma: no cover
                raise NotImplementedError("Parameters in memory not impl")

    def gen_function_exit(self, rv):
        live_out = set()
        if rv[1]:
            retval_loc = self.determine_rv_location(rv[0])
            yield self.move(retval_loc, rv[1])
            live_out.add(retval_loc)
        yield RegisterUseDef(uses=live_out)

    def determine_arg_locations(self, arg_types):
        """
        Given a set of argument types, determine location for argument
        ABI:
        pass args in R12-R17
        return values in R10
        """
        locations = []
        regs = [R12, R13, R14, R15, R16, R17]

        offset = 0
        for a in arg_types:
            if a.is_blob:
                r = StackLocation(offset, a.size)
                offset += a.size
            else:
                # if a in [ir.f32, ir.f64] and self.has_option("rvf"):
                #     if fregs:
                #         r = fregs.pop(0)
                #     else:
                #         arg_size = self.info.get_size(a)
                #         r = StackLocation(offset, a.size)
                #         offset += arg_size
                # else:
                if regs:
                    r = regs.pop(0)
                else:
                    arg_size = self.info.get_size(a)
                    r = StackLocation(offset, arg_size)
                    offset += arg_size
            locations.append(r)
        return locations

    def determine_rv_location(self, ret_type):
        return R10

    def litpool(self, frame):
        """Generate instruction for the current literals"""
        yield Section("data")
        # Align at 4 byte
        if frame.constants:
            yield Align(4)

        # Add constant literals:
        while frame.constants:
            label, value = frame.constants.pop(0)
            yield Label(label)
            if isinstance(value, (int, str)):
                yield dcd(value)
            elif isinstance(value, bytes):
                for byte in value:
                    yield DByte(byte)
                yield Align(4)  # Align at 4 bytes
            else:  # pragma: no cover
                raise NotImplementedError(f"Constant of type {value}")

        yield Section("code")


    def between_blocks(self, frame):
        return []


    def get_callee_saved(self, frame):
        saved_registers = []
        for register in self.callee_save:
            if frame.is_used(register, self.info.alias):
                saved_registers.append(register)
        return saved_registers


    # I added this function straight from chat
    def get_reloc_type(self, reloc_type, symbol):
        """Map PPCI relocation types to ELF relocation type numbers.
        
        These numbers are architecture-specific and should be documented
        in your ISA specification. For now, we use arbitrary numbers.
        """
        # Map relocation class names to ELF relocation numbers
        reloc_map = {
            "BR_i10": 1,           # Branch 10-bit
            "MI_jal_i25": 2,       # JAL 25-bit
            "MI_abs_i25": 3,       # Absolute upper 25 bits
            "M_i12": 4,            # Memory 12-bit
            "I_i12": 5,            # I-type 12-bit (JALR)
        }
        
        # Get the relocation name from the relocation type
        if hasattr(reloc_type, 'name'):
            reloc_name = reloc_type.name
        elif isinstance(reloc_type, str):
            reloc_name = reloc_type
        else:
            reloc_name = reloc_type.__class__.__name__
        
        if reloc_name in reloc_map:
            return reloc_map[reloc_name]
        else:
            raise NotImplementedError(
                f"ELF relocation type for '{reloc_name}' not defined"
            )

def round_up(s):
    return s + (16 - s % 16)
