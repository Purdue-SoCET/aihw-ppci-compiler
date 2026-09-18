# 03 — The actual compilation pipeline

Each stage: **entry** (file:function), **input → output**, **key structures**, **side effects**,
**next stage**. All verified by reading and by the traces in ch. 21.

```mermaid
flowchart TD
  A[".c source"] -->|CPreProcessor.process_file| B["token stream"]
  B -->|prepare_for_parsing + CParser.parse<br/>(CSemantics builds AST nodes)| C["C AST (CompilationUnit)"]
  C -->|CCodeGenerator.gen_code| D["ir.Module (SSA-ish IR, allocas + load/store)"]
  D -->|api.optimize x3: Mem2Reg, RemoveAddZero, ConstantFolder, CSE, TailCall, LoadAfterStore, DeleteUnused, Clean| E["ir.Module (phis, no promotable allocas)"]
  E -->|CodeGenerator.generate → generate_function| F
  subgraph F["per function"]
    F1["prepare_function_info: labels, phi vregs, arg vregs"] --> F2["SelectionGraphBuilder.build → SelectionGraph (SGNode/SGValue)"]
    F2 --> F3["DagSplitter.split_into_trees → list of Tree + Label"]
    F3 --> F4["gen_function_enter + TreeSelector.gen per tree → Frame.instructions (vregs)"]
    F4 --> F5["GraphColoringRegisterAllocator.alloc_frame (+ spills, +scratchpad spills)"]
    F5 --> F6["AtallaArch.peephole (fprel fix-up, identity-move removal)"]
    F6 --> F7["emit_frame_to_stream: gen_prologue, body, gen_epilogue → PeepHoleStream → MasterOutputStream"]
  end
  F7 --> G["BinaryOutputStream: encode() bytes, symbols, RelocationEntry → ObjectFile"]
  F7 --> H["TextOutputStream: assembly text (-S)"]
  G -->|obj.save| I[".o (JSON)"]
  I -->|python -m ppci ld| J["Linker: merge, layout, relocate"]
  J -->|write_elf ET_REL| K["ELF32 LE, e_machine 0x270F"]
```

## Stage 0 — Driver
* `atalla_cc:174 main()` → subprocess per source. Nothing compiler-related happens here.

## Stage 1 — CLI and target creation
* `ppci/cli/atalla_cc.py:47 atalla_cc()`; `create_arch("atalla")` → `AtallaArch.__init__`
  (`ppci/arch/atalla/arch.py:199-250`).
* `AtallaArch.__init__` builds: `self.isa = isa + data_isa` (Isa merge, `ppci/arch/isa.py:34-41`),
  `self.regclass` (3 register classes), `ArchInfo(type_infos=..., register_classes=...)`
  (`ppci/arch/arch_info.py:34-60`, computes `value_classes` {ir type → Register subclass} and `alias`),
  `AtallaAssembler().gen_asm_parser(self.isa)` (Earley grammar from every instruction `Syntax`,
  `ppci/binutils/assembler.py:168-263`), ABI constants (`_arg_regs`, `_ret_reg`, `callee_save=()`,
  `caller_save=(R10,R12..R17)`), `scpad_fp_start = 2000000`.
* Output: one `AtallaArch` instance shared by all later stages. Side effect: `lru_cache`.

## Stage 2 — Frontend: source → `ir.Module`
* Entry `ppci/lang/atalla_c/api.py:20 atalla_c_to_ir()` → `CBuilder(march.info, coptions).build(src, filename)`
  (`builder.py:23-40`) → `_parse` (`:67-74`): `CPreProcessor(coptions).process_file` → tokens →
  `CSemantics(context)`, `CParser(coptions, semantics)`, `prepare_for_parsing(tokens, parser.keywords)`,
  `parser.parse(tokens)` → AST `CompilationUnit`. Then `CCodeGenerator(context).gen_code(ast)` → `ir.Module`.
* Key structures: `CContext` (type sizes: `vec` 64 B/64-aligned from `ArchInfo`, `float` 2 B),
  AST nodes in `ppci/lang/atalla_c/nodes/`, `irutils.Builder`.
* Output IR properties (verified in ch. 21 traces): every local is an `alloc` + `AddressOf` in the
  entry block; params stored to allocas; `vec` locals are `alloc 64 bytes aligned at 64`;
  a function ending in `return` always produces an unreachable trailing block and the warning
  "Function does not return a value" (`codegenerator.py:483-494`) — the block is deleted by
  `ir_function.delete_unreachable()` (`:502`).
* Next: optimization.

## Stage 3 — IR optimization
* `ppci/api.py:195 optimize()`. `verify_module` before and after. Level `0` → return; every other
  level runs the identical list three times (`:226-235`). `CJumpPass` is gated on `level == "3"` which
  is not a legal level (`OPT_LEVELS = ("0","1","2","s")`, `:192`) → never runs.
* Effects that matter downstream: `Mem2RegPromotor` turns scalar allocas into SSA values + `Phi`
  (`ppci/opt/mem2reg.py`); `vec` allocas are promoted too when only loaded/stored (the trace in ch. 21
  shows `vec v3 = v1 + v2` without any alloca) but **not** when their address escapes (passed to
  `add_vec(&v_add, …)`). `CleanPass` merges blocks (this is why block numbering has gaps).
* Next: code generation.

## Stage 4 — Code generation driver
* `ppci/api.py:284 ir_to_object()` (or `:256 ir_to_stream()` for `-S`) → `CodeGenerator(march, reporter,
  optimize_for="speed")` (`ppci/codegen/codegen.py:41-60`): builds `SelectionGraphBuilder`,
  `InstructionSelector1` (which builds the BURS rule table from `arch.isa.patterns`, weights (3,10,1)),
  `InstructionScheduler` (a no-op class), `GraphColoringRegisterAllocator`.
* `generate()` (`:62-98`): emits `section data`, `Global`/`SetSymbolType` for externals, globals via
  `generate_global` (`Alignment`, `Label`, `DByte`/`DZero`/`Dcd2`), then `section code` and
  `generate_function` per function.

## Stage 5 — Per-function lowering (`generate_function`, `codegen.py:143-222`)
1. Split blocks longer than 200 instructions (`:156-165`).
2. `Global(name)`, `SetSymbolType(name,"func")`.
3. `frame = arch.new_frame(name, fn)` → `Frame` (`ppci/arch/stack.py:42`).
4. `select_and_schedule` → `InstructionSelector1.select(fn, frame)` (ch. 10). Output: `frame.instructions`
   (list of `Instruction` with virtual registers), `frame.stacksize`, `frame.scpad_stacksize`,
   `frame.out_calls`, `frame.constants`.
5. `register_allocator.alloc_frame(frame)` (ch. 11). Mutates register `_color`s in place; may insert
   spill code and grow `frame.stacksize`/`scpad_stacksize`; deletes coalesced moves (none for Atalla).
6. `arch.peephole(frame)` (`ppci/arch/atalla/arch.py:448-487`): adds `round_up(stacksize+8)-8` to
   every `fprel` instruction's `imm12` (except `scpadfprel` and `VregLd/VregSt`), and drops identity
   moves. Returns a new instruction list.
7. `emit_frame_to_stream` (`:242-306`): `gen_prologue` → body (skips `RegisterUseDef`; expands
   `InlineAssembly` through the assembler; asserts all registers colored) → `gen_epilogue` (which also
   emits the literal pool: `Section("data")`, constants, `Section("code")`).
8. A second `gen_function_exit(rv)` call (`:204-210`) with `rv[1] is None` yields a single
   `RegisterUseDef(uses=set())` into the `PeepHoleStream`, which is never flushed → silently dropped.
   Verified: no `VUseDef` appears in any `.s` output.

## Stage 6 — Output streams
* `PeepHoleStream` (`ppci/codegen/peephole.py:18-54`): 2-entry window; removes an instruction whose
  `effect()` equals the next one's (only `Label` defines `effect()`, and labels are never removed →
  effectively a pass-through for Atalla).
* `OutputStream.emit` (`ppci/binutils/outstream.py:32-40`): `ArtificialInstruction`s (`Align`, `Section`)
  are `render()`ed into `Alignment`/`SectionInstruction`.
* `BinaryOutputStream.do_emit` (`:98-150`): `item.encode()` → `section.add_data`; `item.symbols()` →
  `Symbol` at current section offset; `item.relocations()` → `RelocationEntry(name, symbol_id, section,
  address+offset, addend)`; `Alignment` pads with zero bytes and raises `section.alignment`.
* `TextOutputStream.do_emit` (`:68-83`): `AtallaAsmPrinter.print_instruction` → `str(instruction)` →
  `Syntax.render`.

## Stage 7 — Object file
* `ObjectFile.save` → JSON (`ppci/binutils/objectfile.py:363-370`): sections (hex data, alignment),
  symbols, relocations, `arch: "atalla"`.

## Stage 8 — Link
* `Linker.link` (`ppci/binutils/linker.py:100-169`): `merge_objects` (concatenate same-named sections
  with alignment padding, remap symbol ids), `layout_sections` (assign `section.address` from the
  `.mmap`, build `Image`s), `check_undefined_symbols`, `do_relaxations` (no Atalla relocation defines
  `can_shrink` → no-op), `do_relocations` (ch. 14).

## Stage 9 — ELF
* `write_elf` (`ppci/format/elf/writer.py:23-48`), see ch. 02 §5 and ch. 15.

## Stages that do not exist
* **Instruction scheduling**: `InstructionScheduler.schedule` is `pass`
  (`ppci/codegen/instructionscheduler.py:7-11`) and is never called (`codegen.py:240` is commented out).
* **Packetization**: see ch. 13. Nothing runs.
* **Linker relaxation**: framework exists, no Atalla relocation opts in.
* **Function inlining**: `ppci/opt/inline.py` is a stub and is not imported by `optimize()`.
* **Runtime library**: `AtallaArch.get_runtime` is commented out; `Architecture.get_runtime` assembles
  an empty string; `atalla_cc` never passes `use_runtime`.

## Alternative paths and when they are taken

| Condition | Path |
|-----------|------|
| `-S` | `ir_to_stream` with `TextOutputStream`; no object, no link |
| `--ir` | IR writer after optimize; no backend |
| `-O0` | `optimize` returns immediately; allocas stay → every variable access is a stack load/store through `FPRELU32` patterns |
| `vec` alloca (amount == 64) | `Frame.scpad_alloc` → `SCPADREL` node → scratchpad addressing (`x33`) |
| any other alloca | `Frame.alloc` → `FPREL` node → `x8`-relative |
| vector vreg spilled | `scpad_alloc` slot + `LDRVEC/STRVEC` spill code |
| > 6 scalar args | 7th+ go to `StackLocation`s: caller `sw_s` to `SP+off`, callee `lw_s` from `FP+off` |
| inline `asm(...)` | `InlineAssembly` virtual instruction, assembled at emission with real registers |
| `frame.name == "main"` | prologue initialises `x32`/`x33` to `2000000` |
| `frame.scpad_stacksize != 0` | prologue/epilogue save/restore `x33` and bump `x32` |
