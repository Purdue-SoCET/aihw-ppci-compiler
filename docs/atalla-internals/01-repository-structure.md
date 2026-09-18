# 01 — Repository structure

## Top level

| Path | Role | Classification |
|------|------|----------------|
| `atalla_cc` | Python driver script (`#!/usr/bin/env python3`, argparse). Shells out to `python -m ppci atalla_cc` per source and `python -m ppci ld`. Defaults `-O2`, `-m atalla`. | tooling |
| `atalla_layout.mmap` | Linker memory layout: `code` at `0x1000` (size `0x40000`), `data` at `0x80000` (size `0x40000`). | tooling/config |
| `Makefile` | Only a `clean` target. | tooling |
| `main.py` | Obsolete (“Do not use this file”). | dead |
| `disassemble.py` | Standalone Atalla ELF disassembler (own opcode table; does **not** use `ppci.arch.atalla`). Writes `disassembly.txt`. | tooling |
| `dump_elf.py` | Hex dump with hard-coded offsets (`code_start = 0x34`, `code_end = 0xF0`, and iterates in **6-byte** steps at `:31` although the ISA is 5 bytes). Not trustworthy. | tooling (stale) |
| `test_relocations.py` | Parses `disassembly.txt` + `atalla_layout.mmap` and checks branch targets/symbols/globals. | testing |
| `vliw_packetizer.py`, `instruction_latency.py` | Text-based packetizer + 7-entry latency table; imported by `ppci/api.py` but effectively never invoked (ch. 13). | dead |
| `verify_disassembly.py` | Not read in detail; not referenced by `atalla_cc`. | tooling (Unknown) |
| `ppci/` | The compiler package (upstream PPCI + Atalla changes). | see below |
| `atalla_tests/*.c` | The only Atalla test programs. No harness runs them; they are compiled by hand. | testing (samples) |
| `test/` | Upstream PPCI unit tests. **No file mentions Atalla** (`grep -ril atalla test/` is empty). | testing (generic) |
| `docs/` | Upstream Sphinx docs (no Atalla content) + this manual. | docs |
| `examples/`, `librt/`, `tools/` | Upstream PPCI material, unused by the Atalla flow. | generic |
| `requirements.txt` | Pins `ppci==0.5.8` (the pip package is **not** what runs; see ch. 02), `pydot`, `pudb`, … | build |
| `.github/workflows/*.yml` | Upstream CI: `black --check`, `flake8`, `pytest`. Runs only the generic tests. | CI |

## Inside `ppci/`

### Atalla-specific (new files)

| Path | Contents |
|------|----------|
| `ppci/arch/atalla/__init__.py` | exports `AtallaArch` |
| `ppci/arch/atalla/arch.py` | `AtallaArch` (ABI, prologue/epilogue, `move`, `gen_call`, peephole, ELF reloc numbers), `AtallaAssembler`, `round_up` |
| `ppci/arch/atalla/registers.py` | 34 scalar registers `x0..x33` (`x32`=SCPADSP, `x33`=SCPADFP), register class `reg` = `x9..x27` |
| `ppci/arch/atalla/vector_registers.py` | `v0..v31`, class `vecreg` = `v1..v31` |
| `ppci/arch/atalla/mask_registers.py` | `m0..m15`, class `maskreg` = `m1..m15` |
| `ppci/arch/atalla/tokens.py` | 16 token layouts, all 40 bits |
| `ppci/arch/atalla/instructions.py` | scalar ISA (R/I/BR/M/MI/S formats), `Isa` object, relocation registration, ~160 scalar selection patterns |
| `ppci/arch/atalla/vector_instructions.py` | vector/mask/SDMA ISA and ~55 patterns (shares the same `isa` object) |
| `ppci/arch/atalla/relocations.py` | 5 relocation classes |
| `ppci/arch/atalla/asm_printer.py` | prints `.section` and `nop` |
| `ppci/lang/atalla_c/` | full copy of the C frontend with Atalla types/intrinsics |
| `ppci/cli/atalla_cc.py` | CLI subcommand |
| `ppci/codegen/print_dag.py`, `test_print_dag.py` | DAG depth bucketing (dead packetizer support); imports `pydot` at module import time |

### Generic PPCI files carrying Atalla edits (verified by reading; markers noted)

| File | Atalla edit |
|------|-------------|
| `ppci/ir.py:157-165` | types `bf16`, `vec`, `mask`; `:1395-1627` nodes `Gemm`, `VecOpMasked`, `VecIndex`, `MakeMask`, `LoadWeights`, `ScpadLoad`, `ScpadStore`, `VectorLoad`, `VectorStore`, `SqrtBf` |
| `ppci/irutils/builder.py:155-193` | `emit_*` helpers for the new nodes |
| `ppci/irutils/verify.py:131-137` | relaxed operand-type check for vector `Binop` |
| `ppci/codegen/irdag.py` | `do_*` handlers for new nodes (`:224-351`), `SCPADREL`/`scpad_alloc` in `do_alloc` (`:434-458`), `atalla` name checks in `do_inline_asm` (`:524`, `:556`) |
| `ppci/codegen/dagsplit.py:80-84,91,96-127` | `tree_owner` map (dead packetizer support) |
| `ppci/codegen/instructionselector.py` | new terminals (`:105-123`, `:131-141`), `node_to_insts` bookkeeping and `print` in `emit` (`:158-187`), dead bucket builder (`:411-473`), prints (`:383`, `:504`) |
| `ppci/codegen/codegen.py` | `_emit_packets_from_buckets` (`:308-344`), second `gen_function_exit` call (`:204-210`), `hasattr(arch,"peephole")` hook (`:186-187`) |
| `ppci/codegen/registerallocator.py` | imports `AtallaVectorRegister` (`:119`); `make_fmt` VEC hack (`:186-187`); spill to scratchpad (`:709-712`) |
| `ppci/arch/stack.py` | `StackKind`, `StackLocation.kind`, `Frame.scpad_stacksize`, `Frame.scpad_alloc` (`:16-19`, `:66-96`) |
| `ppci/arch/arch.py` | unchanged interface; `get_reloc_type` default raises |
| `ppci/arch/target_list.py:18-21,37` | registers `AtallaArch` first; **`print(target_classes[0])` at import** |
| `ppci/api.py:36,56-57,269-272,379-418` | imports, `ir_module.display()` per compile, broken packetizer hook, `atalla_cc()` API |
| `ppci/binutils/objectfile.py:121-123` | comment about alignment experiments (no functional change) |
| `ppci/binutils/debuginfo.py:259-264` | `ScpadOffsetAddress` |
| `ppci/format/elf/writer.py:37,98` | `atalla` → 32-bit LE, `ElfMachine.ATALLA` |
| `ppci/format/elf/headers.py:120` | `ATALLA = 0x270F` |
| `ppci/lang/atalla_c/nodes/types.py`, `scope.py`, `context.py` | `vec`, `mask`, `float`(2 bytes) types |

Everything else under `ppci/` (other backends, wasm, pascal, …) is upstream and not on the Atalla path.

## Where each classic stage lives

| Stage | Entry | File |
|-------|-------|------|
| Driver | `main()` | `atalla_cc:174` |
| CLI | `atalla_cc()` | `ppci/cli/atalla_cc.py:47` |
| Preprocess/lex/parse/semantics | `CBuilder.build` → `_parse` | `ppci/lang/atalla_c/builder.py:23,67` |
| AST → IR | `CCodeGenerator.gen_code` | `ppci/lang/atalla_c/codegenerator.py:77` |
| IR optimization | `optimize` | `ppci/api.py:195` |
| IR → DAG | `SelectionGraphBuilder.build` | `ppci/codegen/irdag.py:140` |
| DAG → trees | `DagSplitter.split_into_trees` | `ppci/codegen/dagsplit.py:26` |
| Instruction selection | `TreeSelector.gen` | `ppci/codegen/instructionselector.py:196` |
| Register allocation | `GraphColoringRegisterAllocator.alloc_frame` | `ppci/codegen/registerallocator.py:233` |
| Target peephole | `AtallaArch.peephole` | `ppci/arch/atalla/arch.py:448` |
| Frame → stream | `CodeGenerator.emit_frame_to_stream` | `ppci/codegen/codegen.py:242` |
| Encoding | `Instruction.encode` | `ppci/arch/encoding.py:417` |
| Object file | `BinaryOutputStream.do_emit` | `ppci/binutils/outstream.py:98` |
| Link + relocate | `Linker.link`, `_do_relocation` | `ppci/binutils/linker.py:100,623` |
| ELF | `ElfWriter.export_object` | `ppci/format/elf/writer.py:113` |
| Scheduling | — | does not exist on the default path |
| Packetization | — | does not exist on the default path |
