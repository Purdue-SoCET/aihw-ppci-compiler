# Encoder Reconciliation: build_compiler vs compile_and_convert

## Summary

The two `.s`-to-`.in` encoding paths produce **identical instruction encodings** for
all shared instruction types. They diverge only on **SDMA (scratchpad) instructions**
due to different operand formats.

## Paths Compared

| Path | Entry | SDMA format |
|------|-------|-------------|
| **build_compiler** (`functional_sim/build_compiler.py` + `_asm_encoding.py`) | `compile_asm(s_text)` | 3-register: `scpad.ld rs1, rs2, rs3` |
| **compile_and_convert** (`atalla_tests/compile_and_convert.py` using `asm_converter` + `build.py`) | `assemble_to_in(emu_asm)` | 5-operand: `scpad.ld rs1, rs2, num_cols, num_rows, sid` |

## Findings

1. **Instruction encoding is identical** for scalar, vector, memory, branch, and control
   instructions — both encoders share the same opcode table and bit-packing logic.

2. **SDMA divergence**: The ppci compiler emits `scpad_ld x11, x10, x9` (3-register form
   where the config is packed in a register). `build.py`'s assembler expects the explicit
   5-operand form with immediate num_cols/num_rows/sid. `asm_converter` converts to
   `scpad.ld $11, $10, $9` which `build.py` rejects (`parse_int('$9')` fails).

3. **`build_compiler.py` is the only working encoder for compiler-generated `.s`** because
   it handles both the 3-register SDMA and performs VLIW scheduling/packetization.

4. **The team's `build.py` assembler** works for hand-written assembly using the explicit
   5-operand SDMA form.

## Conclusion

**`build_compiler.py` is the canonical encoder** for the compiler pipeline path.
`compile_and_convert.py` should be updated to use `build_compiler.compile_asm()` instead of
`asm_converter` + `build.assemble_file()`, or noted as incompatible with compiler SDMA output.
No further unification is needed — instruction encoding is already consistent.
