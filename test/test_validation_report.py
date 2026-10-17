import unittest

from ci.validation_report import render


class ValidationReportTestCase(unittest.TestCase):
    def test_handwritten_failure_fails_accuracy_gate(self):
        unit = [{"test": "unit", "status": "pass", "error": None}]
        kernel = [{"test": "kernel", "status": "pass", "error": None,
                   "handwritten": {"status": "fail", "error": "wrong result"}}]
        self.assertIn("Accuracy gate: FAILED", render(unit, kernel))

    def test_report_separates_branch_expansion_from_original_instructions(self):
        results = [{"test": "kernel", "status": "pass", "error": None}]
        report = render(results, results)
        self.assertIn("Accuracy gate: PASSED", report)
        self.assertIn("Branch-expansion instructions (C / HW)", report)
