"""BEAN OS isolated desktop tests: state, interaction, retention, evaluation."""
import tempfile
import unittest
from pathlib import Path

from experiments.bean_os.virtual_desktop import (
    EPISODES, FAMILIES, OPERATIONS, VirtualDesktop,
    episode_conditions, run, training_environment,
)


class VirtualDesktopTest(unittest.TestCase):
    def test_all_registered_repairs_change_only_simulated_state(self):
        for family in FAMILIES:
            for fault in (-1, 1):
                conditions = {group: 0 for group in FAMILIES}
                conditions[family] = fault
                machine = VirtualDesktop(conditions, identity=2026)
                before = machine.inspect(family)
                self.assertFalse(machine.complete())
                result = machine.apply(family, fault)
                self.assertTrue(result["changed"], (family, fault))
                self.assertFalse(result["unnecessary"])
                self.assertNotEqual(before, result["post_observation"])
                self.assertTrue(machine.complete())
                self.assertEqual(OPERATIONS[family][fault], result["operation"])

    def test_wrong_repair_does_not_count_as_success(self):
        conditions = {family: 0 for family in FAMILIES}
        conditions["network"] = -1
        machine = VirtualDesktop(conditions, identity=42)
        outcome = machine.apply("network", 1)
        self.assertTrue(outcome["unnecessary"])
        self.assertEqual(-0.25, outcome["reward"])
        self.assertFalse(machine.complete())

    def test_healthy_state_is_not_improved_by_any_repair(self):
        machine = VirtualDesktop({family: 0 for family in FAMILIES}, identity=77)
        self.assertEqual(0, machine.apply("apps", 0)["reward"])
        self.assertTrue(machine.apply("apps", -1)["unnecessary"])
        self.assertTrue(machine.complete())

    def test_observation_is_not_given_the_answer(self):
        for family in FAMILIES:
            for n in range(100, 160):
                state = training_environment(family, str(n))
                readings = state.inspect(family)
                self.assertEqual(3, len(readings))
                self.assertTrue(all(isinstance(x, float) for x in readings))
                self.assertTrue(all(abs(x) <= 100000 for x in readings))

    def test_blind_episode_is_multistep_and_disjoint(self):
        for index in range(EPISODES):
            faults = episode_conditions(index)
            self.assertEqual(set(FAMILIES), set(faults))
            self.assertGreater(sum(c != 0 for c in faults.values()), 1)

    def test_actual_core_retains_and_uses_rules(self):
        with tempfile.TemporaryDirectory() as folder:
            report = run(Path(folder) / "reasoning.sqlite3")
        self.assertTrue(report["real_bean_core"])
        self.assertFalse(report["external_model_used"])
        self.assertEqual(report["persisted_episode_records"], EPISODES)
        self.assertEqual(report["blind_episodes"], EPISODES)
        self.assertEqual(len(report["episodes"]), EPISODES)
        self.assertGreaterEqual(
            report["completion_rate"], 0.80,
            str({k: report[k] for k in (
                "accepted_rules", "learned_rules", "completion_rate",
                "remaining_faults", "repair_actions", "unnecessary_actions")})
            + " first_episode=" + str(report["episodes"][0]["trace"][:5]))
        self.assertLessEqual(report["unnecessary_action_rate"], 0.10)


if __name__ == "__main__":
    unittest.main()
