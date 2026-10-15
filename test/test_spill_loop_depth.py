import unittest
from unittest.mock import MagicMock
from ppci.arch.example import ExampleRegister, ExampleInstruction
from ppci.codegen.flowgraph import FlowGraph
from ppci.codegen.interferencegraph import InterferenceGraph
from ppci.codegen.registerallocator import GraphColoringRegisterAllocator


class MockInstruction(ExampleInstruction):
    def __init__(self, name, jumps=None, defs=None, uses=None):
        super().__init__()
        self._name = name
        self.jumps = list(jumps) if jumps else []
        self.output_registers = list(defs) if defs else []
        self.input_registers = list(uses) if uses else []

    def __repr__(self):
        return f"MockIns({self._name})"


class SpillLoopDepthTestCase(unittest.TestCase):
    def test_flowgraph_loop_depth_calculation(self):
        """Verify that loop nesting depths (0, 1, 2) and weights (1, 10, 100)
        are properly computed for basic blocks and instructions in FlowGraph.
        """
        # CFG structure:
        # entry -> outer_header -> inner_header -> inner_body -> outer_body -> exit
        # inner_body jumps back to inner_header (inner loop)
        # outer_body jumps back to outer_header (outer loop)
        inner_header_ins = MockInstruction("inner_header")
        outer_header_ins = MockInstruction("outer_header")
        inner_body_ins = MockInstruction("inner_body")
        outer_body_ins = MockInstruction("outer_body")
        exit_ins = MockInstruction("exit")

        entry_ins = MockInstruction("entry", jumps=[outer_header_ins])
        outer_header_ins.jumps = [inner_header_ins]
        inner_header_ins.jumps = [inner_body_ins]
        inner_body_ins.jumps = [inner_header_ins, outer_body_ins]
        outer_body_ins.jumps = [outer_header_ins, exit_ins]

        instrs = [
            entry_ins,
            outer_header_ins,
            inner_header_ins,
            inner_body_ins,
            outer_body_ins,
            exit_ins,
        ]

        cfg = FlowGraph(instrs)
        cfg.calculate_loop_depth()

        self.assertEqual(entry_ins.loop_depth, 0)
        self.assertEqual(entry_ins.weight, 1)

        self.assertEqual(outer_header_ins.loop_depth, 1)
        self.assertEqual(outer_header_ins.weight, 10)

        self.assertEqual(inner_header_ins.loop_depth, 2)
        self.assertEqual(inner_header_ins.weight, 100)

        self.assertEqual(inner_body_ins.loop_depth, 2)
        self.assertEqual(inner_body_ins.weight, 100)

        self.assertEqual(outer_body_ins.loop_depth, 1)
        self.assertEqual(outer_body_ins.weight, 10)

        self.assertEqual(exit_ins.loop_depth, 0)
        self.assertEqual(exit_ins.weight, 1)

    def test_select_spill_prioritizes_outer_variable(self):
        """Verify that register allocator select_spill picks the cold outer-scope
        variable to spill rather than the hot inner-loop variable with equal degrees.
        """
        from ppci.api import get_arch
        allocator = GraphColoringRegisterAllocator(get_arch("example"), None, None)
        frame = MagicMock()
        ig = MagicMock()
        frame.ig = ig
        allocator.frame = frame

        # Create two nodes in spill_worklist
        node_outer = MagicMock()
        node_outer.is_colored = False
        node_outer.degree = 5
        t_outer = ExampleRegister("t_outer")
        node_outer.temps = [t_outer]

        node_inner = MagicMock()
        node_inner.is_colored = False
        node_inner.degree = 5
        t_inner = ExampleRegister("t_inner")
        node_inner.temps = [t_inner]

        # Instructions for outer variable (depth=0, weight=1)
        ins_def_outer = MockInstruction("def_outer")
        ins_def_outer.weight = 1
        ins_use_outer = MockInstruction("use_outer")
        ins_use_outer.weight = 1

        # Instructions for inner variable (depth=2, weight=100)
        ins_def_inner = MockInstruction("def_inner")
        ins_def_inner.weight = 100
        ins_use_inner = MockInstruction("use_inner")
        ins_use_inner.weight = 100

        ig.defs.side_effect = lambda t: [ins_def_outer] if t == t_outer else [ins_def_inner]
        ig.uses.side_effect = lambda t: [ins_use_outer] if t == t_outer else [ins_use_inner]

        from ppci.utils.collections import OrderedSet
        allocator.spill_worklist = OrderedSet([node_inner, node_outer])
        allocator.simplify_worklist = OrderedSet()
        allocator.freeze_moves = MagicMock()

        allocator.select_spill()

        # The node selected for spilling should be node_outer (cost 2 vs 200)
        self.assertIn(node_outer, allocator.simplify_worklist)
        self.assertNotIn(node_outer, allocator.spill_worklist)
        self.assertIn(node_inner, allocator.spill_worklist)


if __name__ == "__main__":
    unittest.main()
