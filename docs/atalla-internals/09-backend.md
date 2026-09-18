# 09 — Backend driver, ABI, frames, prologue/epilogue (`ppci/codegen/codegen.py`, `ppci/arch/atalla/arch.py`)

## 9.1 `CodeGenerator` construction (`codegen.py:41-60`)

`optimize_for="speed"` (from `ir_to_stream`'s default `opt="speed"`) → selection weights `(3, 10, 1)` for
(size, cycles, energy). Every Atalla pattern is declared with `size=N` and default `cycles=1, energy=1`,
so rule cost = `3*size + 10 + 1`. Costs only matter when two rules cover the same tree (ch. 10).

## 9.2 Module-level emission (`generate`, `:62-98`)

1. `select_section("data")`; for each external: `Global(name)` if global binding, `SetSymbolType(name,"func")`
   for external subroutines. This is why `.s` files start with `.section data` twice (a second
   `select_section("data")` precedes the globals loop).
2. `generate_global` (`:100-141`): `Alignment(var.alignment)`, `Global`, `Label(var.name)`, then
   `DByte` per byte for initialised data, or `DZero(amount)`; pointer initialisers become `Dcd2(label)`
   (4-byte little-endian → `absaddr32` relocation from `data_isa`). Verified in the `glob.c` trace:
   `g` → four `.byte`, `arr` → `.zero 16`.
3. `select_section("code")`, functions in module order.

## 9.3 Frame layout (verified from `gen_prologue`/`gen_epilogue`/`peephole` and the traces)

Registers: `x2` = SP, `x8` = FP, `x1` = LR, `x0` = zero (assumed), `x32` = scratchpad SP, `x33` = scratchpad FP.

Prologue (`arch.py:318-388`), with `ssize = round_up(stacksize + 8)`, `rsize = round_up(4*len(callee_saved)) = 16`
(callee_save is empty and `round_up(0) == 16`), `extras = max(out_calls)` if any:

```
.align 5                      ; Align(5) → section alignment 5, pads to a multiple of 5 bytes
<name>:
[main only] lui_s x32, 15625 ; 2000000 >> 7
            addi_s x32, x32, 0 ; 2000000 & 0x7F
            addi_s x33, x32, 0
addi_s x2, x2, -ssize
sw_s x1, 4(x2)
sw_s x8, 0(x2)
[scpad]  sw_s x33, 8(x2)
addi_s x8, x2, 8              ; FP = SP + 8  (FP points just above the saved pair)
addi_s x2, x2, -16            ; rsize: always 16 bytes for zero saved registers
[extras] addi_s x2, x2, -round_up(extras)
[scpad]  addi_s x33, x32, 0 ; scratchpad FP = scratchpad SP
         addi_s x32, x32, -scpad_stacksize
```

Stack picture after the prologue (addresses grow upward):

```
SP_old            ─┐
  locals (stacksize bytes, FP-relative, offsets fixed up by peephole)
  padding
SP_new+8  x33 save (only if scpad frame)       ← FP = SP_new+8
SP_new+4  LR
SP_new+0  FP_old                               ← SP after first adjust
  16 bytes never used (rsize)
  outgoing-arg area (round_up(extras)), only for calls with >6 scalar args
                                               ← SP during body
```

Local slot addressing: patterns emit `Addis/Lws/Sws(..., FP, offset)` with `offset < 0` and mark the
instruction `fprel = True`. `AtallaArch.peephole` (`:454-460`) adds `round_up(stacksize+8) - 8` so the
final address is `FP + offset + ssize - 8 = SP_new + ssize + offset = SP_old + offset`, i.e. the locals
live *below the old SP*. Incoming stack arguments (`gen_function_enter`, `Lws(arg, off, FP)` with
`fprel=True`) get the same fix-up → `SP_old + off`, matching where the caller stored them (`Sws(arg, off, SP)`
at the caller's post-prologue SP). Verified in the `manyargs.c` trace: callee reads `8(x8)`, `12(x8)`
with `ssize=16`: `FP+8 = SP_new+16 = SP_old+0`… i.e. offsets 0 and 4 above the old SP, exactly where
the caller wrote `sw_s x10, 0(x2)` / `sw_s x9, 4(x2)`.

Scratchpad frame (only when `frame.scpad_stacksize != 0`): vector slots at `x33 + offset`, `offset ∈
{-64, -128, …}` (`Frame.scpad_alloc`), `x32` lowered by the total; instructions are marked
`scpadfprel = True`/`spadrel` and **excluded** from the peephole fix-up (`:457`), so offsets are used verbatim.
`x33` is saved to `8(x2)` and restored in the epilogue; `x32` is restored from `x33`.

Epilogue (`:390-446`): reverse order, then `jalr x0, x1, 0`, then the literal pool (`litpool`: `Section("data")`,
`Align(4)` if constants, `dcd` per constant, `Section("code")`). With no constants the pool is just the
two section switches you see at the end of every `.s`.

## 9.4 Calling convention (`determine_arg_locations`, `:570-601`; `gen_call`, `:489-536`; `gen_function_enter/exit`, `:539-568`)

* Scalar/vector/mask arguments **all** take the next register from `[R12, R13, R14, R15, R16, R17]`;
  the function does not look at the type except `is_blob` (struct by value → `StackLocation`). A `vec`
  argument would therefore be assigned an `x` register and `move(x12, vecvreg)` would produce
  `AddVv(x12, …)`/`Addis(x12, vec)` → operand type assertion failure. This is the README's "cannot pass
  `vec` by value" limitation, and it is a crash, not a diagnostic. (Verified by reading; not executed.)
* 7th+ scalar arguments: `StackLocation(offset, 4)` at SP+0, +4, …; caller `sw_s` them, `frame.add_out_call`.
* Return value in `R10` (`determine_rv_location`). A `vec` return would try `move(R10, vecvreg)` → crash (Inferred).
* Caller side (`gen_call`): `move(argreg, argvreg)` per register arg, `RegisterUseDef(uses=argregs)`,
  `Jal(LR, label, clobbers=caller_save)`, then `RegisterUseDef(defs=(R10,))`, `move(rv_vreg, R10)`.
  `caller_save = (R10, R12..R17)` — **R9, R11, R18..R27 are neither callee- nor caller-saved**: the
  allocator assumes they survive a call (no interference with clobbers), but no callee saves them
  (`callee_save = ()`). Correctness currently relies on low register pressure keeping live values in
  `x9..x12` and callees being short. (Verified reasoning; latent bug.)
* Callee side (`gen_function_enter`): `RegisterUseDef(defs=argregs)`, `move(argvreg, R12..)` — these moves
  are what the `addi_s x11, x13, 0` lines at the top of `add_vec` are.
* `branch()` (`:261`): `Jalr(reg, lab, 0)` when the target is a register (indirect call), else `Jal(reg, lab)`.
* Blob args (`gen_call`, `:500-519`): copied with `gen_Atalla_memcpy` which issues **one `lw_s/sw_s` pair
  per byte** at byte offsets (`for idx in range(size): Lws(tmp, idx, src); Sws(tmp, idx, dst)`) — it
  copies overlapping 4-byte words; functionally copies the bytes but over-writes 3 bytes past the end.

## 9.5 `move` and the coalescing consequence (`:303-308`)

```python
def move(self, dst, src):
    if V0 in src.registers or V0 in dst.registers:   # src/dst are Register objects here, .registers is the class list
        return AddVv(dst, src, V0, M0)
    return Addis(dst, src, 0)
```

`src.registers` is the *class attribute* `AtallaVectorRegister.registers` (list of all `v` registers)
for vector registers and `AtallaRegister.registers` for scalars, so the test is effectively “is this a
vector register”. Neither instruction is created with `ismove=True`, so the register allocator never
sees a move (ch. 11). Mask registers hit the scalar branch: `Addis(m1, m2, 0)` would fail the operand
assert — but no code path moves masks (masks are never phi'd/arguments) (Inferred).

## 9.6 Peephole (`:448-487`)

1. `fprel` fix-up as described (skips `scpadfprel` and `VregLd/VregSt`).
2. Delete `Addis rd, rs, 0` where `rd` and `rs` colour to the same physical register.
3. Delete `AddVv vd, vs1, v0, m0` where `vd` and `vs1` colour to the same register.
4. Also prunes `frame.buckets_by_block` (never set → no-op).

This is the *only* copy elimination in the compiler. It catches identity moves that the allocator
happened to colour equal (e.g. `x12 → x12` for the third argument of `add_vec` in `sample.s`).

## 9.7 `emit_frame_to_stream` (`codegen.py:242-306`)

Asserts `all(r.is_colored for r in instruction.registers)` for every real instruction → any vreg left
uncoloured is an assertion, not a silent bug. `RegisterUseDef` is dropped; `ArtificialInstruction`
(`Align`, `Section`) emitted for later rendering; `InlineAssembly` assembled now.
