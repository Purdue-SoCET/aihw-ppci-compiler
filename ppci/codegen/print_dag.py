#!/usr/bin/env python3
"""
Utility script to print out the IR Selection DAG for a given function.
This uses the SelectionGraphBuilder from your irdag module.
"""

import sys
import logging
from .irdag import SelectionGraphBuilder, FunctionInfo, prepare_function_info
from .selectiongraph import SGValue

def print_dag(sgraph):
    """Pretty print the selection DAG grouped by basic block."""
    print("=== SELECTION DAG ===")
    node_ids = {n: i for i, n in enumerate(sgraph.nodes)}

    # Group nodes by basic block (group attr)
    groups = {}
    for n in sgraph.nodes:
        grp = getattr(n, "group", None)
        groups.setdefault(grp, []).append(n)

    for grp, nodes in groups.items():
        grp_name = getattr(grp, "name", "<no-group>")
        print(f"\n[ Basic Block: {grp_name} ]")
        for n in nodes:
            nid = node_ids[n]
            op = str(n.name)
            val = f" value={n.value}" if getattr(n, "value", None) is not None else ""
            print(f"  (n{nid}) {op}{val}")

            # Inputs
            if n.inputs:
                in_str = ", ".join(
                    f"n{node_ids.get(inp.node, '?')}.{inp.name}"
                    + ("[CTRL]" if inp.kind == SGValue.CONTROL else "")
                    for inp in n.inputs
                )
                print(f"    inputs : {in_str}")
            else:
                print("    inputs : -")

            # Outputs
            if n.outputs:
                out_str = ", ".join(
                    f"{out.name}" +
                    ("[CTRL]" if out.kind == SGValue.CONTROL else "")
                    for out in n.outputs
                )
                print(f"    outputs: {out_str}")
            else:
                print("    outputs: -")

def build_and_print(ir_function, arch, frame, debug_db=None):
    """Builds the selection DAG for a function and prints it."""
    class DummyDebugDb:
        def map(self, *a, **kw): pass
        def contains(self, *a, **kw): return False
        def get(self, *a, **kw): return None

    if debug_db is None:
        debug_db = DummyDebugDb()

    finfo = FunctionInfo(frame)
    prepare_function_info(arch, finfo, ir_function)
    builder = SelectionGraphBuilder(arch)
    sgraph = builder.build(ir_function, finfo, debug_db)
    print_dag(sgraph)


if __name__ == "__main__":
    print("Usage: import this script and call build_and_print(ir_func, arch, frame)")
    print("Example:")
    print("  from print_dag import build_and_print")
    print("  build_and_print(ir_function, arch, frame)")
