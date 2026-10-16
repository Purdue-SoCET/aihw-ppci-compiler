import unittest

from ppci.arch.generic_instructions import ArtificialInstruction
from ppci.arch.atalla.instructions import Addis, Lis, Luis, materialize_i32
from ppci.arch.atalla.registers import LR, R0


class AtallaImmediateTestCase(unittest.TestCase):
    def test_materialize_i32_boundaries(self):
        cases = (
            (0, [Luis]),
            (1, [Addis]),
            (-1, [Addis]),
            (2047, [Addis]),
            (2048, [Luis]),
            (2049, [Luis, Addis]),
            (-2048, [Luis]),
            (-2047, [Addis]),
            ((1 << 24) - 1, [Luis, Addis]),
            (1 << 24, [Luis]),
            ((1 << 25) - 1, [Luis, Addis]),
            (1 << 25, [Luis]),
            (0x7FFFFFFF, [Luis, Addis]),
            (0x80000000, [Luis]),
            (0xFFFFFFFF, [Addis]),
        )

        for value, expected_types in cases:
            with self.subTest(value=value):
                instructions = materialize_i32(LR, value)
                self.assertEqual(expected_types, [type(inst) for inst in instructions])

                result = 0
                for instruction in instructions:
                    if isinstance(instruction, Luis):
                        self.assertLessEqual(instruction.imm25.bit_length(), 25)
                        result = instruction.imm25 << 7
                    else:
                        self.assertIsInstance(instruction, Addis)
                        base = 0 if instruction.rs1 is R0 else result
                        result = base + instruction.imm12
                self.assertEqual(value & 0xFFFFFFFF, result & 0xFFFFFFFF)

    def test_li_is_a_pseudo_instruction(self):
        pseudo = Lis(LR, -1)
        self.assertIsInstance(pseudo, ArtificialInstruction)
        self.assertEqual([Addis], [type(inst) for inst in pseudo.render()])


if __name__ == "__main__":
    unittest.main()
