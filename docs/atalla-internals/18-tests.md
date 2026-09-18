# 18 — Tests as specifications

## 18.1 What the CI actually runs

`.github/workflows/*.yml`: `black --check .`, `flake8 ppci test tools`, `pytest` (root `tox.ini` sets
`log_level=info`). `pytest` collects `test/` — **upstream PPCI tests only**; `grep -ril atalla test/` returns
nothing. So no automated test exercises the Atalla frontend, backend, or linker. (Note: `pytest` from
the repo root would also pick up `ppci/codegen/test_print_dag.py` and the root `test_relocations.py`;
the latter has a `main()` guarded by `__name__` and no `test_*` functions with pytest semantics that
survive — its `test_control_flow(instructions, symbols, …)` functions take arguments and would error
under pytest collection. Not executed; Inferred.)

Generic tests that do pin behaviour the Atalla backend relies on:

| Test | Establishes |
|------|-------------|
| `test/codegen/test_register_allocator.py` | IRC allocator on the `example` arch: interference, **coalescing works when `Mov(..., ismove=True)` is used** (`test_register_coalescing`), spilling, register classes with aliases (x86 xmm). This is the spec Atalla's `move()` fails to meet. |
| `test/codegen/test_burm.py` | Tree matching semantics (`State`, chain rules, structural equality). |
| `test/codegen/test_codegen.py` (`IrDagTestCase`) | DAG builder phi handling (`test_phi_register`), two regression bugs. |
| `test/samples/*` | End-to-end C/C3 samples for other targets — the closest thing to a conformance suite, none run for Atalla. |

## 18.2 The Atalla “test suite”: `atalla_tests/*.c`

Compiled by hand (`./atalla_cc -S atalla_tests/x.c`). Each file is a *specification by example* of a
feature. What each one pins down (verified by compiling on 2026-09-18 unless noted):

| File | Exercises | Verified outcome |
|------|-----------|------------------|
| `forloop.c` | scalar arithmetic, phi copies, `blt_s`/`jal`, prologue/epilogue | compiles; body has 3 copies per 2 ops (ch. 21) |
| `sample.c` | `scpad_load/store`, `vector_load/store`, `make_mask`, address-taken `vec` locals, `vec` by pointer to a function, `vec + vec + vec`, `vec * float`, `vec -= int`, `vec_op_masked("EXP")`, `gemm`, `v[5]`, `(int)float`, `helper()` external | compiles and links with `helper.c`; 6 branch relocations verified correct by `test_relocations.py` |
| `vv_instr.c`, `vs_instr.c` | vector-vector / vector-scalar ops | `vv_instr.c` compiles (ch. 21) |
| `masktest.c`, `intrinsictest.c`, `load_weights.c`, `testptr.c` | inline `asm` with `=v`/`v`/`r`, `mv_mts` via asm, masks, `RMIN`, `load_weights`, `vec*` through asm | not compiled in this investigation |
| `bftest.c` | bf16 `/` (rcp+mul), `sqrt`, pass `float*`, `(int)float` | compiles; a 2-byte local is stored with `sw_s` (ch. 21) |
| `int_pressure.c` | scalar register pressure (48 live values, `volatile`) | spills 4+ scalars to `x8`-relative slots |
| `vec_pressure.c` | vector pressure (40 live vectors) | spills 10 vectors to scratchpad slots `-64..-640`, `x32 -= 640` |
| `instructtest*.c` | per-format instruction coverage | not compiled here |
| `helper.c`/`help.h` | external function + multi-file link | links |

Behaviour documented **only** by these tests: the `(int)v[5]` idiom (`vmov_vts` + `bfts_s`),
`vec_op_masked("EXP", v, 0.0, mask)` requiring a float second operand, and masks being plain `int`s.

## 18.3 `test_relocations.py` (root)

Input: `disassembly.txt` + `atalla_layout.mmap` in the CWD (produced by `disassemble.py` from `output.elf`).
Three checks:

1. **Symbol range** — every symbol offset inside `code` or `data` ranges. Passes.
2. **Control flow** — for `jal|bgt_s|blt_s|beq_s|bne_s` (note: `bge_s`/`ble_s` are not matched), the last
   hex number on the line (`extract_target`, the disassembler's computed target) + `code_base` must equal
   a symbol. Passes for `sample.c + helper.c` (6/6). This validates `BR_i10`/`MI_jal_i25` arithmetic
   *against the disassembler's own convention* (branch-relative, ×5) — it cannot detect a convention
   mismatch with hardware.
3. **Global address** — finds `lui_s` immediately followed by `addi_s` and checks the reconstructed
   address is in `data`. The implementation is broken: a second `if m1 and m2:` block (`:130-135`)
   overrides the first and computes `addr = upper + int(m2.group(1))` where `group(1)` is the
   **destination register number**, and `upper` is the raw 25-bit field (not `<< 7`). Verified output on
   `sample.c`: `WRONG REGION … 0x3D29` (= 15625 + 32 from the `lui_s x32, 15625` prologue) and
   `INVALID ADDRESS: 0x1FFF409` (= 33551360 + 9 from the `0xFFFA0001` mask constant). Both are false
   positives; `sample.c` has no globals. It also does not test the extra `lw_s` bug (ch. 14.5).

## 18.4 Coverage gaps (verified absent)

No test for: global variable read/write correctness (broken), >6 arguments (works for scalars — ch. 21),
struct by value, `vec` by value (crashes), `switch`, signed big constants (crash), bf16 comparisons
(link failure), mask spills, `load_weights` clobbering `v0`, inline-asm register pressure, `-O0`,
`--ir` round-trip, ELF loading, any execution result. Nothing asserts the generated code's *semantics*.
