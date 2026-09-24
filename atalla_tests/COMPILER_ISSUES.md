# Compiler Issues: Fixes Applied and Questions

All test files compile from the repo root:
```
./atalla_cc atalla_tests/<file>.c -S -o atalla_tests/<file>.s
```

Full pipeline (compile + assemble + emulator):
```
python3 compile_test.py atalla_tests/<file>.c
```

---

## Branch History

This branch (`atalla_arch_emul_robert`) is based on `atalla-arch-emul` with `atalla-arch` merged in, plus our fixes on top.

- `atalla-arch-emul` provides: `compile_test.py`, `emulator/build_compiler.py`, full emulator
- `atalla-arch` provides: latest compiler backend (ISA compliance, mask-creation, vreg ld/st rework, br encoding, rs1_rd1 fix)
- Our fixes on top: ty=VEC, halt/nop opcodes, sac operand (see below)

`build_compiler.py` handles the notation conversion between compiler output (`add_s`, `x5`, `m2`) and emulator input (`add.s`, `$5`, `2`), so a separate `asm_converter.py` is not needed when using `compile_test.py`.

---

## Fixes Applied (still carried on this branch)

These three fixes are NOT in the latest `atalla-arch` and are applied here.

### 1. Vector Register Spill Pattern Match: Missing `ty = "VEC"`

**File:** `ppci/arch/atalla/vector_registers.py`

`AtallaVectorRegister` had no `ty` attribute, so `MiniGen.make_fmt()` built tree names like `STRI512`/`LDRI512`. The backend patterns are `STRVEC`/`LDRVEC`, so spills never matched.

Note: the compiler team fixed the vreg_ld/st instruction encoding (Lis + rs2 + num_cols=31) in commit `1efb1797`, but without `ty = "VEC"` the pattern still can't fire.

**Fix:** Added `ty = "VEC"` to `AtallaVectorRegister`.

### 2. `halt`/`nop` Opcode Mismatch

**File:** `ppci/arch/atalla/instructions.py`

Compiler used `halt=0b1111111` and `nop=0x00000000`. The ISA spec and emulator expect `halt=0b0110000` (`halt.s`, opcode 48) and `nop=0b0101111` (`nop.s`, opcode 47).

**Fix:** Updated opcodes to match ISA spec.

### 3. Missing `sac` Operand on VV Instructions

**Files:** `ppci/arch/atalla/tokens.py`, `ppci/arch/atalla/vector_instructions.py`, `ppci/arch/atalla/arch.py`

The VV bit format (ISA spec bits 35-39) includes a `sac` (shift-accumulate control) field. The compiler's `AtallaVVToken` had no bit field for it, `make_vv` defined only 4 operands, and all emit sites passed 4 args.

**Fix:**
- Added `sac = bit_range(35, 40)` to `AtallaVVToken`
- Added `sac` operand to `make_vv`
- All VV emit sites now pass `sac=0` (including `arch.py` vector move)

Verified: `gemm_vv v1, v2, v1, m1, 0` in output.

---

## Fixes Now Upstream (in `atalla-arch`, came via merge)

These were issues we identified and fixed on `robert`; the compiler team has since fixed them independently on `atalla-arch`.

### 4. `rs1_rd1` Read-Write Hazard on `scpad_ld`/`scpad_st`

The SDMA first operand is both read and auto-incremented by hardware. Was marked `read=True` only. Now `read=True, write=True` on `atalla-arch`.

### 5. Branch Relocation / Encoding

`BranchBase.relocations()` referenced `self.imm12` but the BR-type format uses `imm10`. The compiler team added a custom `encode()` method and cleaned up the operand definitions.

### 6. `vreg_ld`/`vreg_st` Instruction Rework

The `make_vm` signature changed from 7 positional ints to `(vd, rs1, rs2, num_cols, sid)`. Spill patterns now use `Lis(c, 1)` to load a register value for the rs2 operand and set `num_cols=31`.

---

## Build Pipeline Updates

We updated `emulator/build_compiler.py` and `emulator/build_softmax.py` to handle the new instruction formats from the latest compiler:

- **VM type**: now parses `vd, rs1, rs2, num_cols, sid` (5 operands with rs2 as register) in addition to the old 7-int format
- **SDMA type**: now parses `rs1_rd1, rs2, rs3` (3 register operands) in addition to the old 5-operand format with ints
- **Encoding**: `encode_instruction` updated for new VM bit layout (`rs2` at bits 23-30, `num_cols` at bits 31-35, `sid` at bits 36-37) and new SDMA layout (`rs3` at bits 23-30)
- **`rcp.bf`**: Added to opcode table (replaces `div.bf` at opcode `0b0010001`) and emulator execution

---

## Observations / Questions for Compiler Team

### A. Mask Register Flow

The intended design is for masks to flow through ints: `make_mask()` produces a mask reg internally, assigning to `int` auto-inserts `mv_mts`, and passing an `int` to masked ops auto-inserts `mv_stm`. Users never declare `mask` typed variables.

**Question:** Is this the intended and final design?

### B. Register Coloring for Vec Regs

Even with spills fixed, the allocator only ever colors v1 and v2. The `vector_register_class` includes v1-v31, but the graph coloring doesn't use more than 2. This causes excessive spilling in any kernel with more than 2 live vec variables.

### C. Data Section in `.in` Files

Compiling from C produces `.in` files with instruction hex but an empty data section. To run kernels with actual tensor data, `DRAMWriter` integration is needed (as used in the `atalla-graph` pipeline's `c_emitter.py`). This is a known gap -- the C-only path doesn't populate data.

---

## Pipeline Test Results

All kernels tested with `python3 compile_test.py atalla_tests/<file>.c --no-verify`:

| File | .c -> .s | .s -> .in | Emulator | Notes |
|------|----------|-----------|----------|-------|
| `sample.c` | pass | pass | pass | |
| `spill_test.c` | pass | pass | pass | Spills use num_cols=31 |
| `relu.c` | pass | pass | pass | |
| `softmax.c` | pass | pass | runtime err | rcp.bf on empty data produces inf |
| `gemm_tiled.c` | pass | pass | pass | gemm_vv with sac=0 |
| `hazard_test.c` | pass | pass | pass | |
| `conv_sa_pipelined.c` | pass | pass | pass | |

Pre-existing failures in `vv_instr.c`, `vs_instr.c`, `vi_instr.c`, `masktest.c`, `intrinsictest.c`, `instructtest.c`, `instructtest2.c`, `bftest.c` (all due to `int mask` keyword conflict) are unchanged.
