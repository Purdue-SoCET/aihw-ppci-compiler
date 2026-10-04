import unittest

from ppci.api import get_arch
from ppci.arch.atalla.instructions import Halt, Lis, Nop
from ppci.arch.atalla.registers import LR
from ppci.codegen.codegen import CodeGenerator
from ppci.utils.reporting import DummyReportGenerator


class AtallaPacketizerTestCase(unittest.TestCase):
    def test_halt_is_isolated_after_prior_instructions(self):
        code_generator = CodeGenerator(
            get_arch("atalla"), DummyReportGenerator(), packetize=True
        )

        packed = code_generator._pack_flat_vliw([Lis(LR, 1), Halt()])

        self.assertEqual(8, len(packed))
        self.assertIsInstance(packed[0], Lis)
        self.assertTrue(all(isinstance(ins, Nop) for ins in packed[1:4]))
        self.assertIsInstance(packed[4], Halt)
        self.assertTrue(all(isinstance(ins, Nop) for ins in packed[5:8]))


if __name__ == "__main__":
    unittest.main()
