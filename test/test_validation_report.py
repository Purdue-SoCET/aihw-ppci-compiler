import unittest
from ci.validation_report import fmt_diff, render


class ValidationReportTestCase(unittest.TestCase):
    def test_fmt_diff_noise_deadband(self):
        # Exact zero
        self.assertEqual(fmt_diff(100, 100), "0 (unchanged)")

        # Within 1.0% and <= 2 cycles (should be parity within noise, not regressed)
        res_plus_1 = fmt_diff(101, 100)
        self.assertIn("parity (within noise)", res_plus_1)
        self.assertNotIn("[REGRESSED]", res_plus_1)

        res_plus_2 = fmt_diff(102, 100)
        self.assertIn("parity (within noise)", res_plus_2)
        self.assertNotIn("[REGRESSED]", res_plus_2)

        # Regressed beyond noise deadband (> 1.0% and > 2 units)
        res_regressed = fmt_diff(110, 100)
        self.assertIn("[REGRESSED]", res_regressed)
        self.assertNotIn("parity", res_regressed)

        # Improved (lower is better)
        res_improved = fmt_diff(90, 100)
        self.assertIn("[IMPROVED]", res_improved)

    def test_spill_alert_banner(self):
        kernel_clean = [
            {
                "test": "k1",
                "status": "pass",
                "perf": {"packets_executed": 100},
                "stack": {"loop_spills": 0},
            }
        ]
        report_clean = render(unit=[], kernel=kernel_clean)
        self.assertNotIn("Stack Spilling Detected", report_clean)

        kernel_spills = [
            {
                "test": "k1",
                "status": "pass",
                "perf": {"packets_executed": 100},
                "stack": {"loop_spills": 3},
            }
        ]
        report_spills = render(unit=[], kernel=kernel_spills)
        self.assertIn("> [!WARNING]", report_spills)
        self.assertIn("Stack Spilling Detected", report_spills)

    def test_macro_regression_alert_banner(self):
        curr = [
            {
                "test": "k1",
                "status": "pass",
                "perf": {"packets_executed": 110},
                "stack": {"loop_spills": 0},
            }
        ]
        macro = [
            {
                "test": "k1",
                "status": "pass",
                "perf": {"packets_executed": 100},
                "stack": {"loop_spills": 0},
            }
        ]
        # 110 vs 100 is +10% regression (> 3%)
        report = render(unit=[], kernel=curr, macro_baseline=macro)
        self.assertIn("> [!WARNING]", report)
        self.assertIn("Performance Regression Detected", report)

    def test_dual_baseline_rendering(self):
        curr = [
            {
                "test": "k1",
                "status": "pass",
                "perf": {
                    "packets_executed": 95,
                    "instructions_executed": 120,
                    "packet_slot_utilization_executed_pct": 45.0,
                    "dyn_retired_scalar_mem": 0,
                },
                "stack": {"loop_spills": 0},
            }
        ]
        macro = [
            {
                "test": "k1",
                "status": "pass",
                "perf": {
                    "packets_executed": 100,
                    "instructions_executed": 130,
                    "packet_slot_utilization_executed_pct": 40.0,
                    "dyn_retired_scalar_mem": 0,
                },
                "stack": {"loop_spills": 0},
            }
        ]
        micro = [
            {
                "test": "k1",
                "status": "pass",
                "perf": {
                    "packets_executed": 98,
                    "instructions_executed": 125,
                    "packet_slot_utilization_executed_pct": 42.0,
                    "dyn_retired_scalar_mem": 0,
                },
                "stack": {"loop_spills": 0},
            }
        ]
        c_git = {"branch": "feature", "commit": "11111111", "message": "feat"}
        macro_git = {"branch": "atalla-arch", "commit": "00000000", "message": "macro"}
        micro_git = {"branch": "feature", "commit": "22222222", "message": "prev"}

        report = render(
            unit=[],
            kernel=curr,
            macro_baseline=macro,
            micro_baseline=micro,
            current_git=c_git,
            macro_git=macro_git,
            micro_git=micro_git,
        )
        self.assertIn("vs atalla-arch", report)
        self.assertIn("vs Last Commit", report)
        self.assertIn("Summary vs atalla-arch", report)
        self.assertIn("Summary vs Last Commit", report)


if __name__ == "__main__":
    unittest.main()
