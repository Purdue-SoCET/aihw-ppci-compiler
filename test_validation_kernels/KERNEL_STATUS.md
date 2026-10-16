# Kernel validation status

Status of every test run by the `compiler_validation` CI workflow
(`.github/workflows/compiler_validation.yml`), what was wrong with it, what was
fixed, and what is still broken. Last updated 2026-10-16.

## How the checks work

Each compiled kernel is packetized by this branch's `atalla_cc -p`, encoded
without rescheduling by `functional_sim/build_compiler.py --prepacked`, run on
the functional simulator, and compared against a **golden** computed with numpy
from the same seeded inputs. Handwritten kernels are parsed by
`build_compiler.py --packetize` and call the same implementation in
`ppci/arch/atalla/packetizer.py`, with a single latency table in
`ppci/arch/atalla/latency.py`. Neither validation path uses the legacy simulator
scheduler. Unit validation also uses compiler `-p` and encoder `--prepacked`.

- `test_validation/*.c` (unit tests): each checks one feature; the expected
  result is in register `x10` (`EXPECT_X10` in the file header).
- `test_validation_kernels/*.c` (kernels): checked against numpy goldens in
  `run_kernel_validation.py`. Where a matching handwritten kernel exists in
  `functional_sim/kernels/`, it runs on the same memory image and is checked
  against the same golden, for a correctness and packet-count comparison.

Kernels with a known compiler bug are listed in `EXPECTED_FAILURES` in
`run_kernel_validation.py`. They are reported as `KNOWN BUG` and do not fail
the gate; any other failure does. When a fix makes a listed kernel pass, the
report shows `FIXED?`: remove it from `EXPECTED_FAILURES` so the gate protects
it from then on.

CI checks out the exact simulator commit recorded by this repository's
`functional_sim` gitlink, verifies the hash, and records it in the job summary.

## Summary

| Kernel | Compiled | Handwritten | Open issue |
|---|---|---|---|
| add | PASS | PASS | none |
| relu | PASS | PASS | none |
| conv_baseline | PASS | PASS | none |
| conv_pipelined | PASS | PASS | none |
| conv_pipelined_unrolled | PASS | PASS | none |
| gemm_tiled_baseline | PASS | PASS | none |
| gemm_tiled_pipelined | PASS | PASS | none |
| gemm_tiled_pipelined_unrolled | PASS | PASS | none |
| softmax | PASS | PASS | none |
| layernorm | PASS | PASS | none |
| maxpool | PASS | PASS | none in current kernel |
| maxpool_2x2 | PASS | PASS | none |
| All 12 unit tests | PASS | n/a | none |

## Open issues

### C. Packetizer model limitations

The simulator's legacy `schedule_program` remains more permissive than the
hardware, but neither side of the kernel comparison uses it now. Compiled
kernels arrive through `--prepacked`; handwritten kernels use the textual
assembly adapter selected by `--packetize`.

Both adapters now isolate control operations, retain every outstanding WAR
reader, and distinguish scalar, vector, and mask register files. Remaining
model limitations include unmapped instructions (which currently have no FU
restriction) and a deliberately conservative chain across all memory-touching
operations. Packet counts are now comparable between these two paths, but they
should not be presented as RTL-final throughput estimates.

### D. Handwritten comparison coverage

All 12 kernels have a handwritten comparison. `HANDWRITTEN_KERNELS` in
`run_kernel_validation.py` supplies each generator's shape and layout options.
The unrolled convolution uses `build_conv_unrolled_pipelined.py`; tiled GEMMs
use `build_gemm_tiled.py` with prefetch/unroll options; layernorm supplies its
32-column GMEM stride; and maxpool selects vertical or 2x2 pooling.

Generators emit unpacked assembly with `--emit-asm-only`. The harness applies
the shared packetizer once, seeds the same image as the compiled kernel, and
checks the same golden. Missing default pairings or failing handwritten
goldens fail validation.

## Fixed issues

| Issue | Kernels affected | Fix | Where |
|---|---|---|---|
| Reduction lowering encoded the float placeholder as a mode, writing the result only into lane 0. | softmax, layernorm, maxpool_2x2 | Emit broadcast mode 64 for RSUM/RMIN/RMAX; require a constant-zero placeholder. | compiler vector instruction selection |
| Masked assignments had no dependency on the previous destination; optimization removed earlier maxpool pair results. | maxpool, maxpool_2x2 | Optional fifth merge operand carried through AST, IR, and allocation; four-argument elementwise calls preserve the first vector operand. Initialize and track the destination as read/write. | compiler frontend, IR, vector lowering, kernel sources |
| Instruction selection matched only a prefix of a tree's operands, allowing a rule to discard merge dependencies. | masked vector operations | Require matching terminal arities; correct the REGVEC/REGMASK leaf patterns. | compiler tree matcher + Atalla patterns |
| Scalar peephole folding removed a live K-loop increment when the next instruction copied the incremented value into another register. Both pipelined GEMMs then repeated the same tile until timeout. | gemm_tiled_pipelined, gemm_tiled_pipelined_unrolled | Fold adjacent `addi.s` or `li.s` instructions only when both write the same register. Both kernels now pass their numerical goldens. | functional_sim `build_compiler.py` |
| Packetizer dependency keys used only `reg.num`, making `x1`, `v1`, and `m1` conflict, and WAR tracking retained only the latest reader. | all compiler-packetized code | Use typed register keys and retain all readers since the last definition; mirror the all-reader rule in the handwritten adapter. | compiler packetizer + functional_sim adapter |
| Handwritten kernels used the simulator's permissive scheduler, so their packet counts were not comparable to compiler output. | add, relu, softmax, conv_baseline, conv_pipelined | Add `--packetize`: parse unpacked assembly, use the shared compiler packetizer and compiler latency table, relocate labels after block reordering, and bypass simulator peepholes. All five handwritten goldens pass. | functional_sim + compiler validation harness |
| Compiled kernels were rescheduled by the simulator, producing optimistic and previously nondeterministic packet counts. | all compiled kernels | Compile with `-p`, encode with `--prepacked`, and preserve all-NOP stall rows. Two repeated full runs produced identical static packet counts. | compiler validation harness |
| Simulator packetizer ignored dependencies of mask compares (`mgt/mlt/meq/mneq` `.mvv/.mvs`): it checked for type names `MVV`/`MVS`, but the opcode table calls them `VMV`/`VMS`, so compares could move ahead of the instructions they depend on. | relu, make_mask_gt_scalar | Use the opcode table's type names. | functional_sim `75dba64` |
| Simulator vector spill (`vreg_ld`/`vreg_st` with sid 3) used the previous instruction's address before reading the current one, so a spill also overwrote whatever the last vector load touched. | load_weights_lane0_dot | Read the address before using it; error if a sid 3 access is outside the spill area. | functional_sim `75dba64` |
| The simulator changed `gemm.vv` to matmul only (`vd = vs1 @ W`) in April, but the compiler still relied on it adding the accumulator. | conv_baseline, conv_pipelined, conv_pipelined_unrolled, gemm_passthrough_lane0 | `gemm(a, acc, mask)` now emits `gemm_vv` followed by `add_vv`. | compiler `e2ba24ea` |
| gemm_tiled C kernels told SDMA the matrices were 4 wide (stride field 3) when they are 8 wide, so every tile after the first read the wrong data. | gemm_tiled_* | Stride field 7: control words `0x06300007` / `0x46300007`. | this change |
| gemm_tiled harness: `lw_vi` loads a scratchpad row as a *column* of the weight buffer, and the weight buffer kept appending columns across K tiles. | gemm_tiled_* | Seed W with each 4x4 tile transposed; set `FUNCTIONAL_SIM_GEMM_WEIGHT_TILE=4` so each K tile refills the buffer. | this change |
| Weak or missing checks hid wrong results: softmax only checked the sum, maxpool only checked for finite numbers, gemm_tiled only checked the three variants agreed, and layernorm allowed a 317% error on one element. | softmax, maxpool, maxpool_2x2, gemm_tiled_*, layernorm | numpy goldens for every kernel; layernorm tolerance set from a BF16-rounded reference. | this change |
| Duplicate copies of the kernel `.c` files in `test_validation/` failed the unit runner (no `EXPECT_X10`); stale `*_atalla.py` runners pointed at a nonexistent directory; the CI workflow pointed at a misspelled directory. | all | Removed the duplicates and stale runners; rewrote the workflow. | compiler `83ac7e21` and CI commits |

## Numbers from last semester's report

The Spring 2026 report's handwritten packet counts were produced by an older,
more permissive scheduler and are not directly comparable to the new
shared-packetizer results. Historical numbers should remain labeled with their
scheduler version. The report's claim that compiled layernorm is more accurate
than the handwritten one may reflect the historical memory-layout mismatch;
the current comparisons use matched layouts and goldens.
