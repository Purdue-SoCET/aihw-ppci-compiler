import unittest

from ppci.api import get_arch
from ppci.arch.atalla.instructions import Addis, Adds, Halt, Lis, Muls, Nop
from ppci.arch.atalla.mask_registers import M0
from ppci.arch.atalla.registers import FP, LR, R0, R3, R4, R7, R9, R10
from ppci.arch.atalla.vector_instructions import AddVv
from ppci.arch.atalla.vector_registers import V1, V2, V3
from ppci.codegen.codegen import CodeGenerator
from ppci.arch.generic_instructions import Alignment, Label, SectionInstruction
from ppci.utils.reporting import DummyReportGenerator


class AtallaPacketizerTestCase(unittest.TestCase):
    def setUp(self):
        self.code_generator = CodeGenerator(
            get_arch("atalla"), DummyReportGenerator(), packetize=True
        )

    def test_halt_is_isolated_after_prior_instructions(self):
        packed = self.code_generator._pack_flat_vliw([Lis(LR, 1), Halt()])

        self.assertEqual(8, len(packed))
        self.assertIsInstance(packed[0], Addis)
        self.assertTrue(all(isinstance(ins, Nop) for ins in packed[1:4]))
        self.assertIsInstance(packed[4], Halt)
        self.assertTrue(all(isinstance(ins, Nop) for ins in packed[5:8]))

    def test_register_files_with_the_same_number_do_not_conflict(self):
        scalar = Addis(LR, R0, 1)
        vector = AddVv(V2, V1, V3, M0)

        packed = self.code_generator._pack_flat_vliw([scalar, vector])

        self.assertEqual([scalar, vector], packed[:2])

    def test_writer_waits_for_every_prior_reader(self):
        producer = Muls(R7, R3, R4)
        delayed_reader = Adds(FP, LR, R7)
        later_reader = Muls(R9, LR, R10)
        writer = Addis(LR, R0, 0)

        packed = self.code_generator._pack_flat_vliw(
            [producer, delayed_reader, later_reader, writer]
        )
        issued = [
            instruction
            for instruction in packed
            if not isinstance(instruction, Nop)
        ]

        self.assertLess(issued.index(delayed_reader), issued.index(writer))
        self.assertLess(issued.index(later_reader), issued.index(writer))

    def test_counts_exclude_padding_and_directives(self):
        packed = self.code_generator._pack_flat_vliw([
            Alignment(5), Label("entry"), Nop(), Lis(LR, 1), Halt(),
            SectionInstruction("data"),
        ])

        self.assertIsInstance(packed[0], Alignment)
        self.assertIsInstance(packed[-1], SectionInstruction)
        self.assertEqual(self.code_generator.packetization_stats, {
            "instructions_before_packetization": 2, "packets": 2, "nop_packets": 0,
        })

    def test_large_immediate_expands_before_counting_and_scheduling(self):
        from ppci.arch.atalla.instructions import Addis, Luis

        packed = self.code_generator._pack_flat_vliw([Lis(LR, 133169183), Halt()])
        real = [ins for ins in packed if not isinstance(ins, Nop)]
        self.assertEqual([Luis, Addis, Halt], [type(ins) for ins in real])
        self.assertEqual(3, self.code_generator.packetization_stats[
            "instructions_before_packetization"
        ])


if __name__ == "__main__":
    unittest.main()
