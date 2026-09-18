# 08 — Optimization (`ppci/api.py:195-253`, `ppci/opt/`)

## 8.1 What runs

```
level = str(level); assert level in ("0","1","2","s")
if level == "0": return
passes = [Mem2RegPromotor(), RemoveAddZeroPass(), ConstantFolder(),
          CommonSubexpressionEliminationPass(), TailCallOptimization(),
          LoadAfterStorePass(), DeleteUnusedInstructionsPass(), CleanPass()] * 3
if level == "3": passes.append(CJumpPass())     # unreachable: "3" is not a valid level
verify_module(m); for p in passes: p.run(m); verify_module(m)
```

`-O1`, `-O2`, `-Os` are **identical** (`# TODO: differentiate between optimization levels!`, `:223`).
`atalla_cc` defaults to `-O2`. The `opt="speed"` selection-weight setting in `ir_to_stream` is
independent of `-O`.

## 8.2 The passes (all generic, `ppci/opt/`)

| Pass | Kind | Effect (verified by reading) | Atalla relevance |
|------|------|------|------|
| `Mem2RegPromotor` (`mem2reg.py`) | function | For each `Alloc` used by exactly one `AddressOf` whose users are all `Load`/`Store` of one type and not volatile: place phis on dominance frontiers (`CfgInfo`), rename, delete loads/stores/alloc. | Promotes `vec` locals too (types compare with `is`, and `ir.vec` is interned). Address-taken vectors (`&v`) stay in memory → scratchpad stack. `volatile` locals stay (see `int_pressure.c`). |
| `RemoveAddZeroPass` (`transform.py:76`) | instruction | `x + 0 → x`, `x * 1 → x` | |
| `ConstantFolder` (`constantfolding.py`) | block | folds `Binop`/`Cast`/… on `Const` operands with type-correct wraparound (`cast()` helper) | float constants: `cast` for non-integer types — not inspected; **Unknown** whether bf16 folds |
| `CommonSubexpressionEliminationPass` (`cse.py`) | block | replaces identical instructions within a block | explains shared `num_1_70` constants in traces |
| `TailCallOptimization` (`tailcall.py`) | function | self-recursive tail calls → jumps | |
| `LoadAfterStorePass` (`load_after_store.py`) | block | `[x]=a; b=[x]` → `b=a` | |
| `DeleteUnusedInstructionsPass` (`transform.py:102`) | block | removes unused `Value`s except `FunctionCall` | side-effect intrinsics are not `Value`s (`LoadWeights`, `ScpadLoad`, `VectorStore`) so they survive; `VectorLoad`/`Gemm`/`VecOpMasked` **are** `Value`s and are deleted if unused (e.g. an unused `vector_load` disappears — Inferred, consistent with the pass logic) |
| `CleanPass` (`clean.py`) | function | merges single-predecessor blocks, removes empty jump blocks | source of the non-contiguous block numbers |
| `CJumpPass` | — | never runs | |

Not wired: `ppci/opt/inline.py` (stub), any LICM, strength reduction, GVN, DCE across blocks.

## 8.3 Interactions to know

* Because `Mem2Reg` requires *all* uses to be loads/stores of the *same type*, a `vec` variable that is
  both loaded as `vec` and passed as `&v` is not promoted (see `sample.c` trace: `v1`, `v2`, `v_add` stay
  in scratchpad memory; `v3`, `v4` are SSA).
* `DeleteUnusedInstructionsPass` skips `FunctionCall` only; a call through `ProcedureCall` is not a Value.
* The passes do not know about vector semantics; `RemoveAddZeroPass` would rewrite `v + 0` only if the
  `0` is an `ir.Const` with `value == 0`, which for `vec + 0.0`(bf16 const) is `0.0 == 0` → True in Python
  → `v + 0.0` would be replaced by `v`. (Verified by reading; consistent with `patt_exp_vi` ignoring its
  constant.) Note `vec_op_masked` is *not* a `Binop`, so it is unaffected.
* `verify_module` after optimization enforces the dominance invariant that the DAG builder relies on
  (values available before use within a block ordering).
