"""Machine code generator.

The architecture is provided when the generator is created.
"""

import logging

from .. import ir
from ..arch import data_instructions
from ..arch.arch import Architecture
from ..arch.arch_info import Endianness
from ..arch.data_instructions import DByte, DZero
from ..arch.encoding import Instruction
from ..arch.generic_instructions import (
    Alignment,
    ArtificialInstruction,
    Comment,
    DebugData,
    Global,
    InlineAssembly,
    Label,
    RegisterUseDef,
    SetSymbolType,
    VirtualInstruction,
)
from ..binutils.debuginfo import DebugDb, DebugLocation, DebugType
from ..binutils.outstream import FunctionOutputStream, MasterOutputStream
from ..irutils import Verifier, split_block
from .instructionscheduler import InstructionScheduler
from .instructionselector import InstructionSelector1
from .irdag import SelectionGraphBuilder
from .peephole import PeepHoleStream
from .registerallocator import GraphColoringRegisterAllocator


class CodeGenerator:
    """Machine code generator"""

    logger = logging.getLogger("codegen")

    def __init__(self, arch, reporter, optimize_for="size", packetize=False):
        assert isinstance(arch, Architecture), arch
        self.arch = arch
        self.reporter = reporter
        self.packetize = packetize
        self.verifier = Verifier()
        self.sgraph_builder = SelectionGraphBuilder(arch)
        weights_map = {
            "size": (10, 1, 1),
            "speed": (3, 10, 1),
            "co2": (1, 2, 10),
            "awesome": (13, 13, 13),
        }
        selection_weights = weights_map.get(optimize_for, (1, 1, 1))
        self.instruction_selector = InstructionSelector1(
            arch, self.sgraph_builder, reporter, weights=selection_weights
        )
        self.instruction_scheduler = InstructionScheduler()
        self.register_allocator = GraphColoringRegisterAllocator(
            arch, self.instruction_selector, reporter
        )

    def generate(self, ircode: ir.Module, output_stream, debug=False):
        """Generate machine code from ir-code into output stream"""
        assert isinstance(ircode, ir.Module)
        if ircode.debug_db:
            self.debug_db = ircode.debug_db
        else:
            self.debug_db = DebugDb()

        self.logger.info(
            "Generating %s code for module %s", str(self.arch), ircode.name
        )

        # Declare externals:
        output_stream.select_section("data")
        for external in ircode.externals:
            self._mark_global(output_stream, external)
            if isinstance(external, ir.ExternalSubRoutine):
                output_stream.emit(SetSymbolType(external.name, "func"))

        # Generate code for global variables:
        output_stream.select_section("data")
        for var in ircode.variables:
            self.generate_global(var, output_stream, debug)

        # Generate code for functions:
        # Munch program into a bunch of frames. One frame per function.
        # Each frame has a flat list of abstract instructions.
        output_stream.select_section("code")
        for function in ircode.functions:
            self.generate_function(function, output_stream, debug=debug)

        # Output debug type data:
        if debug:
            for di in self.debug_db.infos:
                if isinstance(di, DebugType):
                    # TODO: prevent this from being emitted twice in some way?
                    output_stream.emit(DebugData(di))

    def generate_global(self, var, output_stream, debug):
        """Generate code for a global variable"""
        alignment = Alignment(var.alignment)
        output_stream.emit(alignment)
        self._mark_global(output_stream, var)
        label = Label(var.name)
        output_stream.emit(label)
        if var.amount == 0 and var.value is None and not var.used_by:
            pass  # E.g. empty WASM func_table
        elif var.amount > 0:
            if var.value:
                assert isinstance(var.value, tuple)
                for part in var.value:
                    if isinstance(part, bytes):
                        # Emit plain byte data:
                        for byte in part:
                            output_stream.emit(DByte(byte))
                    elif isinstance(part, tuple) and part[0] is ir.ptr:
                        # Emit reference to a label:
                        assert isinstance(part[1], str)
                        labels_refs = {
                            (2, Endianness.LITTLE): data_instructions.Dw2,
                            (4, Endianness.LITTLE): data_instructions.Dcd2,
                            (8, Endianness.LITTLE): data_instructions.Dq2,
                        }
                        key = (
                            self.arch.info.get_size(part[0]),
                            self.arch.info.endianness,
                        )
                        op_cls = labels_refs[key]
                        output_stream.emit(op_cls(part[1]))
                    else:
                        raise NotImplementedError(str(part))
            else:
                output_stream.emit(DZero(var.amount))
        else:  # pragma: no cover
            raise NotImplementedError()
        self.debug_db.map(var, label)
        if self.debug_db.contains(label) and debug:
            dv = self.debug_db.get(label)
            dv.address = label.name
            output_stream.emit(DebugData(dv))

    def generate_function(self, ir_function, output_stream, debug=False):
        """Generate code for one function into a frame"""
        self.logger.info(
            "Generating %s code for function %s",
            str(self.arch),
            ir_function.name,
        )

        self.reporter.heading(3, f"Log for {ir_function}")
        self.reporter.dump_ir(ir_function)

        # Split too large basic blocks in smaller chunks (for literal pools):
        # TODO: fix arbitrary number of 500. This works for arm and thumb..
        split_block_nr = 1
        for block in ir_function:
            max_block_len = 200
            while len(block) > max_block_len:
                self.logger.debug("%s too large, splitting up", str(block))
                newname = f"{ir_function.name}_splitted_block_{split_block_nr}"
                split_block_nr += 1
                _, block = split_block(
                    block, pos=max_block_len, newname=newname
                )

        self._mark_global(output_stream, ir_function)
        output_stream.emit(SetSymbolType(ir_function.name, "func"))

        # Create a frame for this function:
        frame_name = ir_function.name
        frame = self.arch.new_frame(frame_name, ir_function)
        frame.debug_db = self.debug_db  # Attach debug info
        self.debug_db.map(ir_function, frame)

        # Select instructions and schedule them:
        self.select_and_schedule(ir_function, frame)

        self.reporter.dump_frame(frame)

        # Do register allocation:
        self.register_allocator.alloc_frame(frame)

        # TODO: Peep-hole here?
        # frame.instructions = [i for i in frame.instructions]
        if hasattr(self.arch, "peephole"):
            frame.instructions = self.arch.peephole(frame)

        self.reporter.dump_frame(frame)

        # Add label and return and stack adjustment:
        instruction_list = []
        output_stream = MasterOutputStream(
            [FunctionOutputStream(instruction_list.append), output_stream]
        )
        peep_hole_stream = PeepHoleStream(output_stream)

        if self.arch.name == "atalla" and self.packetize:
            # Collect ALL instructions (prologue + body + epilogue + exit) into
            # a staging list so the packetizer sees the full hazard picture.
            staging = []
            staging_stream = PeepHoleStream(
                MasterOutputStream([FunctionOutputStream(staging.append)])
            )

            if hasattr(frame, "buckets_by_block") and frame.buckets_by_block:
                self._emit_packets_from_buckets(frame, staging_stream, debug=debug, slots_per_packet=4)
            else:
                self.emit_frame_to_stream(frame, staging_stream, debug=debug)

            if isinstance(ir_function, ir.Function):
                if hasattr(ir_function, "return_ty") and ir_function.return_ty is not None:
                    rv = (ir_function.return_ty, frame.rv_vreg if hasattr(frame, "rv_vreg") else None)
                else:
                    rv = None
                for ins in self.arch.gen_function_exit(rv):
                    staging_stream.emit(ins)

            staging_stream.flush()

            # Now run packetization over the complete staged list and emit.
            packed = self._pack_flat_vliw(staging, max_width=4)
            for ins in packed:
                peep_hole_stream.emit(ins)
            peep_hole_stream.flush()
        else:
            if hasattr(frame, "buckets_by_block") and frame.buckets_by_block:
                self._emit_packets_from_buckets(frame, peep_hole_stream, debug=debug, slots_per_packet=4)
            else:
                self.emit_frame_to_stream(frame, peep_hole_stream, debug=debug)
            peep_hole_stream.flush()

            if isinstance(ir_function, ir.Function):
                if hasattr(ir_function, "return_ty") and ir_function.return_ty is not None:
                    rv = (ir_function.return_ty, frame.rv_vreg if hasattr(frame, "rv_vreg") else None)
                else:
                    rv = None
                for ins in self.arch.gen_function_exit(rv):
                    peep_hole_stream.emit(ins)

        # Emit function debug info:
        if self.debug_db.contains(frame) and debug:
            func_end_label = self.debug_db.new_label()
            output_stream.emit(Label(func_end_label))
            d = self.debug_db.get(frame)
            d.begin = frame_name
            d.end = func_end_label
            dd = DebugData(d)
            output_stream.emit(dd)

        self.reporter.dump_instructions(instruction_list, self.arch)


    def select_and_schedule(self, ir_function, frame):
        """Perform instruction selection and scheduling"""
        self.logger.debug("Selecting instructions")

        tree_method = True
        if tree_method:
            self.instruction_selector.select(ir_function, frame)
        else:  # pragma: no cover
            raise NotImplementedError("TODO")
            # Build a graph:
            # self.sgraph_builder.build(ir_function, function_info)
            # reporter.message('Selection graph')
            # reporter.dump_sgraph(sgraph)

            # Schedule instructions:
            # self.instruction_scheduler.schedule(sgraph, frame)

    def emit_frame_to_stream(self, frame, output_stream, debug=False):
        """
        Add code for the prologue and the epilogue. Add a label, the
        return instruction and the stack pointer adjustment for the frame.
        At this point we know how much stack space must be reserved for
        locals and what registers should be saved.
        """
        # Materialize the register allocated instructions into a stream of
        # real instructions.
        self.logger.debug("Emitting instructions")

        debug_data = []

        # Prefix code:
        output_stream.emit_all(self.arch.gen_prologue(frame))

        for instruction in frame.instructions:
            assert isinstance(instruction, Instruction), str(instruction)

            # If the instruction has debug location, emit it here:
            if self.debug_db.contains(instruction) and debug:
                d = self.debug_db.get(instruction)
                assert isinstance(d, DebugLocation)
                if not d.address:
                    label_name = self.debug_db.new_label()
                    d.address = label_name
                    source_line = d.loc.get_source_line()
                    output_stream.emit(Comment(source_line))
                    output_stream.emit(Label(label_name))
                    debug_data.append(DebugData(d))

            if isinstance(instruction, VirtualInstruction):
                # Process virtual instructions
                if isinstance(instruction, RegisterUseDef):
                    pass
                elif isinstance(instruction, ArtificialInstruction):
                    output_stream.emit(instruction)
                elif isinstance(instruction, InlineAssembly):
                    self._generate_inline_assembly(
                        instruction.template,
                        instruction.output_registers,
                        instruction.input_registers,
                        output_stream,
                    )
                else:  # pragma: no cover
                    raise NotImplementedError(str(instruction))
            else:
                # Real instructions:
                assert all(r.is_colored for r in instruction.registers)
                output_stream.emit(instruction)

        # Postfix code, like register restore and stack adjust:
        output_stream.emit_all(self.arch.gen_epilogue(frame))

        # Last but not least, emit debug infos:
        for dd in debug_data:
            output_stream.emit(dd)

        # Check if we know what variables are live
        for tmp in frame.ig.temp_map:
            if self.debug_db.contains(tmp):
                self.debug_db.get(tmp)
                # print(tmp, di)
                # frame.live_ranges(tmp)
                # print('live ranges:', lr)

    def _emit_packets_from_buckets(self, frame, output_stream, debug=False, slots_per_packet=4):
        def fresh_nop():
            n = self.arch.make_nop()
            n.is_nop = True
            return n

        output_stream.emit_all(self.arch.gen_prologue(frame))

        for blk, depth_list in frame.buckets_by_block.items():
            blk_name = getattr(blk, "name", None)
            if blk_name:
                output_stream.emit(Label(blk_name))

            for insts in depth_list:
                real = [i for i in insts
                        if isinstance(i, Instruction)
                        and (not isinstance(i, VirtualInstruction) or isinstance(i, InlineAssembly))]
                if not real:
                    for _ in range(slots_per_packet):
                        output_stream.emit(fresh_nop())
                    continue
                for i in range(0, len(real), slots_per_packet):
                    chunk = real[i:i+slots_per_packet]
                    while len(chunk) < slots_per_packet:
                        chunk.append(fresh_nop())
                    for ins in chunk:
                        if isinstance(ins, InlineAssembly):
                            self._generate_inline_assembly(
                                ins.template,
                                ins.output_registers,
                                ins.input_registers,
                                output_stream,
                            )
                        else:
                            output_stream.emit(ins)

        output_stream.emit_all(self.arch.gen_epilogue(frame))

    def _generate_inline_assembly(
        self, assembly_source, output_registers, input_registers, ostream
    ):
        """Emit inline assembly template to outstream."""
        from ..common import DiagnosticsManager

        # poor mans assembly api copied from api.py

        # Replace template variables with actual registers:
        mapping = {
            f"%{index}": str(register.get_real())
            for index, register in enumerate(
                output_registers + input_registers
            )
        }

        for k, v in mapping.items():
            assembly_source = assembly_source.replace(k, v)

        diag = DiagnosticsManager()
        assembler = self.arch.assembler
        assembler.prepare()
        assembler.assemble(assembly_source, ostream, diag)
        # TODO: this flush action might be troublesome, since it might emit
        # a literal pool on ARM.
        assembler.flush()

    def _mark_global(self, output_stream, value):
        # Indicate static or global variable.
        assert isinstance(value, ir.GlobalValue)

        if value.binding == ir.Binding.GLOBAL:
            output_stream.emit(Global(value.name))

    def _pack_flat_vliw(self, instructions, max_width=4):
        import sys, os
        sys.path.insert(0, os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "..")
        ))
        try:
            from instruction_latency import latency as latency_map
        except ImportError:
            latency_map = {}

        from ..arch.generic_instructions import Label, VirtualInstruction
        from ..arch.atalla.instructions import BranchBase, Jal, Jalr

        FU_SCALAR_ALU  = "scalar_alu"   # Unit 1: add_s, sub_s, or_s, and_s, xor_s,
        FU_SCALAR_DIV  = "scalar_div"   # Unit 2: div_s, mod_s, divi_s, modi_s,
        FU_BF16_ADD    = "bf16_add"     # Unit 3: add_bf, sub_bf, mul_bf
        FU_SCALAR_MUL  = "scalar_mul"   # Unit 4: mul_s, muli_s
        FU_SCALAR_LDST = "scalar_ldst"  # Unit 5: lw_s, sw_s, lhw_s, shw_s
        FU_VEC_ALU     = "vec_alu"      # Vector ALU lane: add_vv, sub_vv, mul_vv,
        FU_GSAU        = "gsau"         # GSAU lane: gemm_vv, lw_vi
        FU_EXP         = "exp"          # EXP lane: expi_vi
        FU_VLSU        = "vlsu"         # VLSU (4 units, one per scpad): vreg_ld, vreg_st
        FU_SCPAD       = "scpad"        # Scpad (SDMA): scpad_ld, scpad_st

        SCALAR_FUS = {FU_SCALAR_ALU, FU_SCALAR_DIV, FU_BF16_ADD,
                      FU_SCALAR_MUL, FU_SCALAR_LDST}
        VEC_LANE_FUS = {FU_VEC_ALU, FU_GSAU, FU_EXP}
        MAX_VEC_LANES = 2
        MAX_VLSU      = 4  # one per scpad SID

        OP_TO_FU = {
            # Unit 1 – Scalar ALU
            "add_s":  FU_SCALAR_ALU, "sub_s":  FU_SCALAR_ALU,
            "or_s":   FU_SCALAR_ALU, "and_s":  FU_SCALAR_ALU,
            "xor_s":  FU_SCALAR_ALU, "sll_s":  FU_SCALAR_ALU,
            "srl_s":  FU_SCALAR_ALU, "sra_s":  FU_SCALAR_ALU,
            "lui_s":  FU_SCALAR_ALU, "li_s":   FU_SCALAR_ALU,
            "addi_s": FU_SCALAR_ALU, "subi_s": FU_SCALAR_ALU,
            "ori_s":  FU_SCALAR_ALU, "andi_s": FU_SCALAR_ALU,
            "xori_s": FU_SCALAR_ALU, "slli_s": FU_SCALAR_ALU,
            "srli_s": FU_SCALAR_ALU, "srai_s": FU_SCALAR_ALU,
            "div_s":   FU_SCALAR_DIV, "mod_s":   FU_SCALAR_DIV,
            "divi_s":  FU_SCALAR_DIV, "modi_s":  FU_SCALAR_DIV,
            "bfts_s":  FU_SCALAR_DIV, "rcp_bf":  FU_SCALAR_DIV,
            "sqrt_bf": FU_SCALAR_DIV, "stbf_s":  FU_SCALAR_DIV,
            "add_bf": FU_BF16_ADD, "sub_bf": FU_BF16_ADD, "mul_bf": FU_BF16_ADD,
            "mul_s": FU_SCALAR_MUL, "muli_s": FU_SCALAR_MUL,
            "lw_s":  FU_SCALAR_LDST, "sw_s":  FU_SCALAR_LDST,
            "lhw_s": FU_SCALAR_LDST, "shw_s": FU_SCALAR_LDST,
            "add_vv":   FU_VEC_ALU, "sub_vv":   FU_VEC_ALU, "mul_vv":   FU_VEC_ALU,
            "rsum_vi":  FU_VEC_ALU, "rmin_vi":  FU_VEC_ALU, "rmax_vi":  FU_VEC_ALU,
            "mgt_mvv":  FU_VEC_ALU, "mlt_mvv":  FU_VEC_ALU,
            "meq_mvv":  FU_VEC_ALU, "mneq_mvv": FU_VEC_ALU,
            "mgt_mvs":  FU_VEC_ALU, "mlt_mvs":  FU_VEC_ALU,
            "meq_mvs":  FU_VEC_ALU, "mneq_mvs": FU_VEC_ALU,
            "add_vs":   FU_VEC_ALU, "sub_vs":   FU_VEC_ALU, "mul_vs":   FU_VEC_ALU,
            "gemm_vv": FU_GSAU, "lw_vi": FU_GSAU,
            "expi_vi": FU_EXP,
            "vreg_ld": FU_VLSU, "vreg_st": FU_VLSU,
            "scpad_ld": FU_SCPAD, "scpad_st": FU_SCPAD,
        }

        def make_nop():
            return self.arch.make_nop()

        def get_op(ins):
            s = str(ins).strip()
            return s.split()[0] if s else ""

        def get_fu(ins):
            return OP_TO_FU.get(get_op(ins))

        def is_branch(ins):
            return getattr(ins, "is_jump", False) or isinstance(ins, (BranchBase, Jal, Jalr))

        blocks = []
        current = []
        for ins in instructions:
            if isinstance(ins, Label):
                if current:
                    blocks.append(current)
                current = [ins]
            else:
                current.append(ins)
                if is_branch(ins):
                    blocks.append(current)
                    current = []
        if current:
            blocks.append(current)

        result = []

        for block in blocks:
            labels     = [ins for ins in block if isinstance(ins, Label)]
            real_insts = [ins for ins in block if not isinstance(ins, (Label, VirtualInstruction))]
            result.extend(labels)

            if not real_insts:
                continue

            n = len(real_insts)

            # ---- Build dependency graph for this basic block ----
            #
            # Each entry deps[i] is a list of (j, edge_latency): instruction i
            # may not issue before issue_cycle[j] + edge_latency. Edge kinds:
            #
            #   RAW  writer j -> reader i   edge_latency = latency(j)
            #   WAW  writer j -> writer i   edge_latency = latency(j)
            #   WAR  reader j -> writer i   edge_latency = 1
            #   Mem  prev mem op j -> next mem op i   edge_latency = 1
            #   Mem(alias)  store j to mem_key -> later op i to mem_key
            #               edge_latency = latency(j)
            #
            # A previous version of this packetizer skipped WAR/WAW edges and
            # used the within-packet hazard check + linear scan order to keep
            # things in-order. That fails on basic vector tests: PPCI emits
            # patterns like `lw_s x9; ...; li_s x9, 0` where the linear scan
            # picks the later `li_s` (no input dependencies) before the
            # earlier `lw_s` reader chain finishes, so the reader observes the
            # wrong value. Adding explicit WAR/WAW edges preserves the
            # producer/consumer ordering encoded in the linear stream.
            #
            # The memory chain covers every memory-touching FU (scalar LDST,
            # VLSU, SDMA/SCPAD, GSAU) because the SDMA path writes scratchpad
            # while VLSU/GSAU read and write the same scratchpad. Without
            # alias analysis we cannot prove independence, so we conservatively
            # serialise the entire group; the per-(base,imm) `mem_key` edge
            # additionally enforces store-then-load latency for scalar mem.
            MEM_TOUCH_FUS = {FU_SCALAR_LDST, FU_VLSU, FU_SCPAD, FU_GSAU}

            deps = [[] for _ in range(n)]

            ins_op = [get_op(ins) for ins in real_insts]
            ins_lat = [latency_map.get(op, 1) for op in ins_op]
            ins_fu = [get_fu(ins) for ins in real_insts]
            ins_branch = [is_branch(ins) for ins in real_insts]
            ins_reads = [list(getattr(ins, "used_registers", [])) for ins in real_insts]
            ins_writes = [list(getattr(ins, "defined_registers", [])) for ins in real_insts]

            ins_is_load = [False] * n
            ins_is_store = [False] * n
            ins_is_mem = [False] * n
            ins_mem_key = [None] * n
            for i, ins in enumerate(real_insts):
                fu = ins_fu[i]
                op = ins_op[i]
                is_load = fu == FU_SCALAR_LDST and op.startswith("lw")
                is_store = fu == FU_SCALAR_LDST and op.startswith("sw")
                ins_is_load[i] = is_load
                ins_is_store[i] = is_store
                ins_is_mem[i] = fu in MEM_TOUCH_FUS
                if (is_load or is_store) and hasattr(ins, "rs1") and hasattr(ins, "imm12"):
                    base = ins.rs1.num if hasattr(ins.rs1, "num") else ins.rs1
                    ins_mem_key[i] = (base, ins.imm12)

            last_def = {}       # reg.num -> producer index
            last_read = {}      # reg.num -> most recent consumer index since last def
            last_mem = None     # most recent memory-touching op index (chain head)
            last_store_at = {}  # scalar mem_key -> last store index

            for i in range(n):
                reads = ins_reads[i]
                writes = ins_writes[i]
                is_mem = ins_is_mem[i]
                mem_key = ins_mem_key[i]

                # RAW: depend on the most recent writer of each read register.
                for r in reads:
                    rn = r.num
                    if rn in last_def:
                        j = last_def[rn]
                        deps[i].append((j, ins_lat[j]))

                # WAW + WAR for each written register.
                for r in writes:
                    rn = r.num
                    if rn in last_def:
                        j = last_def[rn]
                        deps[i].append((j, ins_lat[j]))
                    if rn in last_read:
                        j = last_read[rn]
                        deps[i].append((j, 1))

                for r in writes:
                    last_def[r.num] = i
                    last_read.pop(r.num, None)
                for r in reads:
                    last_read[r.num] = i

                if is_mem:
                    if last_mem is not None:
                        deps[i].append((last_mem, 1))
                    if mem_key is not None and mem_key in last_store_at:
                        j = last_store_at[mem_key]
                        deps[i].append((j, ins_lat[j]))
                    last_mem = i
                    if ins_is_store[i] and mem_key is not None:
                        last_store_at[mem_key] = i

                # Branches terminate a basic block; pin every prior instruction
                # so the branch is the very last thing scheduled.
                if ins_branch[i]:
                    for j in range(i):
                        deps[i].append((j, 1))

            # Deduplicate edges (keep the maximum latency per predecessor).
            for i in range(n):
                if not deps[i]:
                    continue
                best = {}
                for (j, lat) in deps[i]:
                    if lat > best.get(j, -1):
                        best[j] = lat
                deps[i] = list(best.items())

            successors = [[] for _ in range(n)]
            for i in range(n):
                for (j, lat) in deps[i]:
                    successors[j].append((i, lat))

            # ---- Critical-path priority: longest weighted path to a sink ----
            cp = [0] * n
            for i in range(n - 1, -1, -1):
                best = 0
                for (k, edge_lat) in successors[i]:
                    cand = edge_lat + cp[k]
                    if cand > best:
                        best = cand
                cp[i] = best

            # ---- List schedule into VLIW packets ----
            indeg = [len(deps[i]) for i in range(n)]
            ready_cycle = [0] * n
            issue_cycle = [-1] * n
            scheduled_count = 0
            current_cycle = 0

            while scheduled_count < n:
                packet_reads = set()
                packet_writes = set()
                scalar_fu_used = set()
                vec_lanes_used = set()
                vlsu_in_packet = 0
                sdma_in_packet = False
                count = 0
                packet = []

                # Candidates whose predecessors have all completed by current_cycle.
                candidates = [
                    i for i in range(n)
                    if issue_cycle[i] == -1
                    and indeg[i] == 0
                    and ready_cycle[i] <= current_cycle
                ]
                # Highest critical-path priority first; break ties by source
                # index so that for two equally-good candidates we keep the
                # natural ordering produced by the upstream scheduler.
                candidates.sort(key=lambda i: (-cp[i], i))

                emitted_branch = False
                for i in candidates:
                    if count >= max_width:
                        break
                    if emitted_branch:
                        break

                    if ins_branch[i]:
                        # Branches must be solo in slot 0. The dependency graph
                        # already pins them after every other instruction in
                        # the block, so by the time `i` is a candidate the
                        # rest of the block has been scheduled.
                        if count == 0:
                            result.append(real_insts[i])
                            issue_cycle[i] = current_cycle
                            packet.append(i)
                            count = 1
                            for _ in range(max_width - 1):
                                result.append(make_nop())
                            emitted_branch = True
                            break
                        else:
                            continue

                    fu = ins_fu[i]
                    if fu in SCALAR_FUS and fu in scalar_fu_used:
                        continue
                    if fu in VEC_LANE_FUS:
                        if fu in vec_lanes_used:
                            continue
                        if len(vec_lanes_used) >= MAX_VEC_LANES:
                            continue
                    if fu == FU_VLSU and vlsu_in_packet >= MAX_VLSU:
                        continue
                    if fu == FU_SCPAD and sdma_in_packet:
                        continue

                    reads = ins_reads[i]
                    writes = ins_writes[i]
                    if any(r.num in packet_writes for r in reads):
                        continue
                    if any(d.num in packet_reads or d.num in packet_writes for d in writes):
                        continue

                    result.append(real_insts[i])
                    issue_cycle[i] = current_cycle
                    packet.append(i)
                    count += 1

                    for r in reads:
                        packet_reads.add(r.num)
                    for r in writes:
                        packet_writes.add(r.num)

                    if fu in SCALAR_FUS:
                        scalar_fu_used.add(fu)
                    elif fu in VEC_LANE_FUS:
                        vec_lanes_used.add(fu)
                    elif fu == FU_VLSU:
                        vlsu_in_packet += 1
                    elif fu == FU_SCPAD:
                        sdma_in_packet = True

                if not emitted_branch:
                    for _ in range(max_width - count):
                        result.append(make_nop())

                # Release successors of everything we just scheduled.
                for i in packet:
                    for (k, edge_lat) in successors[i]:
                        new_ready = current_cycle + edge_lat
                        if new_ready > ready_cycle[k]:
                            ready_cycle[k] = new_ready
                        indeg[k] -= 1

                scheduled_count += count
                current_cycle += 1

        return result
