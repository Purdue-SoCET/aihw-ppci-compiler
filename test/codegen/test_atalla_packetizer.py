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

    def test_far_branch_layout_preserves_both_paths_and_original_packets(self):
        from ppci.arch.atalla.branch_layout import relax_branches
        from ppci.arch.atalla.instructions import Beqs, Bnes, Blts, Bges, Bgts, Bles, Jal

        def packet(ins):
            return [ins, Nop(), Nop(), Nop()]

        inverses = {Beqs: Bnes, Bnes: Beqs, Blts: Bges, Bges: Blts,
                    Bgts: Bles, Bles: Bgts}
        for branch, inverse in inverses.items():
            for backward in (False, True):
                with self.subTest(branch=branch, backward=backward):
                    middle = sum((packet(Addis(R3, R3, 1)) for _ in range(130)), [])
                    conditional = branch(R3, R4, "target")
                    source = ([Label("target")] + middle + packet(conditional)
                              if backward else packet(conditional) + middle + [Label("target")])
                    source += packet(Halt())
                    result, added = relax_branches(source, Nop)
                    self.assertEqual(1, added)
                    real = [ins for ins in result if not isinstance(ins, Label)]
                    index = next(i for i, ins in enumerate(real) if type(ins) is inverse)
                    labels = {}
                    pc = 0
                    for ins in result:
                        if isinstance(ins, Label):
                            labels[ins.name] = pc
                        else:
                            pc += 1
                    # False original condition skips the JAL; true reaches the
                    # original target. Both controls remain solo 20-byte packets.
                    self.assertEqual(index + 8, labels[real[index].imm10])
                    self.assertIsInstance(real[index + 4], Jal)
                    self.assertEqual("target", real[index + 4].imm25)
                    self.assertTrue(all(isinstance(ins, Nop) for ins in real[index + 1:index + 4]))
                    self.assertEqual(middle, real[:index] if backward else real[index + 8:-4])
                    self.assertEqual((result, 0), relax_branches(result, Nop))

    def test_branch_layout_rechecks_branches_after_insertions(self):
        from ppci.arch.atalla.branch_layout import relax_branches
        from ppci.arch.atalla.instructions import Beqs, Bnes

        def packet(ins):
            return [ins, Nop(), Nop(), Nop()]

        filler = lambda n: sum((packet(Addis(R3, R3, 1)) for _ in range(n)), [])
        source = (packet(Beqs(R3, R4, "near")) + packet(Bnes(R3, R4, "far"))
                  + filler(125) + [Label("near")] + filler(130)
                  + [Label("far")] + packet(Halt()))
        result, added = relax_branches(source, Nop)
        self.assertEqual(2, added)  # Second insertion pushes the first branch past +511.
        self.assertEqual((result, 0), relax_branches(result, Nop))

    def test_packetizer_accounts_for_branch_expansion_separately(self):
        from ppci.arch.atalla.instructions import Beqs

        source = ([Beqs(R3, R4, "far")]
                  + [Addis(R3, R3, 1) for _ in range(130)] + [Label("far"), Halt()])
        self.code_generator._pack_flat_vliw(source)
        self.assertEqual(132, self.code_generator.packetization_stats["instructions_before_packetization"])
        self.assertEqual(1, self.code_generator.packetization_stats["branch_lowering_instructions"])

    def test_short_branches_are_unchanged(self):
        from ppci.arch.atalla.instructions import Beqs

        branch = Beqs(R3, R4, "near")
        result = self.code_generator._pack_flat_vliw(
            [branch] + [Addis(R3, R3, 1) for _ in range(126)] + [Label("near"), Halt()])
        self.assertIs(result[0], branch)  # +508 instruction words still fits BR10.
        self.assertNotIn("branch_lowering_instructions", self.code_generator.packetization_stats)

    def test_cleanup_inversion_then_latency_growth_preserves_control_flow(self):
        from ppci.arch.atalla.instructions import Beqs, Bnes, Jal

        branch = Beqs(R3, R4, "body")
        jump = Jal(R0, "exit")
        source = ([branch, jump, Label("body")]
                  + [Muls(R3, R3, R4) for _ in range(45)] + [Label("exit"), Halt()])
        cleaned = self.code_generator.arch._branch_cleanup(source, set())
        self.assertIsInstance(cleaned[0], Bnes)
        self.assertNotIn(jump, cleaned)
        result = self.code_generator._pack_flat_vliw(cleaned)
        # Cleanup's inversion survives semantically: equality enters the body;
        # inequality uses a long jump to exit. Cleanup is not rerun afterwards.
        self.assertIsInstance(result[0], Beqs)
        self.assertIsInstance(result[4], Jal)
        self.assertEqual("exit", result[4].imm25)
        self.assertEqual(result[0].imm10, result[8].name)
        self.assertEqual("body", result[9].name)


if __name__ == "__main__":
    unittest.main()
