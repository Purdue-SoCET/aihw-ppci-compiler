import io
import unittest

from ppci import ir, irutils
from ppci.binutils.debuginfo import DebugDb
from ppci.opt import ConstantFolder

from .helper_util import test_path


class IrCodeTestCase(unittest.TestCase):
    def test_add(self):
        """See if the ir classes can be constructed"""
        v1 = ir.Const(1, "const", ir.i32)
        v2 = ir.Const(2, "const", ir.i32)
        ir.add(v1, v2, "add", ir.i32)

    def test_use(self):
        """Check if use def information is correctly administered"""
        c1 = ir.Const(1, "one", ir.i32)
        c2 = ir.Const(2, "two", ir.i32)
        c3 = ir.Const(3, "three", ir.i32)
        c4 = ir.Const(4, "four", ir.i32)
        add = ir.add(c1, c2, "add", ir.i32)
        self.assertEqual({c1, c2}, add.uses)

        # Replace usage by setting the variable:
        add.a = c3
        self.assertEqual({c3, c2}, add.uses)

        # Replace use by changing value:
        add.replace_use(c2, c4)
        self.assertEqual({c3, c4}, add.uses)
        self.assertEqual(c4, add.b)

    def test_inline_asm_replace_use(self):
        """Inline asm rewrites inputs and address outputs, not results."""
        old = ir.Const(1, "old", ir.ptr)
        new = ir.Const(2, "new", ir.ptr)
        result = ir.InlineAsmResult("result", ir.i32)
        replacement_result = ir.InlineAsmResult("replacement", ir.i32)
        inline_asm = ir.InlineAsm("test %0, %1", [])

        # Use the same value in multiple places to verify that the def-use set
        # is updated once while every operand occurrence is replaced.
        inline_asm.add_input_variable(old)
        inline_asm.add_input_variable(old)
        inline_asm.add_output_variable(old)
        inline_asm.add_output_result(result)

        inline_asm.replace_use(old, new)

        self.assertEqual([new, new], inline_asm.input_values)
        self.assertEqual(
            [("address", new), ("result", result)],
            inline_asm.output_operands,
        )
        self.assertEqual({new}, inline_asm.uses)
        self.assertNotIn(inline_asm, old.used_by)
        self.assertIn(inline_asm, new.used_by)

        # Results are definitions of the inline asm, not its uses.
        inline_asm.replace_use(result, replacement_result)
        self.assertEqual(
            [("address", new), ("result", result)],
            inline_asm.output_operands,
        )


class IrBuilderTestCase(unittest.TestCase):
    def setUp(self):
        self.b = irutils.Builder()
        self.m = ir.Module("test")
        self.b.set_module(self.m)

    def test_builder(self):
        f = self.b.new_procedure("add", ir.Binding.GLOBAL)
        self.b.set_function(f)
        entry = self.b.new_block()
        f.entry = entry
        self.b.set_block(entry)
        bb = self.b.new_block()
        self.b.emit(ir.Jump(bb))
        self.b.set_block(bb)
        self.b.emit(ir.Const(0, "const", ir.i32))
        self.b.emit(ir.Exit())
        # Run interpreter:
        # r = self.m.getFunction('add').call(1, 2)
        # self.assertEqual(3, r)


class ConstantFolderTestCase(unittest.TestCase):
    def setUp(self):
        self.b = irutils.Builder()
        debug_db = DebugDb()
        self.cf = ConstantFolder()
        self.m = ir.Module("test", debug_db=debug_db)
        self.b.set_module(self.m)

    def test_builder(self):
        f = self.b.new_procedure("test", ir.Binding.GLOBAL)
        self.b.set_function(f)
        entry = self.b.new_block()
        f.entry = entry
        self.b.set_block(entry)
        bb = self.b.new_block()
        self.b.emit(ir.Jump(bb))
        self.b.set_block(bb)
        v1 = self.b.emit(ir.Const(5, "const", ir.i32))
        v2 = self.b.emit(ir.Const(7, "const", ir.i32))
        self.b.emit(ir.add(v1, v2, "add", ir.i32))
        self.b.emit(ir.Exit())
        self.cf.run(self.m)

    def test_add0(self):
        f = self.b.new_procedure("test", ir.Binding.GLOBAL)
        self.b.set_function(f)
        self.b.set_block(self.b.new_block())
        v1 = ir.Const(12, "const", ir.i32)
        self.b.emit(v1)
        v2 = ir.Const(0, "const", ir.i32)
        self.b.emit(v2)
        v3 = ir.add(v1, v2, "add", ir.i32)
        self.b.emit(v3)


class TestWriter(unittest.TestCase):
    def test_write(self):
        module = ir.Module("mod1")
        function = ir.Procedure("func1", ir.Binding.GLOBAL)
        module.add_function(function)
        entry = ir.Block("entry")
        function.add_block(entry)
        function.entry = entry
        entry.add_instruction(ir.Exit())
        f = io.StringIO()
        writer = irutils.Writer(file=f)
        writer.write(module)
        # print(f.getvalue())
        f2 = io.StringIO(f.getvalue())
        reader = irutils.Reader()
        module2 = reader.read(f2)
        f3 = io.StringIO()
        writer = irutils.Writer(file=f3)
        writer.write(module2)
        self.assertEqual(f3.getvalue(), f.getvalue())


class TestReader(unittest.TestCase):
    def test_add_example(self):
        sample = test_path / "data" / "add.pi"
        with sample.open() as f:
            m = irutils.read_module(f)
            self.assertTrue(m)


class TestIrToPython(unittest.TestCase):
    def test_add_example(self):
        reader = irutils.Reader()
        sample = test_path / "data" / "add.pi"
        with sample.open() as f:
            reader.read(f)


if __name__ == "__main__":
    unittest.main()
