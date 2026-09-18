# 21 — End-to-end traces (all outputs real, produced 2026-09-18 with `./atalla_cc -O2`)

Reading key for the “trees” lines: `MOVI32[vreg]` = store into a vreg; `REGI32[vreg]` = read a vreg;
`CONSTI32[n]` = constant; a tree's children are in parentheses. `[emit]` lines are printed by
`InstructionContext.emit`.

## 21.1 Integer arithmetic, control flow, constants — `atalla_tests/forloop.c`

```c
int main(){ int a = 5; for(int i = 0; i < 10; i++){ a += i; } return a; }
```

**IR after `optimize` (`-O2`)** — allocas for `a` and `i` promoted to phis; blocks renumbered by `CleanPass`:
```
main_block0: { i32 num_15 = 5; i32 num_1_17 = 0; jmp main_block2; }
main_block2: { i32 phi_alloca_13_0 = phi main_block0: num_1_17, main_block3: tmp_10_20;
               i32 phi_alloca_0 = phi main_block0: num_15, main_block3: tmp_7;
               i32 num_4 = 10; cjmp phi_alloca_13_0 < num_4 ? main_block3 : main_block4; }
main_block3: { i32 tmp_7 = phi_alloca_0 + phi_alloca_13_0; i32 num_9_19 = 1;
               i32 tmp_10_20 = phi_alloca_13_0 + num_9_19; jmp main_block2; }
main_block4: { return phi_alloca_0; }
```

**Selection trees** (`DagSplitter` output; note the two-step phi copies and that constants are not vreg'd):
```
main_block0:
MOVI32[vreg3](CONSTI32[0])                       ; tmp copy of phi input
MOVI32[vreg4](CONSTI32[5])
MOVI32[vreg0phi_alloca_13_0](REGI32[vreg3])      ; i ← tmp
MOVI32[vreg1phi_alloca_0](REGI32[vreg4])         ; a ← tmp
JMP[main_block2:]
main_block2:
MOVI32[vreg0phi_alloca_13_0](REGI32[vreg0phi_alloca_13_0])   ; phi self-copies (successor main_block3's phis
MOVI32[vreg1phi_alloca_0](REGI32[vreg1phi_alloca_0])         ;  are the same vregs) → identity moves
CJMPI32[('<', main_block3:, main_block4:)](REGI32[vreg0phi_alloca_13_0], CONSTI32[10])
main_block3:
MOVI32[vreg5](ADDI32(REGI32[vreg0phi_alloca_13_0], CONSTI32[1]))
MOVI32[vreg6](ADDI32(REGI32[vreg1phi_alloca_0], REGI32[vreg0phi_alloca_13_0]))
MOVI32[vreg0phi_alloca_13_0](REGI32[vreg5])
MOVI32[vreg1phi_alloca_0](REGI32[vreg6])
JMP[main_block2:]
main_block4:
MOVI32[vreg2retval](REGI32[vreg1phi_alloca_0])
JMP[main_epilog:]
```

**Selected instructions with virtual registers** (`[emit]` lines, in order):
```
li_s vreg7, 0 ; addi_s vreg3, vreg7, 0            ← CONSTI32 rule then MOVI32 rule (arch.move)
li_s vreg8, 5 ; addi_s vreg4, vreg8, 0
addi_s vreg0phi_alloca_13_0, vreg3, 0
addi_s vreg1phi_alloca_0, vreg4, 0
jal x0, main_block2
addi_s vreg0…, vreg0…, 0 ; addi_s vreg1…, vreg1…, 0   ← identity moves (deleted by peephole)
li_s vreg9, 10 ; blt_s vreg0…, vreg9, main_block3 ; jal x0, main_block4
addi_s vreg10, vreg0…, 1 ; addi_s vreg5, vreg10, 0   ← ADDI32(reg, CONSTI32) then the MOV
add_s vreg11, vreg1…, vreg0… ; addi_s vreg6, vreg11, 0
addi_s vreg0…, vreg5, 0 ; addi_s vreg1…, vreg6, 0
jal x0, main_block2
addi_s vreg2retval, vreg1…, 0 ; jal x0, main_epilog
(then gen_function_exit) addi_s x10, vreg2retval, 0 ; VUseDef(x10)
```

**After register allocation + peephole + prologue/epilogue** (`forloop.s`), with the colouring
`vreg0→x12, vreg1→x11, vreg2→x9, vreg3→x10, vreg4→x11?…` (read from the output):
```
       .align 5
 main:
       lui_s x32, 15625        ; scpad SP/FP init (main only)
       addi_s x32, x32, 0
       addi_s x33, x32, 0
       addi_s x2, x2, -16      ; round_up(0+8) = 16
       sw_s x1, 4(x2)
       sw_s x8, 0(x2)
       addi_s x8, x2, 8
       addi_s x2, x2, -16      ; round_up(0) = 16 bytes for zero callee-saved registers
 main_block0:
       li_s x9, 0
       addi_s x10, x9, 0
       li_s x9, 5
       addi_s x12, x10, 0      ; i
       addi_s x11, x9, 0       ; a
       jal x0, main_block2
 main_block2:                  ; identity moves removed here
       li_s x9, 10
       blt_s x12, x9, main_block3
       jal x0, main_block4
 main_block3:
       addi_s x9, x12, 1
       addi_s x10, x9, 0
       add_s x9, x11, x12
       addi_s x12, x10, 0
       addi_s x11, x9, 0
       jal x0, main_block2
 main_block4:
       addi_s x9, x11, 0
       jal x0, main_epilog
 main_epilog:
       addi_s x10, x9, 0       ; return value → x10
       addi_s x2, x2, 16
       lw_s x1, 4(x2)
       lw_s x8, 0(x2)
       addi_s x2, x2, 16
       jalr x0,x1, 0
```
Loop body: 2 useful instructions (`addi_s`, `add_s`), 3 copies, 1 jump. The copies exist because
coalescing is disabled (ch. 11).

**Object file** (`forloop.o`, JSON): section `code` = 155 bytes (31 × 5), `alignment 0x5`; symbols
`main@0x0 (global,func)`, `main_block0@0x28`, `main_block2@0x46`, `main_block3@0x55`, `main_block4@0x73`,
`main_epilog@0x7d` (local, object); relocations `MI_jal_i25@0x41→sym2`, `BR_i10@0x4b→sym3`,
`MI_jal_i25@0x50→sym4`, `MI_jal_i25@0x6e→sym2`, `MI_jal_i25@0x78→sym5`. All immediates in the data are 0.

**Link** (`atalla_layout.mmap`): `code.address = 0x1004`. Relocation `BR_i10@0x4b`: `sym = 0x1004+0x55`,
`reloc = 0x1004+0x4b`, `calc = (0x55-0x4b)//5 = 2` → bytes at 0x4b become `25 00 86 84 00`.
`MI_jal_i25@0x6e→main_block2`: `(0x46-0x6e)//5 = -8` → `2D 00 FC FF FF`.

**ELF / disassembly** (file offsets; code at file offset 0x37):
```
0x0082    25 00 86 84 00   blt_s x12, x9, 0x8C  # offset=2
0x0087    2D 80 03 00 00   jal   x0, 0xAA       # offset=7
0x00A5    2D 00 FC FF FF   jal   x0, 0x7D       # offset=-8
0x00CD    2E 80 00 00 00   jalr  x0, x1, 0
```

## 21.2 Load/store through pointers and frame slots — `ptrload.c`

```c
int main(){ int x[3]; int *p = x; p[1] = 4; return p[1] + x[2]; }
```
IR (excerpt): `blob<12:4> alloca = alloc 12 bytes aligned at 4; ptr alloca_addr = &alloca;
… ptr tmp_4_30 = typecast_25 + tmp_3_29; store num_5_31, tmp_4_30; … load tmp_17_38`.
The array stays in memory (`Alloc` used as an address, not promotable). Trees: `STRI32(ADDU32(FPRELU32[..],
MULU32(CONSTU32[1], CONSTU32[4])), CONSTI32[4])`-style; the selector picks `FPRELU32 → reg`
(`addi_s x10, x8, 12` after fix-up: slot offset −12 + (round_up(12+8)−8 = 24) = 12), `MULU32(reg, CONSTU32)`
→ `li_s x9, 1; muli_s x9, x9, 4` (constant-folding does **not** fold `1*4` because `casted_28 = 1` is a
`ptr`-typed cast result, not an `i32` const in the same type — verified in the IR), `ADDU32(reg,reg)` →
`add_s`, `STRI32(reg, reg)` → `sw_s x9, 0(x10)`, `LDRI32(reg)` → `lw_s x9, 0(x9)`:
```
       addi_s x2, x2, -32      ; round_up(12+8) = 32
       …
       addi_s x10, x8, 12
       li_s x9, 1
       muli_s x9, x9, 4
       add_s x10, x10, x9
       li_s x9, 4
       sw_s x9, 0(x10)
       addi_s x10, x8, 12
       li_s x9, 2
       muli_s x9, x9, 4
       add_s x9, x10, x9
       lw_s x9, 0(x9)
       addi_s x9, x9, 4        ; num_5_31 (4) + load, as ADDI32(reg, CONSTI32) after CSE reused the const
```

## 21.3 Function call / return, stack arguments — `manyargs.c` and `sample.c`

`int f(int a,…,int h){ return a+h; } int main(){ return f(1,…,8); }`

Caller (main): `li_s x9,1; addi_s x12,x9,0; … li_s x9,6; addi_s x11,x9,0; li_s x9,7; addi_s x10,x9,0;
li_s x9,8; addi_s x17,x11,0; sw_s x10, 0(x2); sw_s x9, 4(x2); jal x1, f; addi_s x9, x10, 0`.
Args 1–6 → `x12..x17` (via temporaries because each `MOV` is a separate tree), args 7–8 → `SP+0`, `SP+4`;
the prologue reserved `round_up(8) = 16` extra bytes (`addi_s x2, x2, -16` twice) and the epilogue
releases them. Return value read from `x10`.

Callee (f): `addi_s x10, x12, 0` (a), five dead copies of `x13..x17` into `x9` (each parameter gets a move
even if unused — `DeleteUnusedInstructions` ran on the IR, but the moves are created later by
`gen_function_enter`), `lw_s x9, 8(x8)` (g), `lw_s x9, 12(x8)` (h: offset 4 + fix-up 8), `add_s x9, x10, x9`.

`sample.c` additionally shows a call with pointer arguments to scratchpad locals
(`addi_s x9, x33, -192; addi_s x11, x9, 0; … addi_s x12, x11, 0; addi_s x13, x10, 0; addi_s x14, x9, 0;
jal x1, add_vec`) and a call to `give_5` whose result is converted with `stbf_s x9, x10, x0` and used by
`sub_vs v1, v1, x9, m0` (`v4 -= give_5()`).

## 21.4 Vector operations and Atalla intrinsics — `atalla_tests/vv_instr.c`

IR: ch. 07 §5. Trees:
```
MOVVEC[vreg2tmp_vload_72](VLOADVEC(CONSTI32[43981], CONSTI32[1], CONSTI32[31], CONSTI32[1]))
MOVVEC[vreg3tmp_vload_11_74](VLOADVEC(CONSTI32[57005], CONSTI32[1], CONSTI32[31], CONSTI32[1]))
MOVVEC[vreg4tmp_24_78](MULVEC(SUBVEC(ADDVEC(REGVEC[vreg2…], REGVEC[vreg3…]), REGVEC[vreg3…]), REGVEC[vreg3…]))
VSTORE(GEMMVEC(REGVEC[vreg4…], REGVEC[vreg4…], MVSTMMASK[vreg1](CONSTI32[5])), CONSTI32[43690], CONSTI32[1], CONSTI32[31], CONSTI32[1])
MOVI32[vreg0retval](CONSTI32[0])
JMP[main_epilog:]
```
Note: `VLOAD` is chained, so its result is vreg'd and wrapped in `MOVVEC`; the three arithmetic ops are
single-use and fused into one tree; `gemm` is single-use and fused into `VSTORE`; the `int` mask 5 became
`MVSTMMASK(CONSTI32)`.

Assembly (body):
```
       li_s x10, 43981 ; li_s x9, 1
       vreg_ld v1, x10, x9, 31, 1
       add_vv v3, v1, v0, m0          ; MOVVEC → arch.move (vector) — an uncoalesced copy
       li_s x10, 57005 ; li_s x9, 1
       vreg_ld v1, x10, x9, 31, 1
       add_vv v2, v1, v0, m0
       add_vv v1, v3, v2, m0          ; ADDVEC(vecreg, vecreg) matched the 3-child rule; mask defaulted to M0
       sub_vv v1, v1, v2, m0
       mul_vv v1, v1, v2, m0
       li_s x9, 5
       mv_stm m1, x9                  ; MVSTMMASK(reg)
       gemm_vv v1, v1, v1, m1
       li_s x10, 43690 ; li_s x9, 1
       vreg_st v1, x10, x9, 31, 1
       li_s x9, 0
       jal x0, main_epilog
```
Encodings for these instructions are in ch. 15 §3.

## 21.5 Constants / immediates — from `sample.c`

* `int mask = 0xFFFA0001` → `CONSTU32 ≥ 2²⁵` → `lui_s x9, 33551360 ; addi_s x9, x9, 1` (33551360 = 0xFFFA0001 >> 7).
* `3.6` → `CONSTBF16` → `li_s x9, 16486` (0x4066).
* `return 0x4000000;` → **crash** `RuntimeError: Tree MOVI32[vreg0retval](CONSTI32[67108864]) not covered`
  (no `CONSTI32` rule for signed values ≥ 2²⁵).

## 21.6 Atalla-specific: scratchpad locals, `scpad_ld`, `EXP`, `v[5]` — `sample.c` `main`

```
 main:
       lui_s x32, 15625 ; addi_s x32, x32, 0 ; addi_s x33, x32, 0
       addi_s x2, x2, -16 ; sw_s x1, 4(x2) ; sw_s x8, 0(x2)
       sw_s x33, 8(x2)                 ; scpad FP saved because scpad_stacksize != 0
       addi_s x8, x2, 8 ; addi_s x2, x2, -16
       addi_s x33, x32, 0
       addi_s x32, x32, -192           ; three 64-byte vector slots: v1 @-64, v2 @-128, v_add @-192
 main_block0:
       li_s x11, 43690 ; li_s x10, 48059 ; li_s x9, 2730
       scpad_ld x11, x10, x9           ; scpad_load(a, b, 0b0101010101010)
       li_s x11, 43690 ; li_s x10, 48059 ; li_s x9, 10922
       scpad_st x11, x10, x9
       li_s x10, 43981 ; li_s x9, 1
       vreg_ld v1, x10, x9, 31, 1      ; vector_load(vec_addr1, 1, 31, 1)
       addi_s x10, x33, -64 ; li_s x9, 1
       vreg_st v1, x10, x9, 31, 3      ; store to scratchpad local v1 (STRVEC(mem)) — sid 3, cols 31, rs2 = 1
       …
       jal x1, add_vec
       … (reload v1, v2, v_add, v1 again — one vreg_ld + add_vv copy each)
       jal x1, give_5
       add_vv v1, v5, v4, m0 ; add_vv v2, v1, v2, m0     ; v3 = v1 + v2 + v_add
       li_s x9, 16486 ; mul_vs v1, v3, x9, m0            ; v4 = v1 * 3.6
       stbf_s x9, x10, x0 ; sub_vs v1, v1, x9, m0        ; v4 -= give_5()
       lui_s x9, 33551360 ; addi_s x9, x9, 1 ; mv_stm m1, x9
       expi_vi v1, v1, 0, m1                              ; vec_op_masked("EXP", v4, 0.0, 0xFFFA0001)
       li_s x9, 10 ; mv_stm m1, x9
       gemm_vv v1, v2, v1, m1                             ; gemm(v3, v4, 10)
       li_s x10, 43981 ; li_s x9, 1
       vreg_st v1, x10, x9, 31, 1                         ; vector_store(v4, vec_addr1, 1, 31, 1)
       vmov_vts x9, v1, 5 ; bfts_s x9, x9, x0             ; (int)v4[5]
       jal x0, main_epilog
 main_epilog:
       addi_s x10, x9, 0
       addi_s x32, x33, 0              ; drop scratchpad frame
       addi_s x2, x2, 16
       lw_s x33, 8(x2) ; lw_s x1, 4(x2) ; lw_s x8, 0(x2)
       addi_s x2, x2, 16
       jalr x0,x1, 0
```
Note `v4` (`v1` register) is live across `jal x1, give_5` — vector registers are in no save set at all,
so this is correct only if `give_5` does not touch `v1` (it does not). The `make_mask("<", v1, v2, 0)`
result `m` is unused and was deleted by `DeleteUnusedInstructionsPass` (no `mlt_mvv` in the output).

## 21.7 bf16 — `bftest.c`

`float a = 5.0; float b = 6.7; float c = a / b; float d = sqrt(c); inc_float(&d); return d;`
```
       li_s x10, 16544            ; 5.0  = 0x40A0
       li_s x9, 16598             ; 6.7  = 0x40D6
       rcp_bf x9, x9, x0
       mul_bf x9, x9, x10         ; c = rcp(b) * a
       sqrt_bf x9, x9, x0
       sw_s x9, 6(x8)             ; d lives in memory (address taken): 2-byte slot at FP-2 → 6 after fix-up,
                                  ;   but stored with a 4-byte sw_s (no 16-bit store exists)
       addi_s x9, x8, 6 ; addi_s x12, x9, 0
       jal x1, inc_float
       lw_s x9, 6(x8)
       bfts_s x9, x9, x0          ; (int)d
```

## 21.8 Globals — `glob.c` (demonstrates the bug in ch. 14.5)

```c
int g = 7; int arr[4]; int main(){ g = g + 1; arr[2] = g; return g; }
```
```
       lui_s x9, g ; addi_s x9, x9, g ; lw_s x9, 0(x9)   ; ← "address of g" pattern, already loads g
       lw_s x9, 0(x9)                                    ; ← the real load: loads from address 7
       addi_s x9, x9, 1 ; addi_s x11, x9, 0
       lui_s x9, g ; addi_s x9, x9, g ; lw_s x9, 0(x9)
       sw_s x11, 0(x9)                                   ; stores to address 7
       lui_s x10, arr ; addi_s x10, x10, arr ; lw_s x10, 0(x10)   ; arr base = *arr = 0
       li_s x9, 2 ; muli_s x9, x9, 4 ; add_s x9, x10, x9
       sw_s x11, 0(x9)                                   ; stores to address 8
```
Object: `g@0x0`, `arr@0x4` in `data`; relocations `MI_abs_i25`/`abs_imm7` pairs at 0x28/0x2d, 0x46/0x4b,
0x5a/0x5f, 0x7d/0x82. After link `lui_s x9, 4096` (= 0x80000 >> 7) — the address arithmetic is right,
the extra load is the bug.

## 21.9 Spills — `vec_pressure.c`, `int_pressure.c`

Vector: `Spilling round 1`, ten vregs `Placing {vregN…} on stack`, `Allocating stack slot SCPAD[64 bytes at -64]`
… `-640`; prologue `addi_s x32, x32, -640`; each spill is `addi_s x10, x33, -N ; li_s x9, 1 ; vreg_st v1, x10, x9, 31, 3`
right after the defining `vreg_ld`, and the mirror `vreg_ld` before each use.
Scalar: `NORMAL[4 bytes at -4]` … ; `sw_s x9, 124(x8)` / `lw_s x9, 124(x8)` pairs (offsets after fix-up).
