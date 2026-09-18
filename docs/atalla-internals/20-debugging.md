# 20 — Debugging guide

## 20.1 Run configurations (verified)

```
# assembly only
./atalla_cc -S atalla_tests/forloop.c -o out.s
# IR after optimization (no backend)
python -m ppci atalla_cc -m atalla -O2 --ir atalla_tests/forloop.c -o out.ir
# object (JSON) + link + ELF
./atalla_cc atalla_tests/sample.c atalla_tests/helper.c -o out.elf --verbose   # prints the subcommands
# debug logging from the whole pipeline (allocator spill decisions, linker relocations, …)
./atalla_cc -S --cc-flag=--log --cc-flag=debug atalla_tests/vec_pressure.c -o out.s 2> log.txt
# HTML report with IR, selection trees, frame before/after RA (with use/def/live sets), final instructions
python -m ppci atalla_cc -m atalla -O2 --html-report report.html -S atalla_tests/sample.c -o out.s
# post-mortem debugger on any exception
python -m ppci atalla_cc -m atalla -O2 --pudb -S file.c -o out.s
# -O0 keeps every local in memory (useful to isolate mem2reg effects)
python -m ppci atalla_cc -m atalla -O0 -S file.c -o out.s
```

`atalla_cc` always prints (stdout) the module IR (`ir_module.display()`), each block name, the selection
trees per function (`print(tree)`), and `[emit] mapped <ins> to <node>` per emitted instruction — this is
the cheapest trace of instruction selection and is on by default. Redirect stdout to a file.

Log channels (`logging.getLogger(name)`): `ccodegen`, `optimize`, `codegen`, `instruction-selector`,
`selection-graph-builder`, `dag-splitter`, `regalloc` (`Placing … on stack`, `Spilling round`),
`flowgraph`, `interferencegraph`, `linker` (`Relocation section`, `Merging`), `elf`, `arch`.
Set `GraphColoringRegisterAllocator.verbose = True` / `InstructionSelector1.verbose = True` (class
attributes) for much more detail.

## 20.2 Breakpoints by question

| Question | Break at | Look at |
|----------|----------|---------|
| What AST did the parser build for an intrinsic? | `ppci/lang/atalla_c/semantics.py:992-1083` (`on_*`) | the returned expression node, `.typ` |
| Why did a type coerce/cast? | `semantics.py:1290 coerce` | `from_type`, `to_type`, `do_cast` |
| What IR does statement X produce? | `codegenerator.py:996 gen_expr`, `:1249 gen_binop` | `self.builder.block.instructions` |
| Which allocas survive mem2reg? | `ppci/opt/mem2reg.py:12 is_alloc_promotable` | `addr_inst.used_by` |
| What does the DAG look like? | `irdag.py:187` (after `sgraph.check()`) | `self.sgraph.nodes`, `function_info.value_map`; or set `InstructionSelector1.verbose=True` |
| Which values got vregs before selection? | `dagsplit.py:65 check_vreg` | `data_output.users`, `node.volatile` |
| Which rule was chosen for a tree? | `instructionselector.py:245 apply_rules` | `tree`, `rule`, `self.sys.get_rule(rule).template.__name__`, `tree.state.labels` |
| "Tree … not covered" | `instructionselector.py:202` | `tree` (print it); compare with the terminals in `instructions.py` patterns; add a pattern |
| What did a pattern emit? | the pattern function itself, or `instructionselector.py:172 InstructionContext.emit` | `instruction`, `self.frame.instructions[-5:]` |
| Liveness of a vreg | `flowgraph.py:145-160` | `ins.live_in`, `ins.live_out` per instruction |
| Why does vreg A interfere with B? | `interferencegraph.py:63-72` | `live_and_def`, `ins.clobbers` |
| Which register was assigned and why? | `registerallocator.py:772-781 assign_colors` | `node`, `takenregs`, `ok_regs` |
| Why was something spilled? | `registerallocator.py:686-693 select_spill`, `:700 rewrite_program` | priorities, `slot` |
| Final frame before emission | `codegen.py:187` (after peephole) | `frame.instructions` (repr shows physical names), `frame.stacksize`, `frame.scpad_stacksize`, `frame.out_calls` |
| Prologue/epilogue contents | `arch.py:318 gen_prologue`, `:390 gen_epilogue` | `frame.*`, `saved_registers`, `extras` |
| Bytes of one instruction | `encoding.py:417 encode` or call `ins.encode().hex()` in a REPL | token `bit_value` |
| Symbol/relocation creation | `outstream.py:121-140` | `item.symbols()`, `item.relocations()`, `address` |
| Relocation value | `linker.py:629-648 _do_relocation` | `sym_value`, `reloc_value`, `reloc.calc(...)` |
| Section addresses | `linker.py:320-331` | `section.address`, `section.alignment` |

## 20.3 Determining which pass is running

* Frontend/opt: the `optimize` logger prints `Optimizing module …`; individual passes log under their
  class name (`Mem2RegPromotor`, …) at DEBUG (`Promoting alloc …`, `Deleted N unused instructions`).
* Backend: `codegen` logs `Generating atalla-arch code for function <name>`; then stdout shows
  `===== Selection DAG for function <name> =====`; `regalloc` DEBUG logs `Starting iterative coloring`.
* A stack trace through `apply_rules` → your pattern function means selection; through `alloc_frame`
  means RA; through `emit_frame_to_stream`/`gen_prologue` means emission; through `_do_relocation` means link.

## 20.4 Tracing one value

1. Find its IR name in the printed module (e.g. `tmp_24_78`).
2. In the printed trees, look for `REGVEC[vreg4tmp_24_78]` / `MOVVEC[vreg4tmp_24_78]` — vreg names
   embed the IR name when created by `check_vreg`/`prepare_function_info` (`twain`).
3. `[emit] mapped …` lines show which instructions were emitted while that tree was being reduced.
4. Physical register: in the HTML report's post-RA frame table, or by breaking at `apply_colors` and
   inspecting `node.temps` → `node.reg`.
5. In `-S` output vregs are already replaced by physical names; correlate by instruction order.

## 20.5 Where to look when output is wrong

| Symptom | Likely place |
|---------|--------------|
| wrong stack offset | `AtallaArch.peephole` fix-up, `round_up`, the `fprel` flag on the emitting pattern |
| value clobbered around a call | caller/callee-save sets (`arch.py:249-250`), `Jal` clobbers, missing `RegisterUseDef` |
| wrong branch target | `BR_i10`/`MI_jal_i25.calc` convention (branch-relative), 5-byte alignment of labels |
| global variable garbage | `pattern_label1` extra `lw_s` (ch. 14.5) |
| `v0`/`m0` unexpectedly nonzero | `load_weights` writes `v0`; `move()` relies on `v0 == 0` |
| a vector op got `m0` when a mask was passed | `prepare_mask` only wraps non-`mask`-typed values; check the DAG has 3 children |
| assembler error on inline asm | mnemonic/operand order must match `Syntax` (`vreg_ld vd, rs1, rs2, num_cols, sid`) |
| `Tree not covered` | missing pattern; most often signed constants ≥ 2²⁵ or vector `|,&,^,<<,>>,/,SQRT,~` |
| ELF loader finds no segments | `ET_REL` output with no program headers (ch. 02) |
