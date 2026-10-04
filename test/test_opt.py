"""
Optimalization tests.
"""

import io
import sys
import unittest

from ppci import ir, irutils
from ppci.binutils.debuginfo import DebugDb
from ppci.irutils import verify_module
from ppci.opt import CleanPass, Mem2RegPromotor
from ppci.opt.constantfolding import correct
from ppci.opt.tailcall import TailCallOptimization


class OptTestCase(unittest.TestCase):
    """Base testcase that prepares a module, builder and verifier"""

    def setUp(self):
        self.debug_db = DebugDb()
        self.builder = irutils.Builder()
        self.module = ir.Module("test", debug_db=self.debug_db)
        self.builder.set_module(self.module)
        self.function = self.builder.new_procedure(
            "testfunction", ir.Binding.GLOBAL
        )
        self.builder.set_function(self.function)
        entry = self.builder.new_block()
        self.function.entry = entry
        self.builder.set_block(entry)

    def dump(self):
        iof = io.StringIO()
        writer = irutils.Writer(iof)
        writer.write(self.module)
        print(iof.getvalue())

    def tearDown(self):
        verify_module(self.module)


class CleanTestCase(OptTestCase):
    """Test the clean pass for correct function"""

    def setUp(self):
        super().setUp()
        self.clean_pass = CleanPass()

    def test_glue_blocks(self):
        epilog = self.builder.new_block()
        self.builder.emit(ir.Jump(epilog))
        self.builder.set_block(epilog)
        self.builder.emit(ir.Exit())

    def test_glue_with_phi(self):
        """
        After replacing the predecessor, the use info of a phi is messed
        up.
        """
        block1 = self.builder.new_block()
        block4 = self.builder.new_block()  # This one must be eliminated
        block6 = self.builder.new_block()
        self.builder.emit(ir.Jump(block1))
        self.builder.set_block(block1)
        cnst = self.builder.emit(ir.Const(0, "const", ir.i16))
        self.builder.emit(ir.Jump(block4))
        self.builder.set_block(block4)
        self.builder.emit(ir.Jump(block6))
        self.builder.set_block(block6)
        phi = self.builder.emit(ir.Phi("res24", ir.i16))
        phi.set_incoming(block4, cnst)
        cnst2 = self.builder.emit(ir.Const(2, "cnst2", ir.i16))
        binop = self.builder.emit(ir.add(phi, cnst2, "binop", ir.i16))
        phi.set_incoming(block6, binop)
        self.builder.emit(ir.Jump(block6))
        verify_module(self.module)

        # Act:
        self.clean_pass.run(self.module)
        self.assertNotIn(block4, self.function)


class Mem2RegTestCase(OptTestCase):
    """Test the memory to register lifter"""

    def setUp(self):
        super().setUp()
        self.mem2reg = Mem2RegPromotor()

    def test_normal_use(self):
        alloc = self.builder.emit(ir.Alloc("A", 4, 4))
        addr = self.builder.emit(ir.AddressOf(alloc, "addr"))
        cnst = self.builder.emit(ir.Const(1, "cnst", ir.i32))
        self.builder.emit(ir.Store(cnst, addr))
        self.builder.emit(ir.Load(addr, "Ld", ir.i32))
        self.builder.emit(ir.Exit())
        self.mem2reg.run(self.module)
        self.assertNotIn(alloc, self.function.entry.instructions)

    def test_byte_lift(self):
        """Test byte data type to work"""
        alloc = self.builder.emit(ir.Alloc("A", 1, 1))
        addr = self.builder.emit(ir.AddressOf(alloc, "addr"))
        cnst = self.builder.emit(ir.Const(1, "cnst", ir.i8))
        self.builder.emit(ir.Store(cnst, addr))
        self.builder.emit(ir.Load(addr, "Ld", ir.i8))
        self.builder.emit(ir.Exit())
        self.mem2reg.run(self.module)
        self.assertNotIn(alloc, self.function.entry.instructions)

    def test_volatile_not_lifted(self):
        """Volatile allocs must persist"""
        alloc = self.builder.emit(ir.Alloc("A", 1, 1))
        addr = self.builder.emit(ir.AddressOf(alloc, "addr"))
        cnst = self.builder.emit(ir.Const(1, "cnst", ir.i8))
        self.builder.emit(ir.Store(cnst, addr))
        self.builder.emit(ir.Load(addr, "Ld", ir.i8, volatile=True))
        self.builder.emit(ir.Exit())
        self.mem2reg.run(self.module)
        self.assertIn(alloc, self.function.entry.instructions)

    def test_different_type_not_lifted(self):
        """different types must persist"""
        alloc = self.builder.emit(ir.Alloc("A", 1, 1))
        addr = self.builder.emit(ir.AddressOf(alloc, "addr"))
        cnst = self.builder.emit(ir.Const(1, "cnst", ir.i32))
        self.builder.emit(ir.Store(cnst, addr))
        self.builder.emit(ir.Load(addr, "Ld", ir.i8))
        self.builder.emit(ir.Exit())
        self.mem2reg.run(self.module)
        self.assertIn(alloc, self.function.entry.instructions)

    def test_store_uses_alloc_as_value(self):
        """When only stores and loads use the alloc, the store can use the
        alloc as a value. In this case, the store must remain"""
        alloc = self.builder.emit(ir.Alloc("A", 4, 4))
        addr = self.builder.emit(ir.AddressOf(alloc, "addr"))
        self.builder.emit(ir.Store(addr, addr))
        self.builder.emit(ir.Exit())
        self.mem2reg.run(self.module)
        self.assertIn(alloc, self.function.entry.instructions)


class TypedEvalTestCase(unittest.TestCase):
    """Test various integer values wrapped at bitsizes and signedness"""

    def test_char_overflow(self):
        self.assertEqual(9, correct(9, ir.i8))
        self.assertEqual(-128, correct(127 + 1, ir.i8))
        self.assertEqual(127, correct(-128 - 1, ir.i8))
        self.assertEqual(-125, correct(4 + 127, ir.i8))

    def test_byte_overflow(self):
        self.assertEqual(8, correct(9 + 255, ir.u8))
        self.assertEqual(254, correct(-2, ir.u8))

    def test_u16_overflow(self):
        self.assertEqual(1, correct(2 + 65535, ir.u16))
        self.assertEqual(65534, correct(-2, ir.u16))
        self.assertEqual(1, correct(2 + 65535 + 65536 * 3, ir.u16))

    def test_i16_overflow(self):
        self.assertEqual(-32767, correct(2 + 32767, ir.i16))
        self.assertEqual(32766, correct(-32767 - 3, ir.i16))


class TailCallTestCase(unittest.TestCase):
    """Test the tail call optimization"""

    def setUp(self):
        self.opt = TailCallOptimization()

    def test_function_tailcall(self):
        """Test if a tailcall in a function works out nicely"""
        # Prepare an optimizable module:
        builder = irutils.Builder()
        module = ir.Module("test")
        builder.set_module(module)
        function = builder.new_function("x", ir.Binding.GLOBAL, ir.i8)
        builder.set_function(function)
        entry = builder.new_block()
        function.entry = entry
        a = ir.Parameter("a", ir.i8)
        function.add_parameter(a)
        b = ir.Parameter("b", ir.i8)
        function.add_parameter(b)
        builder.set_block(entry)
        one = builder.emit(ir.Const(1, "const", ir.i8))
        a2 = builder.emit(ir.add(a, one, "a2", ir.i8))
        b2 = builder.emit(ir.add(b, one, "b2", ir.i8))
        result = builder.emit(ir.FunctionCall(function, [a2, b2], "rv", ir.i8))
        builder.emit(ir.Return(result))

        # Verify first version:
        module.display()
        verify_module(module)
        self.assertFalse(function.is_leaf())

        # Run optimizer:
        self.opt.run(module)

        # Verify again:
        module.display()
        verify_module(module)
        self.assertTrue(function.is_leaf())


from ppci.opt.licm import LoopInvariantCodeMotionPass


class LicmTestCase(unittest.TestCase):
    """Test Loop Invariant Code Motion (LICM) pass."""

    def test_licm_hoist_binary_op(self):
        builder = irutils.Builder()
        module = ir.Module("test_licm")
        builder.set_module(module)
        function = builder.new_function("test_func", ir.Binding.GLOBAL, ir.i32)
        builder.set_function(function)
        entry = builder.new_block("entry")
        function.entry = entry
        a = ir.Parameter("a", ir.i32)
        b = ir.Parameter("b", ir.i32)
        function.add_parameter(a)
        function.add_parameter(b)

        header = builder.new_block("header")
        body = builder.new_block("body")
        exit_block = builder.new_block("exit")

        builder.set_block(entry)
        zero = builder.emit(ir.Const(0, "zero", ir.i32))
        builder.emit(ir.Jump(header))

        builder.set_block(header)
        phi_i = builder.emit(ir.Phi("i", ir.i32))
        ten = builder.emit(ir.Const(10, "ten", ir.i32))
        builder.emit(ir.CJump(phi_i, "<", ten, body, exit_block))

        builder.set_block(body)
        # Loop-invariant calculation: a * b
        inv = builder.emit(ir.Binop(a, "*", b, "inv", ir.i32))
        one = builder.emit(ir.Const(1, "one", ir.i32))
        next_i = builder.emit(ir.Binop(phi_i, "+", one, "next_i", ir.i32))
        builder.emit(ir.Jump(header))

        phi_i.set_incoming(entry, zero)
        phi_i.set_incoming(body, next_i)

        builder.set_block(exit_block)
        builder.emit(ir.Return(phi_i))

        verify_module(module)

        # Before LICM, 'inv' is in body
        self.assertIn(inv, body.instructions)
        self.assertNotIn(inv, entry.instructions)

        # Run LICM
        licm = LoopInvariantCodeMotionPass()
        licm.run(module)
        verify_module(module)

        # After LICM, 'inv' must be hoisted to entry (preheader)
        self.assertNotIn(inv, body.instructions)
        self.assertIn(inv, entry.instructions)


from ppci.opt.load_after_store import LoadAfterStorePass


class LoadAfterStoreTestCase(unittest.TestCase):
    """Test LoadAfterStorePass optimizations."""

    def test_load_first_instruction_store(self):
        """Test off-by-one fix when store is at index 0 of the block."""
        builder = irutils.Builder()
        module = ir.Module("test_las")
        builder.set_module(module)
        func = builder.new_function("func", ir.Binding.GLOBAL, ir.i32)
        builder.set_function(func)
        entry = builder.new_block("entry")
        func.entry = entry
        ptr = ir.Parameter("ptr", ir.ptr)
        val = ir.Parameter("val", ir.i32)
        func.add_parameter(ptr)
        func.add_parameter(val)

        builder.set_block(entry)
        # Store is first instruction at index 0 of the block
        st = builder.emit(ir.Store(val, ptr))
        ld = builder.emit(ir.Load(ptr, "loaded", ir.i32))
        ret = builder.emit(ir.Return(ld))

        verify_module(module)
        self.assertEqual(ret.result, ld)

        pas = LoadAfterStorePass()
        pas.run(module)
        verify_module(module)

        # ld uses should be replaced by val
        self.assertEqual(ret.result, val)
        self.assertEqual(len(ld.used_by), 0)

    def test_redundant_load_elimination(self):
        """Test CSE for consecutive loads from the same address."""
        builder = irutils.Builder()
        module = ir.Module("test_rle")
        builder.set_module(module)
        func = builder.new_function("func", ir.Binding.GLOBAL, ir.i32)
        builder.set_function(func)
        entry = builder.new_block("entry")
        func.entry = entry
        ptr = ir.Parameter("ptr", ir.ptr)
        func.add_parameter(ptr)

        builder.set_block(entry)
        ld1 = builder.emit(ir.Load(ptr, "ld1", ir.i32))
        dummy = builder.emit(ir.Binop(ld1, "+", ld1, "dummy", ir.i32))
        ld2 = builder.emit(ir.Load(ptr, "ld2", ir.i32))
        ret = builder.emit(ir.Binop(dummy, "+", ld2, "ret", ir.i32))
        builder.emit(ir.Return(ret))

        verify_module(module)
        self.assertEqual(ret.b, ld2)

        pas = LoadAfterStorePass()
        pas.run(module)
        verify_module(module)

        # ld2 should be replaced by ld1
        self.assertEqual(ret.b, ld1)
        self.assertEqual(len(ld2.used_by), 0)


if __name__ == "__main__":
    unittest.main()
    sys.exit()
