"""Tests for the factor four loop unrolling pass."""

import io
import os
import unittest

from ppci import api, ir, irutils
from ppci.binutils.debuginfo import DebugDb
from ppci.irutils import verify_module
from ppci.lang.atalla_c.api import atalla_c_to_ir
from ppci.opt import (
    DeleteUnusedInstructionsPass,
    LoopUnrollPass,
    Mem2RegPromotor,
)


def module_text(module):
    f = io.StringIO()
    irutils.Writer(f).write(module)
    return f.getvalue()


def run_function(module, name, *args):
    """Run an ir function by converting it to python code."""
    f = io.StringIO()
    api.ir_to_python([module], f)
    namespace = {}
    exec(f.getvalue(), namespace)
    return namespace[name](*args)


class LoopUnrollTestCase(unittest.TestCase):
    """Build the loop below and check how the pass treats it.

    int a = 5;
    for (int i = start; i cond bound; i += step) { a += i; }
    return a;
    """

    def setUp(self):
        self.builder = irutils.Builder()
        self.module = ir.Module("test", debug_db=DebugDb())
        self.builder.set_module(self.module)
        self.function = self.builder.new_function(
            "loop", ir.Binding.GLOBAL, ir.i32
        )
        self.n = ir.Parameter("n", ir.i32)
        self.function.add_parameter(self.n)
        self.builder.set_function(self.function)
        self.pass_ = LoopUnrollPass()

    def tearDown(self):
        verify_module(self.module)

    def build_loop(
        self,
        start=0,
        bound=10,
        step=1,
        cond="<",
        body_hook=None,
        extra_block=False,
    ):
        builder = self.builder
        first = builder.new_block()
        self.function.entry = first
        header = builder.new_block()
        body = builder.new_block()
        iterator = builder.new_block()
        final = builder.new_block()

        builder.set_block(first)
        five = builder.emit(ir.Const(5, "five", ir.i32))
        zero = builder.emit(ir.Const(start, "start", ir.i32))
        builder.emit(ir.Jump(header))

        builder.set_block(header)
        a = builder.emit(ir.Phi("a", ir.i32))
        i = builder.emit(ir.Phi("i", ir.i32))
        if bound is None:
            limit = self.n
        else:
            limit = builder.emit(ir.Const(bound, "bound", ir.i32))
        builder.emit(ir.CJump(i, cond, limit, body, final))

        builder.set_block(body)
        a_next = builder.emit(ir.add(a, i, "a_next", ir.i32))
        if body_hook:
            body_hook(builder, a_next)
        if extra_block:
            middle = builder.new_block()
            builder.emit(ir.Jump(middle))
            builder.set_block(middle)
        builder.emit(ir.Jump(iterator))

        builder.set_block(iterator)
        one = builder.emit(ir.Const(step, "step", ir.i32))
        i_next = builder.emit(ir.add(i, one, "i_next", ir.i32))
        builder.emit(ir.Jump(header))

        builder.set_block(final)
        builder.emit(ir.Return(a))

        a.set_incoming(first, five)
        a.set_incoming(iterator, a_next)
        i.set_incoming(first, zero)
        i.set_incoming(iterator, i_next)
        verify_module(self.module)

        self.header = header
        self.iterator = iterator
        self.a = a
        self.i = i
        self.a_next = a_next
        self.i_next = i_next

    def assert_unchanged(self):
        before = module_text(self.module)
        self.pass_.run(self.module)
        self.assertEqual(before, module_text(self.module))

    def test_unrolls_simple_loop(self):
        # 0, 1, ..., 7. Four copies of the body, result 5 + 28.
        self.build_loop(bound=8)
        expected = run_function(self.module, "loop", 0)

        self.pass_.run(self.module)

        # The iterator gains three copies of the body add and the increment:
        copied = self.iterator.instructions[2:-1]
        self.assertEqual(9, len(copied))
        prev_a = self.a_next
        prev_i = self.i_next
        last_a = last_i = None
        for offset in range(0, 9, 3):
            a_copy, step_copy, i_copy = copied[offset : offset + 3]
            self.assertIs(prev_a, a_copy.a)
            self.assertIs(prev_i, a_copy.b)
            self.assertIsInstance(step_copy, ir.Const)
            self.assertIs(prev_i, i_copy.a)
            self.assertIs(step_copy, i_copy.b)
            prev_a, prev_i = a_copy, i_copy
            last_a, last_i = a_copy, i_copy

        # The phis now take the values from the last copy:
        self.assertIs(last_a, self.a.get_value(self.iterator))
        self.assertIs(last_i, self.i.get_value(self.iterator))

        verify_module(self.module)
        self.assertEqual(33, expected)
        self.assertEqual(expected, run_function(self.module, "loop", 0))

    def test_unrolls_with_nonzero_start(self):
        # i = 1; i < 9 walks eight trips.
        self.build_loop(start=1, bound=9)
        expected = run_function(self.module, "loop", 0)
        self.pass_.run(self.module)
        self.assertIsNot(self.i_next, self.i.get_value(self.iterator))
        self.assertEqual(41, expected)
        self.assertEqual(expected, run_function(self.module, "loop", 0))

    def test_second_run_changes_nothing(self):
        self.build_loop(bound=8)
        self.pass_.run(self.module)
        self.assert_unchanged()

    def test_skips_odd_count(self):
        self.build_loop(bound=9)
        self.assert_unchanged()

    def test_skips_zero_iterations(self):
        self.build_loop(bound=0)
        self.assert_unchanged()

    def test_skips_one_iteration(self):
        self.build_loop(bound=1)
        self.assert_unchanged()

    def test_skips_two_iterations(self):
        self.build_loop(bound=2)
        self.assert_unchanged()

    def test_skips_six_iterations(self):
        self.build_loop(start=3, bound=9)
        self.assert_unchanged()

    def test_skips_variable_bound(self):
        self.build_loop(bound=None)
        self.assert_unchanged()

    def test_skips_step_of_two(self):
        self.build_loop(step=2)
        self.assert_unchanged()

    def test_skips_other_comparison(self):
        self.build_loop(cond="<=")
        self.assert_unchanged()

    def test_skips_call_in_body(self):
        def hook(builder, value):
            builder.emit(
                ir.FunctionCall(self.function, [value], "call", ir.i32)
            )

        self.build_loop(body_hook=hook)
        self.assert_unchanged()

    def test_skips_store_in_body(self):
        def hook(builder, value):
            alloc = builder.emit(ir.Alloc("mem", 4, 4))
            addr = builder.emit(ir.AddressOf(alloc, "addr"))
            builder.emit(ir.Store(value, addr))

        self.build_loop(body_hook=hook)
        self.assert_unchanged()

    def test_skips_extra_block(self):
        self.build_loop(extra_block=True)
        self.assert_unchanged()

    def test_unrolls_fused_vector_latch(self):
        """One latch block, the shape CleanPass leaves behind."""
        builder = self.builder
        first = builder.new_block()
        self.function.entry = first
        header = builder.new_block()
        latch = builder.new_block()
        final = builder.new_block()

        builder.set_block(first)
        zero = builder.emit(ir.Const(0, "start", ir.i32))
        a0 = builder.emit(ir.Const(0x1000, "a0", ir.i32))
        b0 = builder.emit(ir.Const(0x2000, "b0", ir.i32))
        c0 = builder.emit(ir.Const(0x3000, "c0", ir.i32))
        builder.emit(ir.Jump(header))

        builder.set_block(header)
        i = builder.emit(ir.Phi("i", ir.i32))
        a = builder.emit(ir.Phi("a", ir.i32))
        b = builder.emit(ir.Phi("b", ir.i32))
        c = builder.emit(ir.Phi("c", ir.i32))
        bound = builder.emit(ir.Const(8, "bound", ir.i32))
        builder.emit(ir.CJump(i, "<", bound, latch, final))

        builder.set_block(latch)
        one = builder.emit(ir.Const(1, "one", ir.i32))
        cols = builder.emit(ir.Const(31, "cols", ir.i32))
        x = builder.emit(ir.VectorLoad(a, one, cols, one, "x", ir.vec))
        y = builder.emit(ir.VectorLoad(b, one, cols, one, "y", ir.vec))
        z = builder.emit(ir.Binop(x, "+", y, "z", ir.vec))
        builder.emit(ir.VectorStore(z, c, one, cols, one))
        step = builder.emit(ir.Const(64, "step", ir.i32))
        a_next = builder.emit(ir.add(a, step, "a_next", ir.i32))
        b_next = builder.emit(ir.add(b, step, "b_next", ir.i32))
        c_next = builder.emit(ir.add(c, step, "c_next", ir.i32))
        i_next = builder.emit(ir.add(i, one, "i_next", ir.i32))
        builder.emit(ir.Jump(header))

        builder.set_block(final)
        ret = builder.emit(ir.Const(0, "ret", ir.i32))
        builder.emit(ir.Return(ret))

        i.set_incoming(first, zero)
        i.set_incoming(latch, i_next)
        a.set_incoming(first, a0)
        a.set_incoming(latch, a_next)
        b.set_incoming(first, b0)
        b.set_incoming(latch, b_next)
        c.set_incoming(first, c0)
        c.set_incoming(latch, c_next)
        verify_module(self.module)

        self.pass_.run(self.module)

        loads = [ins for ins in latch if isinstance(ins, ir.VectorLoad)]
        stores = [ins for ins in latch if isinstance(ins, ir.VectorStore)]
        self.assertEqual(8, len(loads))
        self.assertEqual(4, len(stores))
        self.assertIs(a_next, loads[2].addr)
        self.assertIs(b_next, loads[3].addr)
        self.assertIs(loads[4].addr, loads[6].addr.a)
        self.assertIs(c_next, stores[1].addr)
        self.assertIs(c_next, stores[2].addr.a)
        vector_add = next(
            ins
            for ins in latch
            if isinstance(ins, ir.Binop) and isinstance(ins.ty, ir.VectorTyp)
        )
        for load in loads:
            self.assertLess(load.position, vector_add.position)
        self.assertIsNot(i_next, i.get_value(latch))
        self.assertIsNot(a_next, a.get_value(latch))
        verify_module(self.module)

        self.assert_unchanged()


class LoopUnrollForLoopTestCase(unittest.TestCase):
    """Unroll atalla_tests/forloop.c after mem2reg."""

    def test_forloop(self):
        filename = os.path.join(
            os.path.dirname(__file__), "..", "atalla_tests", "forloop.c"
        )
        with open(filename) as f:
            module = atalla_c_to_ir(f, "atalla")
        DeleteUnusedInstructionsPass().run(module)
        Mem2RegPromotor().run(module)
        DeleteUnusedInstructionsPass().run(module)
        expected = run_function(module, "main")

        # i < 10 is ten trips, not a multiple of four, so the loop stays.
        before = module_text(module)
        LoopUnrollPass().run(module)
        verify_module(module)
        self.assertEqual(before, module_text(module))
        self.assertEqual(50, expected)
        self.assertEqual(expected, run_function(module, "main"))


if __name__ == "__main__":
    unittest.main()
