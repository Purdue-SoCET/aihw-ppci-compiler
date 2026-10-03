# Kernel validation status

Status of every test run by the `compiler_validation` CI workflow
(`.github/workflows/compiler_validation.yml`), what was wrong with it, what was
fixed, and what is still broken. Last updated 2026-09-29.

## How the checks work

Each kernel is compiled with this branch's `atalla_cc`, packetized and encoded by
`functional_sim/build_compiler.py`, run on the functional simulator, and its
output memory is compared against a **golden**: the expected result computed
with numpy from the same seeded inputs.

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

CI runs the simulator from the tip of the branch named in `.gitmodules`
(currently `vecreg-spill-seth`) and records the simulator commit in the job
summary.

## Summary

| Kernel | Compiled | Handwritten | Open issue |
|---|---|---|---|
| add | PASS | PASS | none |
| relu | PASS | PASS | none |
| conv_baseline | PASS | PASS | none |
| conv_pipelined | PASS | PASS | none |
| conv_pipelined_unrolled | PASS | not paired | no handwritten equivalent |
| gemm_tiled_baseline | PASS | not paired | handwritten pairing (see E) |
| gemm_tiled_pipelined | PASS | not paired | none |
| gemm_tiled_pipelined_unrolled | PASS | not paired | none |
| softmax | PASS | PASS | none |
| layernorm | PASS | not paired | none |
| maxpool | PASS | not paired | none |
| maxpool_2x2 | KNOWN BUG | not paired | B (masked-op merge) |
| All 12 unit tests | PASS | n/a | none |

## Open issues

### A. Reductions only write lane 0 (softmax, layernorm, maxpool_2x2)

**Symptom.** softmax outputs are up to 64% off (they still sum to 1, which is
why the old "sums to about 1" check passed). layernorm is off by 0.22 on
outputs up to 2.2.

**Cause.** `rsum_vi` / `rmax_vi` / `rmin_vi` take an 8-bit mode immediate. In
the simulator (`apply_imm_vector_op` in `functional_sim/src/functional_sim.py`),
bit 6 (value 64) broadcasts the result to every lane; mode 0 writes the result to
lane 0 and leaves the other lanes holding the input. Every kernel assumes
broadcast. The compiler builds the immediate from the intrinsic's float argument
(`vec_op_masked("RSUM", v, 0.0, mask)`) by converting it to BF16 bits, so `0.0`
becomes mode 0, and no float value can produce 64.

**Where.** `patt_rsum_vi`, `patt_rmin_vi`, `patt_rmax_vi` in
`ppci/arch/atalla/vector_instructions.py`.

**Verified fix.** Rewriting the emitted reductions to mode 64 makes softmax pass
its golden and brings layernorm to 0.0156 max error (the bound for a correct
BF16 implementation is 0.016; the golden allows 0.03). The fix is to emit mode 64
for these patterns, and decide what, if anything, the float argument should mean
for reductions.

### B. Masked ops don't preserve the destination's old lanes (maxpool, maxpool_2x2)

**Symptom.** maxpool output is off by up to 1.04: lanes where the second row is
not larger come out as the second row instead of the first.

**Cause.** The kernels rely on
`best = vec_op_masked("+", zero_vec, v1, mask)` leaving `best` unchanged in lanes
where the mask is 0. The compiler treats the result as a new value and picks a
fresh register (in maxpool it reuses the register holding `v1`), so the unmasked
lanes hold whatever was in that register. The README only gives the intrinsic's
signature; the behavior for unmasked lanes is not defined anywhere.

**Needed.** A language decision: either define that `x = vec_op_masked(...)`
merges into `x`'s previous value (the compiler must then use `x`'s register as
the destination), or define unmasked lanes as coming from the first operand and
rewrite these kernels accordingly.

### C. The simulator's packetizer is too permissive (affects efficiency numbers)

`schedule_program` in `functional_sim/build_compiler.py` allows up to four scalar
ALU ops in one packet and has no functional-unit model, which the hardware does
not support. Correctness results are unaffected, but packet counts and slot
utilization for both compiled and handwritten kernels are optimistic. Planned fix:
make its algorithm match Shaunak's packetizer (branch `atalla-shaunak`) after that
packetizer's own bugs are fixed:

- `halt` is not treated as control and gets hoisted to the top of its block.
- WAR tracking only remembers the most recent reader of a register.
- Registers are keyed by number only, so `x1`, `v1` and `m1` create false
  dependencies.

`build_compiler.py --prepacked` already exists to encode compiler-made packets
as-is once the compiler owns packetization.

### D. Compiled output varies between runs

Packet counts for the gemm_tiled kernels differ slightly from run to run
(for example 1,252 vs 1,244 for gemm_tiled_pipelined) with identical inputs.
Harmless for the accuracy gate, but it must be made deterministic before gating
on efficiency.

### E. Kernels without a handwritten comparison

| Kernel | Why not paired |
|---|---|
| layernorm | `build_layernorm_param.py` expects an N-wide tile in memory; the C kernel uses a 4x32 tile. Passing the right stride was not enough (output still skewed). |
| gemm_tiled_* | `build_gemm_tiled.py --tile 4` writes nothing to C on this memory image. |
| maxpool, maxpool_2x2 | `build_maxpool.py` has no `--emit-asm-only` mode. |
| conv_pipelined_unrolled, gemm_tiled_pipelined_unrolled | no matching generator. |

## Fixed issues

| Issue | Kernels affected | Fix | Where |
|---|---|---|---|
| Scalar peephole folding removed a live K-loop increment when the next instruction copied the incremented value into another register. Both pipelined GEMMs then repeated the same tile until timeout. | gemm_tiled_pipelined, gemm_tiled_pipelined_unrolled | Fold adjacent `addi.s` or `li.s` instructions only when both write the same register. Both kernels now pass their numerical goldens. | functional_sim `build_compiler.py` |
| Simulator packetizer ignored dependencies of mask compares (`mgt/mlt/meq/mneq` `.mvv/.mvs`): it checked for type names `MVV`/`MVS`, but the opcode table calls them `VMV`/`VMS`, so compares could move ahead of the instructions they depend on. | relu, make_mask_gt_scalar | Use the opcode table's type names. | functional_sim `75dba64` |
| Simulator vector spill (`vreg_ld`/`vreg_st` with sid 3) used the previous instruction's address before reading the current one, so a spill also overwrote whatever the last vector load touched. | load_weights_lane0_dot | Read the address before using it; error if a sid 3 access is outside the spill area. | functional_sim `75dba64` |
| The simulator changed `gemm.vv` to matmul only (`vd = vs1 @ W`) in April, but the compiler still relied on it adding the accumulator. | conv_baseline, conv_pipelined, conv_pipelined_unrolled, gemm_passthrough_lane0 | `gemm(a, acc, mask)` now emits `gemm_vv` followed by `add_vv`. | compiler `e2ba24ea` |
| gemm_tiled C kernels told SDMA the matrices were 4 wide (stride field 3) when they are 8 wide, so every tile after the first read the wrong data. | gemm_tiled_* | Stride field 7: control words `0x06300007` / `0x46300007`. | this change |
| gemm_tiled harness: `lw_vi` loads a scratchpad row as a *column* of the weight buffer, and the weight buffer kept appending columns across K tiles. | gemm_tiled_* | Seed W with each 4x4 tile transposed; set `FUNCTIONAL_SIM_GEMM_WEIGHT_TILE=4` so each K tile refills the buffer. | this change |
| Weak or missing checks hid wrong results: softmax only checked the sum, maxpool only checked for finite numbers, gemm_tiled only checked the three variants agreed, and layernorm allowed a 317% error on one element. | softmax, maxpool, maxpool_2x2, gemm_tiled_*, layernorm | numpy goldens for every kernel; layernorm tolerance set from a BF16-rounded reference. | this change |
| Duplicate copies of the kernel `.c` files in `test_validation/` failed the unit runner (no `EXPECT_X10`); stale `*_atalla.py` runners pointed at a nonexistent directory; the CI workflow pointed at a misspelled directory. | all | Removed the duplicates and stale runners; rewrote the workflow. | compiler `83ac7e21` and CI commits |

## Numbers from last semester's report

The Spring 2026 report's handwritten packet counts cannot be reproduced with the
current tools. Handwritten relu dropped from 32 to 28 packets with the mask
dependency bug above put back, and then produced wrong output, so the report's
relu numbers came from a mis-scheduled program. Handwritten softmax has been 27
packets at every simulator commit since the April 19 refactor; the report's 22
predates it. The report's claim that compiled layernorm is more accurate than the
handwritten one is likely the same memory-layout mismatch described in E.
