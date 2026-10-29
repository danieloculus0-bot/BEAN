"""Cross-domain rule reuse tests with opaque host rewards and frozen heldouts.

All environments here are seeded synthetic numeric controls, not an installed
external AI, physical robotics, or evidence of open-domain intelligence.
"""
import tempfile
import unittest
from pathlib import Path

from bean.evaluation.active_abstraction_benchmark import World
from bean.learning.reasoning_service import NativeReasoningService


class DiscoveredTransferTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "transfer.sqlite"
        self.world = World(120, "channel")
        self.core = NativeReasoningService(self.path)
        self.original = self.core.discover_analogy(
            domain="source process control", task_ref="source-120",
            source_ref="fixture:source-120",
            probe_ids=[str(100+i) for i in range(40)],
            observe=self.world.observe, reward=self.world.feedback,
            budget=12, validation_probe_ids=[str(300+i) for i in range(12)])
        self.assertEqual(self.original["status"], "provisional_rule")

    def tearDown(self):
        self.core.close()
        self.tmp.cleanup()

    def target_sensors(self, case):
        # Target has a shifted sensor distribution with the same semantic axes.
        # The learner sees only these observations; fixture truth stays hidden.
        return tuple(x*3.0 for x in self.world.observe(case))

    def transfer(self, domain="target energy balancing", probes=None, reward=None,
                 observe=None, margin=0.0):
        return self.core.transfer_discovered_analogy(
            source_receipt_id=self.original["receipt_id"],
            target_domain=domain, task_ref="new-controller",
            source_ref="fixture:other-domain",
            probe_ids=(probes if probes is not None else
                       [str(1000+i) for i in range(12)]),
            observe=observe or self.target_sensors,
            reward=reward or self.world.feedback,
            margin=margin)

    def test_positive_transfer_generalizes_to_frozen_unseen_target_cases(self):
        measured = []
        def target_reward(case, action):
            measured.append((case, action))
            return self.world.feedback(case, action)
        outcome = self.transfer(reward=target_reward)
        self.assertTrue(outcome["transfer_accepted"])
        self.assertEqual(outcome["selected"], "source_rule")
        self.assertEqual(outcome["candidate_generator"],
                         "recovered_native_hypothesis")
        self.assertEqual(outcome["source_domain"], "source process control")
        self.assertEqual(outcome["target_domain"], "target energy balancing")
        self.assertEqual(outcome["number_of_pairs"], 12)
        self.assertEqual(outcome["reward_calls"], 24)
        self.assertEqual(len(measured), 24)
        self.assertEqual(len(outcome["observations"]), 12)
        self.assertFalse(outcome["final_heldout_used"])
        self.assertFalse(outcome["independently_authenticated"])
        self.assertEqual(outcome["source_ancestry_observation_coverage"], "complete")
        frozen_ids = [str(9000+i) for i in range(30)]
        predictions = [
            self.core.use_tested_transfer(
                transfer_receipt_id=outcome["receipt_id"],
                sensors=self.target_sensors(case))["action"]
            for case in frozen_ids]
        correct = sum(self.world.feedback(case, action)
                      for case, action in zip(frozen_ids, predictions))
        baseline = sum(self.world.feedback(case, 0) for case in frozen_ids)
        self.assertEqual(correct, 30)
        self.assertEqual(baseline, 0)
        self.assertTrue(set(case for case, _ in measured).isdisjoint(frozen_ids))
        self.assertTrue(set(outcome["observed_probe_ids"]).isdisjoint(frozen_ids))
        self.assertEqual(len([e for e in self.core.bank.journal.events()
            if e["kind"] == "trial" and e["data"].get("experiment") ==
            "bean.native.discovered_transfer.v1"]), 1)
        self.core.close()
        reopened = NativeReasoningService(self.path)
        try:
            self.assertEqual(reopened.use_tested_transfer(
                transfer_receipt_id=outcome["receipt_id"],
                sensors=self.target_sensors("9000"))["action"], predictions[0])
        finally:
            reopened.close()

    def test_negative_transfer_rejects_old_rule_for_no_action_baseline(self):
        outcome = self.transfer(
            domain="target safety stop",
            reward=lambda case, action: 1.0 if action == 0 else 0.0)
        self.assertFalse(outcome["transfer_accepted"])
        self.assertEqual(outcome["selected"], "stay_0")
        self.assertEqual(outcome["comparison_result"], "prefer_alternative")
        self.assertLess(outcome["average_advantage"], 0)
        self.assertEqual(self.core.use_tested_transfer(
            transfer_receipt_id=outcome["receipt_id"],
            sensors=self.target_sensors("9000"))["action"], 0)

    def test_ties_abstain_and_survive_restart(self):
        outcome = self.transfer(
            domain="target uncertain scenario",
            reward=lambda *_: 0.5)
        self.assertIsNone(outcome["selected"])
        self.assertEqual(outcome["comparison_result"], "inconclusive_abstain")
        self.assertEqual(outcome["reward_calls"], 24)
        answer = self.core.use_tested_transfer(
            transfer_receipt_id=outcome["receipt_id"],
            sensors=self.target_sensors("9000"))
        self.assertEqual(answer["status"], "abstain")
        self.core.close()
        again = NativeReasoningService(self.path)
        try:
            self.assertEqual(again.use_tested_transfer(
                transfer_receipt_id=outcome["receipt_id"],
                sensors=self.target_sensors("9000")), answer)
        finally:
            again.close()

    def test_avoid_ancestral_and_replayed_target_evidence(self):
        with self.assertRaisesRegex(ValueError, "fresh target"):
            self.transfer(probes=["100"] + [str(1100+i) for i in range(11)])
        with self.assertRaisesRegex(ValueError, "fresh target"):
            self.transfer(probes=["300"] + [str(1100+i) for i in range(11)])
        self.transfer()
        with self.assertRaisesRegex(ValueError, "fresh target"):
            self.transfer()
        # A new target domain may evaluate the source again, but cannot
        # relabel old probes as new within the same target.
        self.assertEqual(self.transfer(domain="other independent target")[
            "source_domain"], "source process control")

    def test_invalid_receipts_sensor_layout_and_inputs(self):
        with self.assertRaisesRegex(ValueError, "different target domain"):
            self.transfer(domain="SOURCE PROCESS CONTROL")
        with self.assertRaisesRegex(ValueError, "unique target probe"):
            self.transfer(probes=["1000", "1000", "1001"])
        with self.assertRaisesRegex(ValueError, "Sensor layout"):
            self.transfer(observe=lambda case: (0.5, 0.25))
        with self.assertRaisesRegex(ValueError, "Unknown self-discovered"):
            self.core.transfer_discovered_analogy(
                source_receipt_id="missing", target_domain="elsewhere",
                task_ref="new", source_ref="test",
                probe_ids=["2001", "2002", "2003"],
                observe=self.target_sensors, reward=self.world.feedback)
        with self.assertRaisesRegex(ValueError, "Unknown transfer receipt"):
            self.core.use_tested_transfer(
                transfer_receipt_id="missing",
                sensors=self.target_sensors("9000"))
        result = self.transfer(domain="with-layout-check")
        with self.assertRaisesRegex(ValueError, "Sensor layout"):
            self.core.use_tested_transfer(
                transfer_receipt_id=result["receipt_id"], sensors=(1.0, 2.0))


if __name__ == "__main__":
    unittest.main()
