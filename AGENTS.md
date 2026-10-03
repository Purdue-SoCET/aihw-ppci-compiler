# Codex task checkpoint (2026-10-03)

This note is for Codex when continuing work on the Atalla compiler. Verify the
working tree and test results before relying on this checkpoint.

## Current state

The three scalar intrinsics `atalla_const_u32`, `atalla_load_u32`, and
`atalla_load_bf16_word` have been replaced with ordinary C constants and typed
volatile pointer loads in all 12 validation kernels. The compiler's parser,
semantics, AST, and code generator no longer implement those intrinsics.
`atalla_halt` remains an intrinsic. These changes are uncommitted as of this
checkpoint; verify the working tree before continuing.

The replacement was first tested in `/tmp/atalla-c-scalar-ZDUzL3`, then
applied to the branch. With `PYTHONHASHSEED=0`, 12/12 unit tests and the full
kernel accuracy gate passed. All 12 kernel statuses and error strings matched
the pre-change intrinsic run: eight pass, three expected fail, one existing
unexpected pass. Dynamic scalar-memory counts matched for every kernel.
Executed packet counts matched for 11 kernels; `gemm_tiled_pipelined` used
1,082 packets with C versus 1,092 in the intrinsic baseline. Compilation of an
unchanged GEMM source from a different path also produced different assembly,
consistent with the known nondeterminism in GEMM code generation. Do not claim
byte-for-byte identity for all GEMM assembly. Nine kernels did produce identical
assembly in a matched source comparison. BF16 typed C loads and intrinsic
BF16 loads emitted identical assembly in `layernorm`.

## What was achieved

- The 12 validation kernels were converted from 100 inline-asm calls to the four
  scalar intrinsics. On the current branch, eight compiled kernels pass, three
  retain known expected failures, and one is an existing unexpected pass.
- A separate, still uncommitted compiler change keeps scalar `=r` inline-asm
  outputs in virtual registers and fixes inline-asm register replacement during
  actual spills. It touches `ppci/ir.py`, `ppci/lang/atalla_c/codegenerator.py`,
  `ppci/codegen/irdag.py`, and `ppci/arch/generic_instructions.py`. No kernel or
  simulator source was changed for this experiment.
- Original inline-asm kernels tested in a temporary tree with that compiler fix
  matched the intrinsic kernels' accuracy statuses. With `PYTHONHASHSEED=0`,
  intrinsic versus fixed inline-asm versions used 3,407 versus 3,489 packets
  and 97 versus 218 dynamic scalar-memory operations across 12 separate runs.
  GEMM accounted for most of the memory difference; small kernels sometimes
  used a few fewer packets with inline asm. Packet counts are simulator
  estimates, not hardware cycle measurements.
- The scalar intrinsic comparison has now been done and the three unnecessary
  intrinsics removed. The performance gain over original inline asm does not
  establish that those intrinsic names were required.

The previous inline-asm experiment temp directory may have been deleted.
Kernel status and known bugs are documented in
`test_validation_kernels/KERNEL_STATUS.md`.
