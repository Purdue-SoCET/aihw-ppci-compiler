# 12 — Instruction scheduling

**There is no instruction scheduler on any executed path.** Verified:

* `ppci/codegen/instructionscheduler.py` defines `InstructionScheduler.schedule(self, graph, frame): pass`
  (`:7-11`).
* `CodeGenerator.__init__` instantiates it (`codegen.py:57`) but `select_and_schedule` (`:225-240`) has
  `tree_method = True` and the scheduler call is inside a commented block.
* The order of machine instructions is therefore fixed by:
  1. `depth_first_order` over IR blocks (`irdag.py:83-93`) — BFS from the entry, so block emission order is
     *not* source order and not a layout heuristic (see the `main_block0 → main_block2 → main_block3 →
     main_block4` order in ch. 21).
  2. `topological_sort_modified` (`dagsplit.py:148-189`) inside each block — DFS from the block's tail
     node, visiting control inputs first, then memory, then data. Because every chained node hangs off
     the previous chained node, chained (side-effecting) nodes keep IR order; pure arithmetic is emitted
     as late as possible (just before its first consumer's tree), i.e. **greedy sink** scheduling.
  3. Inline emission order within a pattern function.
  4. Register allocation does not reorder; spill code is inserted adjacent to uses/defs.
  5. `gen_function_enter` moves are emitted **before** the first block label; `gen_function_exit` after the
     epilog label.

The `instruction_latency.py` table (7 scalar entries) is imported by `api.py` but only consumed by the
dead text packetizer. `ppci/codegen/print_dag.py:group_nodes_by_depth` computes per-block DAG depth
layers (Kahn) into `sgraph.levels_by_block` (`instructionselector.py:387`) — computed on every compile,
consumed by nothing (the bucket builder at `:411-473` is defined inside `select` but its call at `:469-470`
is commented out).

Consequences for anyone adding a scheduler: the frame is a flat instruction list with `jumps` on branch
instructions; block boundaries are `Label` instructions; `RegisterUseDef` pseudo-instructions carry
def/use information that a scheduler must treat as barriers for the involved registers; `InlineAssembly`
is opaque; `fprel` immediates are fixed up **after** allocation by the peephole, so a scheduler running
before the peephole must not clone/split those instructions.
