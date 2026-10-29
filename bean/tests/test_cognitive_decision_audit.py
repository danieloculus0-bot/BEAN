"""Independent decision-quality metric tests, including negative cases."""
import hashlib
import json
import unittest
from experiments.cognitive_gauntlet.decision_audit import audit_cases


def case(step, truth, p, q, *, regime="stable", seed=1, mode="remember"):
    return {"regime": regime, "seed": seed, "step": step,
            "truth_revealed_after_forecast": truth,
            "predictions": {"a": p, "b": q},
            "losses": {"a": (p-truth)**2, "b": (q-truth)**2},
            "mode": mode}


class DecisionAuditTests(unittest.TestCase):
    def test_proper_scoring_rewards_honest_probabilities(self):
        rows = [case(0, 1, .8, .99), case(1, 0, .2, .99)]
        report = audit_cases(rows, ["a", "b"])
        self.assertLess(report["overall"]["arms"]["a"]["brier"],
                        report["overall"]["arms"]["b"]["brier"])
        self.assertLess(report["overall"]["arms"]["a"]["log_loss"],
                        report["overall"]["arms"]["b"]["log_loss"])
        self.assertEqual(report["overall"]["arms"]["b"]["high_confidence_mistakes"], 1)

    def test_switching_cost_does_not_override_accuracy_without_assumption(self):
        rows = [case(0, 0, .1, .49), case(1, 1, .9, .49), case(2, 0, .1, .49)]
        report = audit_cases(rows, ["a", "b"])
        a = report["overall"]["arms"]["a"]
        b = report["overall"]["arms"]["b"]
        self.assertEqual(a["decision_switches"], 2)
        self.assertEqual(b["decision_switches"], 0)
        self.assertLess(a["decision_cost_sensitivity"]["0.1"],
                        b["decision_cost_sensitivity"]["0.1"])
        self.assertEqual(a["classification_error"], 0)

    def test_no_cross_seed_switch_count(self):
        rows = [case(0, 0, .1, .1, seed=1), case(0, 1, .9, .9, seed=2)]
        self.assertEqual(audit_cases(rows, ["a", "b"])["overall"]["arms"]["a"]["decision_switches"], 0)

    def test_chaos_mode_changes_are_not_decision_switches(self):
        rows = [case(0, 1, .8, .8), case(1, 1, .8, .8, mode="parallel_chaos")]
        summary = audit_cases(rows, ["a", "b"])["overall"]
        self.assertEqual(summary["dual_state"]["mode_changes"], 1)
        self.assertEqual(summary["arms"]["a"]["decision_switches"], 0)

    def test_integrity_missing_duplicate_and_corrupt_cases(self):
        for rows in ([case(1, 1, .8, .8)],
                     [case(0, 1, .8, .8), case(0, 1, .8, .8)],
                     [case(0, 1, .8, .8), case(2, 1, .8, .8)],
                     [case(0, 1, float("nan"), .8)]):
            with self.assertRaises(ValueError):
                audit_cases(rows, ["a", "b"])
        corrupt = case(0, 1, .8, .8)
        corrupt["losses"]["a"] = 0
        with self.assertRaises(ValueError):
            audit_cases([corrupt], ["a", "b"])

    def test_exact_digest_and_replay(self):
        rows = [case(0, 1, .7, .9), case(1, 0, .4, .1)]
        a = audit_cases(rows, ["a", "b"], source_digest="a"*64)
        self.assertEqual(a, audit_cases(rows, ["a", "b"], source_digest="a"*64))
        unsigned = {k: v for k, v in a.items() if k != "audit_sha256"}
        payload = json.dumps(unsigned, sort_keys=True, separators=(",", ":"))
        self.assertEqual(a["audit_sha256"], hashlib.sha256(payload.encode()).hexdigest())


if __name__ == "__main__":
    unittest.main()
