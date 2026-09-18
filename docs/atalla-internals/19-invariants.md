# 19 — Invariants

Each row: what / established where / checked where / who depends / what breaks.

| # | Invariant | Established | Checked | Depended on by | If violated |
|---|-----------|-------------|---------|----------------|-------------|
| 1 | IR: entry block first, every block reachable and terminated by exactly one `FinalInstruction`, phi inputs match predecessors, uses dominated by defs | `CCodeGenerator.gen_function_def` (+ `delete_unreachable`), opt passes | `verify_module` (`irutils/verify.py`) before/after `optimize` and in `ir_to_stream` | `SelectionGraphBuilder` (assumes every value is in `value_map` when used; BFS block order), `Mem2Reg` (`CfgInfo` dominators) | `KeyError` in `get_value`, assertion in verifier |
| 2 | IR types: `Binop` operands equal result type except `vec` results with one `bf16`/`vec` operand | frontend `coerce`/`get_common_type` | `verify.py:131-147` | patterns assume `ADDVEC(vecreg, reg)` means a scalar bf16 in an `x` register | `IrFormError`/`TypeError` |
| 3 | Every IR value used by the DAG has a `value_map` entry before use within its block; cross-block values are phis or REG nodes with vregs | DAG builder + `DagSplitter.check_vreg` | implicit | tree building | `KeyError`/malformed trees |
| 4 | Selection DAG is acyclic and each chained node has exactly one control input | `chain()` | `topological_sort_modified` asserts "DAG has cycles" | ordering | assertion |
| 5 | Every root tree reduces to `stm`; every `reg`-yielding rule returns a `Register` of the class named by its non-terminal | pattern authors | `TreeSelector.gen` raises `Tree … not covered`; `Operand` setter asserts class | RA (class = `type(vreg)`), encode | `RuntimeError` or `AssertionError` in the instruction constructor |
| 6 | `Instruction.used_registers`/`defined_registers` are exactly the `read`/`write` operands + `extra_uses/defs` | `Operand(read=, write=)` declarations | none | liveness, interference, spill rewriting (`replace_register`) | wrong liveness → wrong allocation; e.g. `ScpadLd.rs1_rd1` is `read+write`, so the allocator treats it as a def |
| 7 | Branch/jump instructions list every successor `Label` (or jump instruction) in `jumps`; the fall-through after a conditional branch is the explicit `jal x0, no_label` | `pattern_cjmpi`, `pattern_jmp`, `arch.branch` | none | `FlowGraph` leaders/edges (no implicit fall-through edges) | liveness holes → clobbered live values |
| 8 | After `alloc_frame` every register operand of every non-virtual instruction is coloured | `apply_colors` | `emit_frame_to_stream:290` `assert all(r.is_colored …)` | `encode` (`Register.num`) | assertion |
| 9 | Precoloured registers never receive a different colour; two precoloured nodes never coalesce | IRC (`precolored` set, constrained moves) | `apply_colors` asserts `reg.color == node.reg.color` | ABI | assertion |
| 10 | Values live across a call do not reside in `caller_save` registers | clobber edges from `Jal(clobbers=caller_save)` | none | correctness across calls | **currently unsound**: `x9, x11, x18–x27` are in no save set; a callee may overwrite them |
| 11 | `fprel` instructions have an `imm12` that is a raw negative frame offset until the peephole adds `round_up(stacksize+8)-8`; the peephole runs exactly once, after RA, before emission | patterns set `fprel`; `generate_function` order | none | stack layout | double or missing fix-up → wrong addresses. Spill code inserted by RA also carries `fprel` and is fixed up correctly because the peephole runs after RA |
| 12 | `scpadfprel`/`VregLd/VregSt` offsets are final (never adjusted) | `AtallaArch.peephole:454-460` | none | scratchpad layout | — |
| 13 | `Frame.scpad_alloc` only sees size 64; every `vec` is 64 bytes, 64-aligned | `ArchInfo` `vec: TypeInfo(64,64)`, `scpad_alloc` raises otherwise | `ValueError` | patterns hard-code `num_cols=31, sid=3` | crash on other sizes |
| 14 | `x32`/`x33` are initialised before any vector spill/local is touched | `main` prologue only | none | every non-`main` entry point | garbage scratchpad addresses if code does not enter through `main` |
| 15 | Code section bytes are a multiple of 5 and every instruction is 5 bytes; labels sit on 5-byte boundaries | every instruction token is 40 bits; `Align(5)` per function; data lives in another section | none explicitly (relocation `//5` would silently floor) | `BR_i10`/`MI_jal_i25` division, disassembler | mis-targeted branches |
| 16 | Relocation immediates in the object file are zero and the symbol name is carried in the instruction operand | `encode()` overrides | none | linker | — |
| 17 | Section addresses are aligned to `section.alignment`; symbols are section-relative until layout | `Linker.layout_sections`, `inject_object` | none | `get_symbol_id_value` | — |
| 18 | The `Isa` is a module-level singleton shared by `instructions.py` and `vector_instructions.py`; `AtallaArch` instances share it and the `BurgSystem` is rebuilt per `CodeGenerator` | module import | none | pattern registration order = rule number order (tie-breaking) | duplicate/conflicting patterns silently resolved by cost then order |
| 19 | `ptr` is 32-bit and maps to `u32` everywhere (`type_infos["ptr"]`, `new_node` rewrite) | `AtallaArch.__init__` | none | patterns on `…U32`, spill `FPRELU32` | — |
| 20 | Phi copies never read a phi vreg that was already overwritten in the same block | `copy_phis_of_successors` two-step temp copy | none | loop correctness | — (this is why each loop back-edge has 4 copies) |

Pipeline-ordering invariants (why the stages are in this order): allocation needs the complete
instruction list including `gen_function_enter/exit` moves (emitted inside `select`) and call
clobbers; the peephole needs colours to detect identity moves and needs the final `stacksize`
(spills grow it) to compute `fprel` fix-ups; the prologue/epilogue need `stacksize`, `scpad_stacksize`,
`out_calls` and `used_regs`, all final only after RA — so they are generated at emission time, not
during selection.
