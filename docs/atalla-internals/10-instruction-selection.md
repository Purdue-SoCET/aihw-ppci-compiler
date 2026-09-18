# 10 — Instruction selection

Three sub-stages: (a) IR → selection DAG, (b) DAG → forest of trees, (c) BURS tree matching with the
`@isa.pattern` rules. All three run inside `InstructionSelector1.select` (`ppci/codegen/instructionselector.py:370-487`).

## 10.1 IR → DAG (`ppci/codegen/irdag.py`)

`prepare_function_info` (`:24-67`) pre-allocates: a `Label` per block, `Label(name+"_epilog")`, a vreg per
`Phi` (`twain=phi.name`, giving names like `vreg0phi_alloca_13_0`), argument vregs (or `StackLocation`s)
via `arch.determine_arg_locations`, and `rv_vreg` (`twain="retval"`).

`SelectionGraphBuilder.build` (`:140-188`): `LABEL` nodes for every module variable/function/external
(`value = name`), an `ENTRY` control token, argument nodes (`REG` with `output.vreg = vreg`, or `FPREL`
for stack args), then blocks in `depth_first_order` (BFS from entry, `:83-93`).

Per block (`block_to_sgraph`, `:190-222`): `ENTRY` node → for each IR instruction dispatch `f_map[type]`;
**before the terminator**, `copy_phis_of_successors` (`:729-764`) emits, for every phi in every successor,
`MOV(tmp) ← value` then `MOV(phi_vreg) ← REG(tmp)` (two moves, to break phi cycles). Then `EXIT`.

Handler behaviour that determines what the backend sees:

| IR | DAG (op + type suffix) | chained? | payload |
|----|------|----|----|
| `Binop` | `ADD/SUB/MUL/DIV/REM/OR/SHL/AND/SHR/XOR` + ty (`VEC` for vectors) | no | |
| `Unop` | `NEG`/`INV` | no | |
| `Cast` | skipped when same-size integer & same reg class; else `<FROM>TO` + to-ty, e.g. `I32TOVEC`, `BF16TOI32` | no | |
| `Const` | `CONST<ty>` | no, `wants_vreg=False` | value |
| `Load` | `LDR<ty>(addr)` | **yes** | |
| `Store` | `STR<ty>(addr, val)` or `MOVB` for blobs | yes | |
| `Alloc` | `FPREL<ptr>` (normal) / `SCPADREL<ptr>` (**if `amount == 64`**) | no, `wants_vreg=False` | `StackLocation` |
| `AddressOf` | aliases the alloc's value | | |
| `GlobalValue` address | `LABEL<ptr>` | no | name |
| `CJump` | `CJMP<ty>(a,b)` | yes | `(cond, yes_label, no_label)` |
| `Jump` | `JMP` | yes | `Label` |
| `Return` | `MOV<ty>(val)` into `rv_vreg` + `JMP` epilog | yes | |
| `FunctionCall` | per arg `MOV<ty>` into fresh vreg; `CALL` (`(target, [(ty, vreg)], (ty, ret_vreg))`); `REG<ty>` for the result | yes | |
| `Phi` | `REG<ty>` with the phi vreg | no | |
| `Gemm` | `GEMMVEC(a, b, mask)` | no | |
| `VecOpMasked` | `<OP>VEC(a, b, mask)` with OP from the table at `:268-285` | no | |
| `MakeMask` | `M{EQ,NEQ,LT,GT}MASK(a, b, mask)` | no | |
| `VecIndex` | `VECIDX<ty>(base, index)` (`ty = bf16`) | no | |
| `LoadWeights` | `LOADWEIGHTS(v)` | yes | |
| `ScpadLoad/Store` | `SCPADLD/SCPADST(x,y,z)` | yes | |
| `VectorLoad` | `VLOADVEC(addr, arg2, arg3, arg4)` | yes | |
| `VectorStore` | `VSTORE(vec, addr, arg2, arg3, arg4)` | yes | |
| `SqrtBf` | `SQRTBF16(a)` | no | |
| `InlineAsm` | `MOV`s for inputs, `ASM`, `REG`+`STR` per output | yes | template tuple |

Mask operands: `prepare_mask` (`:224-233`) wraps any non-`mask`-typed mask value in `MVSTM<mask>(v)`
(`wants_vreg=False`) — this is the scalar→mask register transfer. The `value=mask_loc` vreg attached to
that node is never used by the pattern (which allocates its own).

`new_node` (`:364-376`) rewrites `ir.ptr` to `arch.info.type_infos["ptr"]` = `u32`, so pointer ops appear
as `…U32`.

## 10.2 DAG → trees (`ppci/codegen/dagsplit.py`)

`check_vreg` (`:65-78`): a DATA output gets a fresh vreg (`frame.new_reg(cls, name)`) if it has >1 user,
or its node is `volatile` (chained), or a user is in another block — unless `wants_vreg` is False.
Consequences: every `LDR`, `VLOAD`, `CALL` result and every multiply-used arithmetic result becomes a
`MOV<ty>[vreg](tree)` root followed by `REG<ty>[vreg]` leaves in later trees.

`make_trees` (`:86-134`): nodes are ordered by `topological_sort_modified` (`:148-189`: DFS from the block's
tail node honouring control → memory → data inputs; the tail is forced last). For each node a `Tree` is
built recursively from `data_inputs`; single-use, non-volatile producers are inlined into their consumer's
tree (this is what makes `MULVEC(SUBVEC(ADDVEC(…)))` one tree in ch. 21). Only trees that are volatile
or have a vreg'd output become roots; pure trees with an unused result are dropped.

Output of the splitter (per block): `[Label(block)] + roots`, then a final `Label(epilog)`.

## 10.3 Tree matching (`InstructionSelector1`, `TreeSelector`, `BurgSystem`)

Rule table built once per `CodeGenerator` (`instructionselector.py:297-325`): terminals = every
`op+type` combination from the `ops` list × `data_types` (`VEC, BF16, F32, F64, I64, I32, I16, I8, U64,
U32, U16, U8, MASK, PTR`) plus specials and `<op>VEC{I32,BF16}` (`:127-141`); rules: `stm ← CALL`,
`stm ← ASM`, `<class> ← UND<TY>` per register class, then every `arch.isa.pattern` as
`add_rule(non_term, tree, cost, condition, method)`.

Non-terminals in use: `stm`, `reg` (scalar), `vecreg`, `maskreg`, `mem` (address operand `(base_reg, offset)`).

`TreeSelector.gen` (`:196-204`): `burm_label` bottom-up dynamic programming — for each node, for each
rule whose root terminal matches structurally (`tree_terminal_equal`), whose `condition(tree)` holds
and whose kids already have the required non-terminal labels, record `cost = sum(kid costs) + rule.cost`
in `tree.state` (keeping the minimum per non-terminal), then propagate through chain rules
(`mark_tree`, `:235-243`; e.g. `mem ← reg` at `instructions.py:781`). If the root has no `stm` label →
`RuntimeError("Tree … not covered")`. `apply_rules` (`:245-259`) then walks top-down, calling each rule's
function with `(context, tree, *kid_results)`; `context.tree` is set during the call so
`InstructionContext.emit` can record `node_to_insts` (dead) and **print `[emit] mapped …`**.

Kid results are whatever the child rule returned: a `Register` for `reg/vecreg/maskreg`, a tuple
`(base_reg, offset)` for `mem`, `None` for `stm`.

## 10.4 Representative selections (all verified in ch. 21 output)

| IR op | Tree | Rule (file:line) | Emitted |
|-------|------|------------------|---------|
| `a + b` (i32) | `ADDI32(reg, reg)` | `instructions.py:625-630` | `add_s d, a, b` |
| `a + 1` | `ADDI32(reg, CONSTI32)` cond `< 4096` | `:649-665` | `addi_s d, a, 1` (the constant is read from `tree.children[1].value`, no `li_s`) |
| `a * b` | `MULI32(reg, reg)` | `:1164-1172` | `mul_s` |
| `2 * 4` (ptr math) | `MULU32(reg, CONSTU32)` | `:1181-1191` | `li_s; muli_s` |
| `load [FP-4]` | `LDRI32(mem)` with `mem ← FPRELU32` (kind NORMAL) | `:881-892`, `:743-751` | `lw_s d, off(x8)` with `fprel` |
| `load [reg]` | `LDRI32(mem)` via chain `mem ← reg` (`:781`) | | `lw_s d, 0(reg)` (`fprel=True` is set here too — harmless because the peephole only adjusts `imm12`, and `0 + fix` … **see caveat below**) |
| `store` | `STRI32(mem, reg)` | `:786-795` | `sw_s val, off(base)` |
| `cjmp a < b` | `CJMPI32(reg, reg)` | `:594-603` | `blt_s a, b, yes` ; `jal x0, no` |
| `jmp` | `JMP` | `:445-449` | `jal x0, label` |
| call | `CALL` (built-in rule) → `arch.gen_call` | `instructionselector.py:356` | moves into `x12..`, `jal x1, f`, move from `x10` |
| return | `MOVI32[retval](…)` + `JMP[epilog]`, then `gen_function_exit` → `addi_s x10, retval, 0` | | |
| const 5 | `CONSTI32` | `:553-577` | `li_s d, 5` (`li_s` has a 25-bit immediate) |
| const ≥ 2²⁵ unsigned | `CONSTU32` cond `≥ 2**25` | `:545-551` | `lui_s d, c>>7 ; addi_s d, d, c&0x7F` |
| const ≥ 2²⁵ **signed** | — | no rule | **compiler crash** (`Tree MOVI32[…](CONSTI32[67108864]) not covered`) |
| `3.6` (float) | `CONSTBF16` | `:582-592` | `li_s d, 0x4066` (top 16 bits of the IEEE-754 single = bfloat16, `_f32_to_f16_bits`) |
| `int → float` | `I32TOBF16(reg)` | `:1490-1495` | `stbf_s d, a, x0` |
| `int → vec` (from `coerce`) | `I32TOVEC(reg)` | same rule (`:1490`) | `stbf_s d, a, x0` — result stays **scalar**, then `SUBVEC(vecreg, reg)` → `sub_vs` |
| `float → int` | `BF16TOI32(reg)` | `:1484-1488` | `bfts_s` |
| `v1 + v2` | `ADDVEC(vecreg, vecreg, maskreg)` … but plain `Binop` produces `ADDVEC(a, b)` with **two** children | `vector_instructions.py:362-366` | see caveat: the rule tree has 3 children; `tree_terminal_equal` zips children (`burg.py:212-215`), so a 2-child tree matches a 3-child template and `mask` takes its Python default `M0` → `add_vv d, a, b, m0` |
| `vec_op_masked("+", a, b, m)` | `ADDVEC(vecreg, vecreg, MVSTMMASK(reg))` | `:362`, `:218-222` | `mv_stm m, x ; add_vv d, a, b, m` |
| `v * 3.6` | `MULVEC(vecreg, reg)` (the `CONSTBF16` is reduced to `reg` first) | `:564-568` | `li_s x, 0x4066 ; mul_vs d, v, x, m0` |
| `gemm(a,b,m)` | `GEMMVEC(vecreg, vecreg, maskreg)` | `:406-410` | `gemm_vv` |
| `make_mask("<", a, b, m)` | `MLTMASK(vecreg, vecreg, maskreg)` | `:224-228` | `mlt_mvv md, a, b, m` (result is a `maskreg`; `int m = …` then needs `MASKTOI32` → `mv_mts`) |
| `vector_load(a, r, 31, 1)` | `VLOADVEC(reg, reg, CONSTI32, CONSTI32)` cond `cols in 0..31, sid in 0..3` | `:637-645` | `vreg_ld d, a, r, 31, 1` |
| `vector_store` | `VSTORE(vecreg, reg, reg, CONSTI32, CONSTI32)` | `:681-686` | `vreg_st` |
| vec load from scratchpad slot | `LDRVEC(mem)` with `mem ← FPRELU32` kind SCPAD (`instructions.py:770-778`) | `:305-323` | `addi_s t, x33, off ; li_s c, 1 ; vreg_ld d, t, c, 31, 3` |
| vec store to slot | `STRVEC(mem, vecreg)` | `:287-303` | `addi_s ; li_s c,1 ; vreg_st v, t, c, 31, 3` |
| `v[5]` | `VECIDXBF16(vecreg, CONSTI32)` | `:616-620` | `vmov_vts d, v, 5` |
| `load_weights(v)` | `LOADWEIGHTS(vecreg)` | `:622-625` | `lw_vi v0, v, 0, m0` |
| `scpad_load(x,y,z)` | `SCPADLD(reg,reg,reg)` | `:627-630` | `scpad_ld x, y, z` |
| `&g` / `load g` | `LABEL` | `instructions.py:718-725` | `lui_s d, g ; addi_s d, d, g ; lw_s d, 0(d)` — **returns the loaded word, not the address** (bug, ch. 14) |
| `-a` | `NEGI32(reg)` | `:908-914` | `sub_s a, x0, a` (in place) |
| `~a` | `INVI32(reg)` | `:917-923` | `xori_s a, a, -1` |
| `a / b` (bf16) | `DIVBF16(reg,reg)` | `:1468-1474` | `rcp_bf d, b, x0 ; mul_bf d, d, a` |
| `sqrt(x)` | `SQRTBF16(reg)` | `:1461-1465` | `sqrt_bf d, x, x0` |
| `a < b` (bf16) in a condition | `CJMPBF16(reg,reg)` | `:1498-1513` | `call float16_lt` via `call_internal2` → **undefined symbol at link** |
| `x++` on i8/i16 | `I8TOI32` etc. | `:490-529` | `slli_s/srai_s` pairs, **in place on the input register** (mutates `c0`) |

Caveats discovered while tracing:

* **Rule arity mismatch.** `tree_terminal_equal` only compares as many children as both trees have
  (`zip`), and `get_kids` likewise. Hence `ADDVEC(vecreg, vecreg, maskreg)` matches a 2-child `ADDVEC`
  tree and the pattern function receives 2 kid results; `mask` falls back to the default argument `M0`.
  This is how unmasked vector arithmetic gets `m0`. It also means a 3-child `ADDVEC` from
  `vec_op_masked` could in principle match a 2-child template; there is none, so no ambiguity today.
* **`fprel` on non-frame loads is avoided by cost, not by design.** `pattern_ldr32_fprel` (`:886-892`)
  sets `fprel=True` whenever the `mem` non-terminal was used, and `mem ← reg` (`:781-783`, cost 10) makes
  any register a legal `mem` with offset 0. If that path were chosen for a plain pointer dereference,
  the peephole would add `ssize-8` to the offset. It is not chosen because the direct rules
  `LDRI32(reg)` (`:895-905`) and `STRI32(reg, reg)` (`:798-806`) cost 2 versus 2+10. Verified in
  `glob.s`/`ptrload.s`: pointer loads are `lw_s x9, 0(x9)`. For vectors there is no `LDRVEC(reg)` rule,
  so `*vp` goes through `mem ← reg`; that is safe only because `VregLd/VregSt` carry no `imm12`, are
  explicitly exempted by the peephole (`arch.py:458`), and the extra `Addis` is emitted only when
  `offset != 0` (`vector_instructions.py:291`). Verified in `sample.s` (`add_vec`): `vreg_ld v1, x11, x9, 31, 3`.
* `pattern_ldr32_fprel` and `pattern_ldr32_reg` are declared twice for `LDRI32(reg)` (`:895` and `:940`);
  the second registration wins ties only by order, both emit the same code.
* Sign/zero extension rules (`:490-529`) modify the source register in place; if the source vreg is
  still live elsewhere the value is corrupted. (Verified by reading; upstream RISC-V has the same shape.)

## 10.5 Spill code selection

`MiniGen` (`registerallocator.py:147-196`) reuses the same `TreeSelector` with a `MiniCtx`:
`MOV<fmt>[vreg](LDR<fmt>(FPRELU32[slot]))` and `STR<fmt>(FPRELU32[slot], REG<fmt>[vreg])`, where
`fmt = "VEC"` for `AtallaVectorRegister` (`make_fmt`, `:183-191`) else `"I"+bitsize` → `I32`.
For vectors the slot is `SCPAD` kind → the `LDRVEC/STRVEC(mem)` rules with `x33` base. For masks
(`bitsize` 32) it would build `LDRI32`… with an `AtallaMaskRegister` operand → assertion (Inferred; mask
pressure >15 never occurs in tests).
