```
./atalla_cc atalla_tests/<file>.c -S -o atalla_tests/<file>.s
```

---

## 1. Vector Register Spill: Only 1/32 Elements Saved

**File:** `atalla_tests/spill_test.c`

This is a basic ReLU kernel that needs 4 vec variables live at the same time (input, zero, positive mask result, output). The kernel loads a vector from scratchpad, creates a zero vector, compares to build a mask, then does a masked multiply.

```c
vec v_data;
asm("vreg_ld %0, %1, 31, 0, 0, 0, 0" : "=v"(v_data) : "r"(addr));

vec v_zero = vec_op_masked("+", v_data, 0.0, full_mask);
v_zero = vec_op_masked("*", v_zero, 0.0, full_mask);

int pos_mask = make_mask(">", v_data, v_zero, full_mask);
vec v_result = vec_op_masked("*", v_data, 1.0, pos_mask);
```

**Run:**
```
./atalla_cc atalla_tests/spill_test.c -S -o atalla_tests/spill_test.s
```

**Output (`spill_test.s` lines 14-25):**
```asm
       vreg_ld v1, x9, 31, 0, 0, 0, 0   ; user load, num_cols=31, all 32 elements (correct)
       addi_s x9, x33, -64
       vreg_st v1, x9, 0, 0, 0, 0, 0    ; SPILL: num_cols=0, only 1 element saved
       addi_s x9, x33, -64
       vreg_ld v1, x9, 0, 0, 0, 0, 0    ; RELOAD: num_cols=0, only 1 element restored
       addi_vi v4, v1, 0, m0             ; v4 has 31 garbage elements out of 32
       addi_s x9, x33, -64
       vreg_ld v1, x9, 0, 0, 0, 0, 0    ; same reload, same problem
       addi_vi v3, v1, 0, m0
       addi_s x9, x33, -64
       vreg_ld v1, x9, 0, 0, 0, 0, 0    ; same reload, same problem
       addi_vi v2, v1, 0, m0
```

Notice only v1 and v2 ever show up in the output. The register allocator doesn't color beyond 2 vec regs even though 8+ are available, so it spills everything through a single scratchpad slot.

**Where the bug is:**

Two spots in the backend:

1. **`ppci/codegen/registerallocator.py`, `MiniGen.make_fmt()` (~line 181):**
   ```python
   def make_fmt(self, vreg):
       ty = getattr(vreg, "ty", "I")   # defaults to "I"
       fmt = f"{ty}{vreg.bitsize}"      # produces "I512"
       return fmt
   ```
   This builds spill tree names like `STRI512` / `LDRI512` / `MOVI512`. But the Atalla backend only defines patterns for `STRVEC` / `LDRVEC` / `MOVVEC`, so the tree names don't match what the instruction selector knows about.

2. **`ppci/arch/atalla/vector_instructions.py`, spill patterns (lines 317-329):**
   ```python
   @isa.pattern("stm", "STRVEC(mem, vecreg)", size=2)
   def pattern_store_vecreg(context, tree, c0, v1):
       Code = VregSt(v1, c0[0], 0, 0, 0, 0, 0)   # num_cols=0, stores 1 element
       ...
   @isa.pattern("vecreg", "LDRVEC(mem)", size=2)
   def pattern_load_vecreg(context, tree, c0):
       ...
       Code = VregLd(d, c0[0], 0, 0, 0, 0, 0)     # num_cols=0, loads 1 element
   ```
   Even when the correct pattern does match, the dimensions are wrong. `num_cols=0` means transfer 1 element. Should be 31 for all 32 columns.

**Proposed fix (4 lines total):**

In `ppci/arch/atalla/vector_registers.py`, add `ty = "VEC"` so `MiniGen` generates the right tree names:
```python
class AtallaVectorRegister(Register):
    bitsize = 32 * 16
    ty = "VEC"           # makes MiniGen produce STRVEC/LDRVEC/MOVVEC instead of STRI512
```

In `ppci/arch/atalla/vector_instructions.py` lines 317-329, change `num_cols` from 0 to 31:
```python
@isa.pattern("stm", "STRVEC(mem, vecreg)", size=2)
def pattern_store_vecreg(context, tree, c0, v1):
    Code = VregSt(v1, c0[0], 31, 0, 0, 0, 0)   # 31 = all 32 columns
    Code.fprel = True
    context.emit(Code)

@isa.pattern("vecreg", "LDRVEC(mem)", size=2)
def pattern_load_vecreg(context, tree, c0):
    d = context.new_reg(AtallaVectorRegister)
    Code = VregLd(d, c0[0], 31, 0, 0, 0, 0)    # 31 = all 32 columns
    Code.fprel = True
    context.emit(Code)
    return d
```

---

## 2. `gemm_vv` Operand Count (sac field)

**File:** `atalla_tests/gemm_test.c`

Wanted to check whether the compiler emits the 5th operand (sac) that the functional sim expects.

**Run:**
```
./atalla_cc atalla_tests/gemm_test.c -S -o atalla_tests/gemm_test.s
```

**Output (`gemm_test.s` line 29):**
```asm
       gemm_vv v1, v2, v1, m1, 0       ; 5 operands, sac=0 is present
```

This is fine. The compiler does emit all 5 operands. The pattern in `vector_instructions.py` line 415 hardcodes `sac=0` which is correct for standard GEMM. If we ever need non-zero sac the pattern would need to be parameterized, but this is not blocking anything right now.

---

## 3. `mv_stm`: Mask Register Allocation from C

**File:** `atalla_tests/mask_test.c`

**Run:**
```
./atalla_cc atalla_tests/mask_test.c -S -o atalla_tests/mask_test.s
```

**Output (`mask_test.s` lines 13-14):**
```asm
       li_s x9, 65535
       mv_stm m1, x9        ; hardcoded m1 literal in the asm string, works fine
```

**What works:** Hardcoding a specific mask register name in the asm template string:
```c
asm("mv_stm m1, %0" : : "r"(mask_val));   // works
```

**What doesn't work:** Letting the compiler pick which mask register to use via a constraint:
```c
asm("mv_stm %0, %1" : "=m"(some_mask) : "r"(val));   // "=m" means memory, not mask
```

There's no constraint letter (like `"=k"` or `"=M"`) for mask registers. The compiler can't allocate or track them. In practice this means:

- `make_mask()` always goes through m0
- If you need two masks live at the same time, you have to hardcode the register names yourself in inline asm
- The compiler can't properly spill/reload mask values if it runs out

**Proposed fix:** Add a mask register constraint (e.g. `"k"`) in `ppci/lang/atalla_c/semantics.py` (the `on_asm` handler around line 647) and in `ppci/codegen/irdag.py` (`_constraint_to_ir_type`), mapping it to `AtallaMaskRegister`.

---

## 4. `rs1_rd1` Read-Write Hazard on `scpad_ld`/`scpad_st`

**File:** `atalla_tests/hazard_test.c`

**Run:**
```
./atalla_cc atalla_tests/hazard_test.c -S -o atalla_tests/hazard_test.s
```

**Output (`hazard_test.s` lines 13-20):**
```asm
       li_s x9, 256
       addi_s x10, x9, 0
       li_s x9, 4096
       scpad_ld x10, x9, 31, 3, 0    ; x10 is rs1_rd1: read as address, then WRITTEN by hw
       li_s x9, 384
       addi_s x10, x9, 0             ; compiler happens to reload x10 here, so this case is safe
       li_s x9, 4096
       scpad_ld x10, x9, 31, 3, 0
```

This particular test case doesn't blow up because the compiler reloads x10 from a constant anyway. But the actual problem is that the register allocator has no idea x10 got clobbered by `scpad_ld`. Under higher register pressure or with different optimization decisions, it could keep the stale value and produce silently wrong DMA addresses.

**Where the bug is:**

`ppci/arch/atalla/vector_instructions.py` line 616, inside `make_sdma`:
```python
def make_sdma(mnemonic: str, opcode: int):
    rs1_rd1 = Operand("rs1_rd1", AtallaRegister, read=True)
    #                                              only read=True, missing write=True
```

The hardware auto-increments `rs1_rd1` after the DMA transfer completes, but the compiler models it as read-only. This means the register allocator treats it as still holding the original value and won't insert a reload or avoid reusing it.

**Proposed fix (1 line):**

```python
    rs1_rd1 = Operand("rs1_rd1", AtallaRegister, read=True, write=True)
```

This marks the operand as clobbered so the allocator knows the original value is gone after a `scpad_ld` or `scpad_st`.
