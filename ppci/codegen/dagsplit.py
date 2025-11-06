"""DAG splitting into trees.

The selection dag is splitted into trees by this module.

"""

import logging

from .. import ir
from ..utils.tree import Tree


class DagSplitter:
    """Class that splits a DAG into a forest of trees.

    This series is sorted
    such that data dependencies are met. The trees can henceforth be
    used to match trees.
    """

    logger = logging.getLogger("dag-splitter")

    def __init__(self, arch):
        self.arch = arch

    def split_into_trees(self, sgraph, ir_function, function_info, debug_db):
        """Split a forest of trees into a sorted series of trees for each
        block.
        """
        self.debug_db = debug_db
        self.frame = function_info.frame
        forest = []
        self.assign_vregs(sgraph, function_info)

        # Process other blocks:
        for ir_block in ir_function:
            block_trees = self.split_group_into_trees(
                sgraph, function_info, ir_block
            )
            forest.append(function_info.label_map[ir_block])
            forest.extend(block_trees)

        # Emit epilog label here, return and exit instructions jump to it
        forest.append(function_info.epilog_label)

        return forest

    def split_group_into_trees(self, sgraph, function_info, group):
        nodes = sgraph.get_group(group)
        # Get rid of ENTRY and EXIT:
        nodes = set(
            filter(lambda x: x.name.op not in ["ENTRY", "EXIT"], nodes)
        )

        tail_node = function_info.block_tails[group]
        return self.make_trees(nodes, tail_node)

    def assign_vregs(self, sgraph, function_info):
        """Give vreg values to values that cross block boundaries"""
        frame = function_info.frame
        for node in sgraph:
            if node.group:
                self.check_vreg(node, frame)

    def check_vreg(self, node, frame):
        """Determine whether node outputs need a virtual register"""
        assert node.group is not None

        for data_output in node.data_outputs:
            if (
                (len(data_output.users) > 1)
                or node.volatile
                or any(u.group is not node.group for u in data_output.users)
            ):
                if data_output.wants_vreg and not data_output.vreg:
                    cls = self.get_reg_class(data_output)
                    vreg = frame.new_reg(cls, data_output.name)
                    data_output.vreg = vreg

    def _register_tree_owners(self, owner_map, node, tree):
        """Recursively mark DAG node ownership for every subtree."""
        owner_map[tree] = node
        for child in tree.children:
            self._register_tree_owners(owner_map, node, child)

    def make_trees(self, nodes, tail_node):
        """Create a tree from a list of sorted nodes."""
        sorted_nodes = topological_sort_modified(nodes, tail_node)
        trees = []
        node_map = {}
        owner_map = self.frame.__dict__.setdefault("tree_owner", {})

        def mk_tr(inp):
            if inp.vreg:
                t = Tree(self.make_op("REG", inp.ty), value=inp.vreg)
                owner_map[t] = inp.node
            elif inp.node in node_map:
                t = node_map[inp.node]
                # already tracked
            elif inp.node.name.op == "LABEL":
                t = Tree(str(inp.node.name), value=inp.node.value)
                self._register_tree_owners(owner_map, inp.node, t)
            else:
                kids = [mk_tr(i) for i in inp.node.data_inputs]
                t = Tree(str(inp.node.name), *kids, value=inp.node.value)
                self._register_tree_owners(owner_map, inp.node, t)
            return t

        for node in sorted_nodes:
            children = [mk_tr(inp) for inp in node.data_inputs]
            tree = Tree(str(node.name), *children, value=node.value)
            self._register_tree_owners(owner_map, node, tree)
            self.debug_db.map(node, tree)

            if len(node.data_outputs) == 0:
                if node.volatile:
                    trees.append(tree)
            else:
                data_output = node.data_outputs[0]
                if data_output.vreg:
                    vreg = data_output.vreg
                    typ  = data_output.ty
                    mov  = Tree(self.make_op("MOV", typ), tree, value=vreg)
                    self._register_tree_owners(owner_map, node, mov)
                    trees.append(mov)
                    reg  = Tree(self.make_op("REG", typ), value=vreg)
                    self._register_tree_owners(owner_map, node, reg)
                    tree = reg
                elif node.volatile:
                    trees.append(tree)

            node_map[node] = tree
        return trees

    def make_op(self, op, typ):
        """Construct a string opcode from an operation and a type"""
        assert isinstance(typ, ir.Typ), str(typ)
        return f"{op}{typ}".upper()

    def get_reg_class(self, data_flow):
        """Determine the register class suited for this data flow line"""
        op = data_flow.node.name
        assert isinstance(op.ty, ir.Typ)
        return self.arch.get_reg_class(ty=op.ty)


def topological_sort_modified(nodes, start):
    """Modified topological sort, start at the end and work back"""
    unmarked = set(nodes)
    marked = set()
    temp_marked = set()
    L = []

    def visit(n):
        if n not in nodes:
            return
        assert n not in temp_marked, "DAG has cycles"
        if n in unmarked:
            temp_marked.add(n)

            # 1 satisfy control dependencies:
            for inp in n.control_inputs:
                visit(inp.node)

            # 2 memory dependencies:
            for inp in n.memory_inputs:
                visit(inp.node)

            # 3 data dependencies:
            for inp in n.data_inputs:
                visit(inp.node)
            temp_marked.remove(n)
            marked.add(n)
            unmarked.remove(n)
            L.append(n)

    # Start to visit with pre-knowledge of the last node!
    visit(start)
    while unmarked:
        node = next(iter(unmarked))
        visit(node)

    # Hack: move tail again to tail:
    if L:
        if L[-1] is not start:
            L.remove(start)
            L.append(start)
    return L
