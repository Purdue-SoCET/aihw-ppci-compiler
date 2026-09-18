# 11 — Register allocation (`ppci/codegen/registerallocator.py`, `flowgraph.py`, `interferencegraph.py`)

## 11.1 Virtual registers: creation to colouring

```
source value  →  IR value (SSA name)  →  SGValue.vreg (only where needed: phis, args, retval,
   multi-use/cross-block/volatile outputs, call args/results)  →  Tree REG/MOV nodes
→ pattern functions call context.new_reg(AtallaRegister | AtallaVectorRegister | AtallaMaskRegister)
   for every result they produce  →  Instruction operands hold Register objects with _color=None
→ alloc_frame: FlowGraph → liveness → InterferenceGraph → IRC worklists → assign_colors →
   apply_colors: reg.set_color(phys.color)  →  Instruction.encode reads reg.num
```

The register class of a vreg is its Python class (`InterferenceGraphNode.reg_class = type(vreg)`).
Physical candidates come from `arch.info.register_classes`:

| class | Python type | K | allocatable |
|-------|-------------|---|-------------|
| `reg` | `AtallaRegister` | 19 | `x9..x27` (`registers.py:145-172`) |
| `vecreg` | `AtallaVectorRegister` | 31 | `v1..v31` (`v0` reserved as zero/move source) |
| `maskreg` | `AtallaMaskRegister` | 15 | `m1..m15` (`m0` reserved as the default mask) |

`x0..x8`, `x28..x33` are never allocated; `x2`, `x8`, `x1`, `x32`, `x33`, `x0`, `x10`, `x12..x17` appear
as **pre-coloured** operands (created with `num=`), and `x10/x12..x17` also appear as clobbers on `Jal`.

## 11.2 Liveness (`flowgraph.py`)

`FlowGraph(instrs)` (`:51-92`) builds leaders from `ins.jumps` (set by patterns: `Jal(..., jumps=[label])`,
`Blts(..., jumps=[yes_label, jmp_ins])`); every `Label` that is a jump target starts a node, and the
*instruction after a jump* starts a node. Edges: jump instruction's node → target's node. **Fall-through
edges are not added** except via the `jumps` list — which is why `pattern_cjmpi` lists the following
`Jal` (`jmp_ins`) in its `jumps` (`instructions.py:601-602`). Per-instruction `gen = used_registers`,
`kill = defined_registers` (including `extra_uses/defs` from `RegisterUseDef`).

`calculate_liveness` (`:107-164`): iterative dataflow over nodes in list order until no change, then
per-instruction `live_in/live_out` propagated backwards inside each node.

## 11.3 Interference (`interferencegraph.py:51-78`)

For each instruction: nodes for `live_in` temps; edges between every pair in `live_out ∪ kill`;
edges between each of those and every register in `ins.clobbers` (so values live across a `jal` interfere
with `x10, x12..x17`). Also records `_def_map`/`_use_map` used for spill priorities and rewriting.
Pre-coloured registers become nodes too (`reg = vreg if vreg.is_colored`).

## 11.4 The IRC driver (`alloc_frame`, `:233-289`)

```
loop:
  init_data(frame)                       # rebuild CFG, liveness, IG, worklists from scratch
  while simplify | coalesc | freeze | select_spill: …
  spilled = assign_colors()              # pop select_stack, pick first free reg of the class
  if spilled: rewrite_program(node) for each; continue (max 30 rounds)
  else break
remove_redundant_moves(); apply_colors()
```

* `is_colorable` uses the pq-test (`:408-442`): `num_blocked = Σ q(B, class(neighbour))` where
  `q(B, C)` = max number of B-registers one C-register can block via aliases (`:394-406`). Atalla has no
  aliases, so `q(B,B)=1`, `q(B,C≠B)=0` → the test degenerates to “degree within the same class < K”.
* `assign_colors` (`:751-785`): `ok_regs = cls_regs[class] − taken` and takes `ok_regs[0]` — the
  **lowest-numbered free register in class order**. This is why code clusters on `x9, x10, x11` and `v1, v2`.
* **Coalescing is dead for Atalla.** `init_data` collects `self.moves = [i for i in frame.instructions
  if i.ismove]` (`:323`). `AtallaArch.move` never sets `ismove`, no pattern sets it, so `worklistMoves`
  is always empty; `coalesc()` never runs; `freeze_worklist` is always empty (`is_move_related` False).
  Every phi copy, argument copy, return copy and DAG-splitter `MOV` therefore survives as a real
  instruction. Contrast `ppci/arch/riscv/arch.py` where `move` returns `Mov(dst, src, ismove=True)`.
  Verified: the for-loop body (ch. 21) has 3 `addi_s x, y, 0` copies per 2 arithmetic instructions.
* `select_spill` (`:671-698`): priority `(uses+defs)/degree`, lowest first.
* `rewrite_program` (`:700-749`): allocates a slot — `frame.scpad_alloc(64, 64)` for
  `AtallaVectorRegister` (`:709-710`), else `frame.alloc(bitsize//8, same)` — then for every use/def
  instruction replaces the temp with a **fresh vreg** and inserts `gen_load` before / `gen_store` after
  (ch. 10.5). Spill code itself contains new vregs, hence the outer loop.
* `apply_colors` (`:792-808`): `reg.set_color(node.reg.color)` for all temps in every node; asserts
  pre-coloured temps keep their colour; records `frame.used_regs`.

Verified spill behaviour: `vec_pressure.c` (40 live vectors) spills 10 vector vregs to scratchpad slots
`-64 … -640` with `vreg_st v1, x10, x9, 31, 3` / `vreg_ld` pairs; `int_pressure.c` spills scalars to
`sw_s x9, 124(x8)` etc. (offsets already peephole-adjusted).

## 11.5 Constraints and how target facts enter the allocator

| Constraint | Mechanism |
|-----------|-----------|
| Argument/return registers | pre-coloured operands from `gen_function_enter/exit/gen_call` + `RegisterUseDef` to define/use them at the right points |
| Call clobbers | `Jal(..., clobbers=caller_save)` → interference edges |
| Reserved `v0`, `m0`, `x0..x8`, `x28+` | simply absent from the register-class lists; used as fixed operands |
| Per-class K | `RegisterClass.registers` length |
| Spill slot size/kind | `Register.bitsize` and `isinstance(vreg, AtallaVectorRegister)` |
| Mask ↔ scalar | not a move; `mv_stm`/`mv_mts` instructions from patterns |

There is no register-class inference: a vreg's class is fixed at `new_reg` time by the pattern author.
Mixing classes (e.g. `Addis(vecreg, …)`) fails at the `Operand` setter assertion when the instruction is
constructed, long before allocation.

## 11.6 Things that look like allocation but are not

* `frame.live_ranges()` references `frame.cfg`, which this allocator never sets → would raise.
* `frame.is_used(register, alias)` (`stack.py:150-153`) is only consulted for `callee_save`, which is empty.
* `Frame.used_regs` is filled but only read by the HTML reporter.
