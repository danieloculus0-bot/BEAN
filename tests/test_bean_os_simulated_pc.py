"""Acceptance checks for the BEAN-owned simulated PC loop."""
import tempfile
import unittest
from pathlib import Path

from experiments.bean_os.simulated_pc import pc_case, simulate_action, run


class SimulatedPCTest(unittest.TestCase):
    def test_effectors_change_only_disposable_state(self):
        before = pc_case("50100")
        outcome = simulate_action("50100", -1)
        self.assertGreater(outcome["reward"], 0)
        self.assertLess(outcome["after"]["disk_pressure"], before["disk_pressure"])
        self.assertEqual(before, pc_case("50100"))

    def test_real_core_learns_and_reopens_receipt(self):
        with tempfile.TemporaryDirectory() as directory:
            result = run(Path(directory) / "reasoning.sqlite3")
        self.assertTrue(result["real_bean_core"])
        self.assertFalse(result["external_model_used"])
        self.assertEqual(result["blind_cases"], 60)
        self.assertGreaterEqual(result["blind_coverage"], 0.8)
        self.assertGreaterEqual(result["blind_optimal_rate"], 0.8)
        self.assertEqual(len(result["cases"]), 60)


if __name__ == "__main__":
    unittest.main()
