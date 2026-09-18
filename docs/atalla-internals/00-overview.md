# 00 — Overview

This manual is a source-level, forensic description of the AtallaC compiler in this repository.
It documents **what the code actually does**, established by reading the implementation and by
running it (all traces in chapter 21 are real outputs from `./atalla_cc` on this tree, branch
`atalla-arch-erwin17`, HEAD `a3371582`, on 2026-09-18).

Every claim is tagged:

* **Verified** — read in the implementation and/or reproduced by running it.
* **Inferred** — strongly suggested by the code but not executed or not fully traced.
* **Unknown** — cannot be decided from this repository alone (usually a hardware question).

Unless marked otherwise, statements are *Verified*.

## What the repository is

A fork of **PPCI** (Pure Python Compiler Infrastructure, upstream version string `0.5.9`,
`pyproject.toml:4`) with:

1. A new frontend package `ppci/lang/atalla_c/` (a copy of `ppci/lang/c/` with new types
   `vec`, `mask`, a 16‑bit `float`, and nine intrinsics).
2. New IR node classes and three new IR types appended to `ppci/ir.py`.
3. A new backend package `ppci/arch/atalla/` (registers, 40‑bit instruction encodings,
   selection patterns, relocations, ABI/prologue/epilogue, a target peephole).
4. Small but load-bearing edits to generic PPCI files (`codegen/irdag.py`,
   `codegen/dagsplit.py`, `codegen/instructionselector.py`, `codegen/registerallocator.py`,
   `arch/stack.py`, `irutils/verify.py`, `format/elf/writer.py`, `format/elf/headers.py`,
   `api.py`, `binutils/objectfile.py`).
5. Repo-root tooling: `atalla_cc` (driver), `disassemble.py`, `dump_elf.py`,
   `test_relocations.py`, `vliw_packetizer.py`, `instruction_latency.py`,
   `atalla_layout.mmap`.

## The one-paragraph pipeline (verified)

`./atalla_cc file.c` → `python -m ppci atalla_cc -m atalla -O2 file.c -c -o file.o`
→ `ppci.cli.atalla_cc.atalla_cc()` → `api.atalla_c_to_ir()` (preprocess → lex → parse with
semantic actions → `CCodeGenerator.gen_code()` → `ir.Module`) → `api.optimize()` (fixed pass
list ×3) → `api.ir_to_object()` → `CodeGenerator.generate()` per function:
IR → selection DAG (`SelectionGraphBuilder`) → forest of trees (`DagSplitter`) → BURS tree
matching against `@isa.pattern` rules (`TreeSelector`) emitting Atalla `Instruction` objects
with virtual registers into a `Frame` → iterated-register-coalescing allocator
(`GraphColoringRegisterAllocator`, coalescing effectively disabled, see ch. 11) → target peephole
(`AtallaArch.peephole`) → prologue/body/epilogue emitted to a `BinaryOutputStream` which calls
`Instruction.encode()` and records symbols/relocations into an `ObjectFile` → JSON `.o`.
Then `python -m ppci ld *.o -L atalla_layout.mmap` merges sections, assigns addresses,
applies relocations (`Relocation.apply`) and writes an ELF32 (`e_machine = 0x270F`).

There is **no instruction scheduling and no packetization on the default path** (ch. 12, 13).

## How to read this manual

* Chapters 03/04 give the pipeline and call graph. Chapter 05 gives the data model.
* Chapters 06–15 walk each stage in execution order.
* Chapter 16 collects everything Atalla-specific in one place; chapter 17 covers emulator/DMA
  interfaces (which are mostly *absent* from this repo).
* Chapter 19 lists invariants, 20 is the debugging guide, 21 the concrete traces,
  22 the open questions.

## Top findings a new engineer must know (each expanded later)

| # | Finding | Where |
|---|---------|-------|
| 1 | The generic PPCI files are imported from *this tree*, not from pip; `ppci/api.py:56-57` imports `vliw_packetizer` and `instruction_latency` from the **repo root**, so the compiler only runs with the repo root on `sys.path`. | ch. 02, 13 |
| 2 | Register coalescing never runs for Atalla because `AtallaArch.move()` returns instructions with `ismove=False`. Every SSA/phi copy survives as `addi_s rd, rs, 0` or `add_vv vd, vs, v0, m0`. | ch. 11 |
| 3 | Global variable access is mis-lowered: the `LABEL` pattern emits `lui/addi` **plus a load**, so `load g` becomes `*(*(&g))`. Inherited from RISC-V's literal-pool pattern with the pool removed. | ch. 10, 14, 21 |
| 4 | Signed `int` constants ≥ 2²⁵ have no selection pattern and crash the compiler (`Tree ... not covered`). | ch. 10, 22 |
| 5 | bf16 comparisons emit calls to `float16_lt`/`float16_eq`/… which do not exist anywhere → link fails. | ch. 16, 22 |
| 6 | Vector values that live in memory (address-taken `vec` locals, spills) go to a *second stack* in scratchpad memory addressed by `x33`/`x32`, allocated by `Frame.scpad_alloc`. | ch. 09, 11, 16 |
| 7 | Branch relocations are PC-relative to the **branch instruction itself** (not PC+5), divided by the 5-byte instruction width. | ch. 14 |
| 8 | Stack frames always reserve an extra 16 bytes because `round_up(0) == 16` and `callee_save == ()`. | ch. 09, 16 |
| 9 | Three packetizers exist; none runs on the default path. | ch. 13 |
| 10 | Hot-path `print()` calls dump the IR, every selection tree and every emitted instruction to stdout on every compile. | ch. 20 |
