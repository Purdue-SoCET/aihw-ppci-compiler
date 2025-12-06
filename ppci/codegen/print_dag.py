#!/usr/bin/env python3
"""
Utility script to print out the IR Selection DAG for a given function.
This uses the SelectionGraphBuilder from your irdag module.
"""

import sys
import logging
from .irdag import SelectionGraphBuilder, FunctionInfo, prepare_function_info
from .selectiongraph import SGValue
from collections import defaultdict, deque
import pydot


def group_nodes_by_depth(sgraph):
    """
    Returns a dict: { block -> [ [nodes_at_depth0], [nodes_at_depth1], ... ] }.
    Only considers edges within the same basic block (node.group).
    """
    # 1) collect nodes per block
    nodes_by_block = defaultdict(list)
    for n in sgraph.nodes:
        nodes_by_block[n.group].append(n)

    result = {}

    for block, nodes in nodes_by_block.items():
        # 2) build preds within the same block
        preds = {n: [] for n in nodes}
        succs = {n: [] for n in nodes}
        in_same = set(nodes)

        for v in nodes:
            for inp in getattr(v, "inputs", []):
                # inp is SGValue; it has .node pointing to predecessor SGNode
                u = getattr(inp, "node", None)
                if u is not None and u in in_same:
                    preds[v].append(u)
                    succs[u].append(v)

        # 3) topo order with Kahn's algorithm
        indeg = {n: len(preds[n]) for n in nodes}
        q = deque([n for n in nodes if indeg[n] == 0])
        topo = []
        while q:
            x = q.popleft()
            topo.append(x)
            for y in succs[x]:
                indeg[y] -= 1
                if indeg[y] == 0:
                    q.append(y)

        # If graph had cycles (shouldn't), fall back to whatever we got
        if len(topo) < len(nodes):
            # keep remaining nodes appended to preserve stability
            rest = [n for n in nodes if n not in topo]
            topo.extend(rest)

        # 4) assign levels
        level = {}
        for n in topo:
            if not preds[n]:
                level[n] = 0
            else:
                level[n] = 1 + max(level[p] for p in preds[n])

        # 5) pack by level, stable order
        maxlvl = max(level.values()) if nodes else -1
        layers = [[] for _ in range(maxlvl + 1)]
        for n in topo:
            layers[level[n]].append(n)

        '''
        # cap width to 4 per depth by chunking each layer
        MAX_PER_DEPTH = 4
        limited_layers = []
        for layer in layers:
            for i in range(0, len(layer), MAX_PER_DEPTH):
                limited_layers.append(layer[i:i + MAX_PER_DEPTH])
        layers = limited_layers
        '''

        result[block] = layers

    return result

def print_dag(sgraph):
    """Pretty print the selection DAG grouped by basic block."""
    graph = pydot.Dot("my_graph", graph_type="digraph", bgcolor="white")
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

            my_node = pydot.Node(f"n{nid}", label=f"n{nid} {op}{val}")
            graph.add_node(my_node)

            # Inputs
            if n.inputs:
                in_str = ", ".join(
                    f"n{node_ids.get(inp.node, '?')}.{inp.name}"
                    + ("[CTRL]" if inp.kind == SGValue.CONTROL else "")
                    for inp in n.inputs
                )
                print(f"    inputs : {in_str}")
                for inp in n.inputs:
                    graph.add_edge(pydot.Edge(f"n{node_ids.get(inp.node, '?')}", f"n{nid}"))
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

    graph.write_png("selection_dag.png")
    # bucket nodes by depth (per basic block) and attach to sgraph
    sgraph.levels_by_block = group_nodes_by_depth(sgraph)

    # --- PRINT THE BUCKETS ---
    node_ids = {n: i for i, n in enumerate(sgraph.nodes)}
    for blk, layers in sgraph.levels_by_block.items():
        name = getattr(blk, "name", "<no-group>")
        print(f"\n[ Buckets for {name} ]")
        for d, layer in enumerate(layers):
            items = [f"n{node_ids[n]} {str(n.name)}" for n in layer]
            print(f"  depth {d}: {items}")
    # -------------------------

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

    # compute and store the layers (list[list[SGNode]]) per block
    levels_by_block = group_nodes_by_depth(sgraph)
    sgraph.levels_by_block = levels_by_block  # attach for later reuse
    return sgraph, levels_by_block            # keeps function usable programmatically


if __name__ == "__main__":
    print("Usage: import this script and call build_and_print(ir_func, arch, frame)")
    print("Example:")
    print("  from print_dag import build_and_print")
    print("  build_and_print(ir_function, arch, frame)")
