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

    def test_blind_scenarios_keep_realistic_pressure_ranges(self):
        # Numeric case IDs distinguish withheld observations; they must not
        # inflate resource pressure and silently change the simulated task.
        for i in list(range(100, 160)) + list(range(1000, 1012)) + list(range(50000, 50060)):
            state = pc_case(str(i))
            expected = -1 if i % 3 == 0 else 1 if i % 3 == 1 else 0
            self.assertLessEqual(state["disk_pressure"], 100)
            self.assertLessEqual(state["service_fault"], 100)
            rewards = {a: simulate_action(str(i), a)["reward"]
                       for a in (-1, 0, 1)}
            self.assertEqual(expected, max(rewards, key=rewards.get))

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
