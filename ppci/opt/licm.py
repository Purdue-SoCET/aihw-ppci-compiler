"""Loop Invariant Code Motion (LICM) optimization pass.

Detects loop-invariant expressions and loads inside loops and hoists them
to the loop preheader, reducing redundant computation and memory traffic
inside loop bodies.
"""

from .. import ir
from ..graph.cfg import ir_function_to_graph
from .transform import FunctionPass


class LoopInvariantCodeMotionPass(FunctionPass):
    """Hoists loop-invariant expressions and loads out of loops into preheaders."""

    def on_function(self, function: ir.SubRoutine):
        if not function.blocks or len(function.blocks) < 2:
            return

        cfg, block_map = ir_function_to_graph(function)
        node_map = {n: b for b, n in block_map.items()}
        loops = cfg.calculate_loops()
        if not loops:
            return

        # Sort loops by size ascending (process innermost loops first so invariants
        # can propagate outwards through nested loops)
        sorted_loops = sorted(loops, key=lambda l: 1 + len(l.rest))

        for loop in sorted_loops:
            if loop.header not in node_map:
                continue

            header = node_map[loop.header]
            loop_blocks = {header}
            for n in loop.rest:
                if n in node_map:
                    loop_blocks.add(node_map[n])

            # Find or establish the loop preheader
            entry_preds = [p for p in header.predecessors if p not in loop_blocks]
            if not entry_preds:
                continue

            preheader = None
            if len(entry_preds) == 1:
                cand = entry_preds[0]
                if len(cand.successors) == 1 and cand.successors[0] is header:
                    preheader = cand

            if preheader is None:
                # If no clean dedicated preheader exists, skip hoisting for this loop
                continue

            # Check if any memory modification occurs in the loop
            has_stores_or_calls = any(
                isinstance(ins, (ir.Store, ir.FunctionCall, ir.ProcedureCall))
                for b in loop_blocks
                for ins in b
            )

            # Iteratively identify and hoist invariant instructions
            invariant_instructions = set()
            changed = True
            while changed:
                changed = False
                for b in list(loop_blocks):
                    for ins in list(b.instructions):
                        if ins in invariant_instructions:
                            continue
                        if not isinstance(
                            ins, (ir.Binop, ir.Unop, ir.Cast, ir.AddressOf, ir.Load)
                        ):
                            continue
                        if getattr(ins, "volatile", False):
                            continue
                        if isinstance(ins, ir.Load) and has_stores_or_calls:
                            continue

                        # Check if all operands used by this instruction are invariant
                        all_operands_invariant = True
                        for use in ins.uses:
                            if use in function.arguments:
                                continue
                            if hasattr(use, "block") and use.block is not None:
                                if use.block not in loop_blocks or use in invariant_instructions:
                                    continue
                            all_operands_invariant = False
                            break

                        if all_operands_invariant:
                            invariant_instructions.add(ins)
                            ins.block.remove_instruction(ins)
                            preheader.insert_instruction(
                                ins, before_instruction=preheader.last_instruction
                            )
                            changed = True
