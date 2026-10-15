import unittest
from ppci.codegen.dagsplit import topological_sort_modified


class DummySGNode:
    """Mock node mimicking SGNode for topological sort testing."""

    def __init__(self, name, custom_hash=None):
        self.name = name
        self.control_inputs = []
        self.memory_inputs = []
        self.data_inputs = []
        self._hash = custom_hash

    def __hash__(self):
        if self._hash is not None:
            return self._hash
        return id(self)

    def __eq__(self, other):
        return self is other

    def __repr__(self):
        return f"DummySGNode({self.name})"


class DummyInput:
    def __init__(self, node):
        self.node = node


class DagSplitDeterminismTestCase(unittest.TestCase):
    def test_topological_sort_preserves_insertion_order(self):
        """Verify that independent unvisited nodes preserve insertion order,
        independent of hash collisions or arbitrary hash ordering.
        """
        # Create nodes whose hash values would scramble standard set iteration:
        # e.g., hash(n1)=100, hash(n2)=1, hash(n3)=50
        n1 = DummySGNode("Node1", 100)
        n2 = DummySGNode("Node2", 1)
        n3 = DummySGNode("Node3", 50)
        start = DummySGNode("StartNode", 999)

        input_nodes = [n1, n2, n3, start]
        result = topological_sort_modified(input_nodes, start)

        # Expected order: start node dependency (if any), then unvisited roots in insertion order:
        # [n1, n2, n3, start]
        self.assertEqual(result, [n1, n2, n3, start])

    def test_topological_sort_dependencies_and_unvisited_order(self):
        """Verify that data/memory dependencies are respected while unvisited
        independent trees follow insertion order.
        """
        tree_a_child = DummySGNode("TreeA_Child", 500)
        tree_a_root = DummySGNode("TreeA_Root", 20)
        tree_a_root.data_inputs.append(DummyInput(tree_a_child))

        tree_b_child = DummySGNode("TreeB_Child", 10)
        tree_b_root = DummySGNode("TreeB_Root", 80)
        tree_b_root.memory_inputs.append(DummyInput(tree_b_child))

        start = DummySGNode("Start", 300)

        input_nodes = [tree_a_child, tree_a_root, tree_b_child, tree_b_root, start]
        result = topological_sort_modified(input_nodes, start)

        # start has no inputs, so it comes first in visit(start), but hack moves it to tail
        # tree_a_child must precede tree_a_root, tree_b_child must precede tree_b_root,
        # and Tree A must precede Tree B because of insertion order.
        expected = [tree_a_child, tree_a_root, tree_b_child, tree_b_root, start]
        self.assertEqual(result, expected)


if __name__ == "__main__":
    unittest.main()
