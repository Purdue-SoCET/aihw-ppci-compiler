import unittest

from ppci.arch.generic_instructions import ArtificialInstruction
from ppci.arch.atalla.instructions import Addis, Lis, Luis, materialize_i32
from ppci.arch.atalla.registers import LR


class AtallaImmediateTestCase(unittest.TestCase):
    def test_materialize_i32_boundaries(self):
        values = (
            0,
            1,
            -1,
            (1 << 24) - 1,
            1 << 24,
            (1 << 25) - 1,
            1 << 25,
            0x7FFFFFFF,
            0x80000000,
            0xFFFFFFFF,
        )

        for value in values:
            with self.subTest(value=value):
                upper, lower = materialize_i32(LR, value)
                self.assertIsInstance(upper, Luis)
                self.assertIsInstance(lower, Addis)
                self.assertEqual(
                    value & 0xFFFFFFFF,
                    ((upper.imm25 << 7) + lower.imm12) & 0xFFFFFFFF,
                )
                self.assertLessEqual(upper.imm25.bit_length(), 25)
                self.assertIn(lower.imm12, range(1 << 7))

    def test_li_is_a_pseudo_instruction(self):
        pseudo = Lis(LR, -1)
        self.assertIsInstance(pseudo, ArtificialInstruction)
        self.assertEqual([Luis, Addis], [type(inst) for inst in pseudo.render()])


if __name__ == "__main__":
    unittest.main()
