# Compiler Issues: Fixes Applied and Questions

All test files compile from the repo root:
```
./atalla_cc atalla_tests/<file>.c -S -o atalla_tests/<file>.s
```

---

## Fixes Applied

### 1. Vector Register Spill: Only 1/32 Elements Saved

**File:** `atalla_tests/spill_test.c`

Basic ReLU kernel that needs 4 vec variables live at the same time. When the register allocator spills a vec reg, only 1 out of 32 elements was being saved/restored.

**Before:**
```asm
       vreg_st v1, x9, 0, 0, 0, 0, 0    ; num_cols=0, only 1 element saved
       vreg_ld v1, x9, 0, 0, 0, 0, 0    ; num_cols=0, only 1 element restored
```

**Root cause (two parts):**

1. `AtallaVectorRegister` had no `ty` attribute, so `MiniGen.make_fmt()` defaulted to `"I"` and built tree names like `STRI512`. The backend only defines patterns for `STRVEC`/`LDRVEC`, so the spill pattern never matched properly.

2. Even when matched, the spill patterns in `vector_instructions.py` used `num_cols=0` (1 element) instead of `num_cols=31` (all 32).

**Fix:**
- Added `ty = "VEC"` to `AtallaVectorRegister` in `ppci/arch/atalla/vector_registers.py`
- Changed `num_cols` from 0 to 31 in `pattern_store_vecreg` and `pattern_load_vecreg` in `ppci/arch/atalla/vector_instructions.py`

**After:**
```asm
       vreg_st v1, x9, 31, 0, 0, 0, 0   ; all 32 elements saved
       vreg_ld v1, x9, 31, 0, 0, 0, 0   ; all 32 elements restored
```

Verified on `conv_sa_pipelined.c` as well; all spill sites now transfer the full vector.

**Remaining limitation:** Regalloc still only colors 2 vec regs (v1, v2) and spills everything else. The spills are correct now, but using more of v1-v31 would reduce spill overhead.

---

### 2. `halt`/`nop` Opcode Mismatch

The compiler used `halt=0b1111111` and `nop=0x00000000`. The functional simulator expects `halt=0b0110000` and `nop=0b0101111` per the ISA spec (`halt.s`, `nop.s` are R-Int type).

**Fix:** Updated opcodes in `ppci/arch/atalla/instructions.py`.

---

### 3. Missing `sac` Operand on VV Instructions

The VV format (bit-spec shows bits 35-39 beyond the mask field) includes a `sac` (shift-accumulate control) field. The compiler's `AtallaVVToken` had no bit field for it, `make_vv` defined only 4 operands, and all emit sites (`add_vv`, `sub_vv`, `mul_vv`, `gemm_vv`) passed 4 args.

**Fix:**
- Added `sac = bit_range(35, 40)` to `AtallaVVToken` in `ppci/arch/atalla/tokens.py`
- Added `sac` operand to `make_vv` syntax/patterns in `ppci/arch/atalla/vector_instructions.py`
- All VV emit sites now pass `sac=0`

Verified: `gemm_vv v1, v2, v1, m1, 0` in output.

---

### 4. `rs1_rd1` Read-Write Hazard on `scpad_ld`/`scpad_st`

**File:** `atalla_tests/hazard_test.c`

The ISA bit-spec labels the SDMA first operand as "rs1 and rd1", meaning the hardware reads it as a scratchpad address and then writes it back (auto-increment). The compiler's `make_sdma` only marked it `read=True`, so the register allocator didn't know the value was clobbered.

**Fix:** Changed to `Operand("rs1_rd1", AtallaRegister, read=True, write=True)` in `ppci/arch/atalla/vector_instructions.py`.

Simple test cases happened to be safe (compiler reloads from constants), but this prevents silent corruption under register pressure.

---

### 5. Branch Relocation Field Name

`BranchBase.relocations()` referenced `self.imm12` but the BR-type format uses `imm9`+`imm1`, not `imm12`. The actual field on the instruction object is `imm10`.

**Fix:** Changed `self.imm12` to `self.imm10` in `ppci/arch/atalla/instructions.py`.

---

## Observations / Questions for Compiler Team

These are things we noticed while working with the handoff. We haven't changed anything for these; want to confirm whether they're intentional or need attention.

### A. Mask Register Flow

The handoff has `MOVMASK` commented out and no inline asm constraint for mask registers. We initially thought this was a gap and added `"=m"`/`"m"` constraints, `STRMASK`/`LDRMASK` spill patterns, `mask` type keyword, etc.

After looking at `sample.c`, it seems the intended design is for masks to flow through ints:
- `make_mask()` produces a mask reg internally
- Assigning to `int` auto-inserts `MASKTOI32` (emits `mv_mts`)
- Passing an `int` to `vec_op_masked()`/`gemm()` auto-inserts `MVSTMMASK` (emits `mv_stm`)

So users never declare `mask` typed variables or need mask asm constraints. We reverted our additions.

**Question:** Is this the intended and final design? If so, is there a reason `MOVMASK` was left as commented-out code rather than removed? Are there any planned use cases where explicit `mask` typed variables or mask register constraints would be needed?

### B. Constraint Propagation in Inline Asm

The handoff's `irdag.py` uses an `amount==64` heuristic to detect vec types in inline asm operands (`AddressOf.src.amount` or `GlobalValue.amount`). This works but doesn't generalize. The constraint string (`"=v"`, `"r"`, etc.) is parsed in semantics but then discarded in codegen -- `codegenerator.py` calls `add_input_variable(value)` without passing the constraint.

We had refactored this to propagate constraints through IR and use them in `irdag.py` for type routing, but reverted it since the heuristic works for the current use cases.

**Question:** Is constraint propagation something you'd want in the future (e.g. for new register classes), or is the `amount==64` heuristic sufficient for the planned ISA?

### C. `MOVMASK` Implementation

If `MOVMASK` is ever needed, there's no direct mask-to-mask move in the ISA. It would need to route through a scalar temp: `mv_mts tmp, src_mask` then `mv_stm dst_mask, tmp` (size=3 pattern). Same approach for spill/reload of mask regs (via `sw_s`/`lw_s` through a scalar temp). We had this working but reverted it. The code is in git history (commit `6674a42c`) if needed.

### D. Register Coloring for Vec Regs

Even with spills fixed, the allocator only ever colors v1 and v2. The `vector_register_class` includes v1-v31, but the graph coloring doesn't use more than 2. This causes excessive spilling in any kernel with more than 2 live vec variables. Not sure if this is a known limitation of ppci's graph coloring or a configuration issue.

---

## Regression Check

After applying fixes 1-5, recompiled all test files:

| File | Result |
|------|--------|
| `spill_test.c` | compiles, spills use num_cols=31 |
| `lwvi_test.c` | compiles, spills use num_cols=31 |
| `mask_test.c` | compiles, hardcoded m1 works |
| `hazard_test.c` | compiles, rs1_rd1 marked read+write |
| `conv_sa_pipelined.c` | compiles, all spills correct, gemm_vv has sac |
| `sample.c` | compiles, all intrinsics work |

Pre-existing failures in `vv_instr.c`, `vs_instr.c`, `vi_instr.c`, `masktest.c`, `intrinsictest.c`, `instructtest.c`, `instructtest2.c`, `bftest.c` (all due to `int mask` keyword conflict) are unchanged.
