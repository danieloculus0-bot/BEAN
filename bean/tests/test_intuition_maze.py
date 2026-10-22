"""BEAN Lab027 tests: real SpongeTD, no mocked learning code."""
import json
from pathlib import Path
import tempfile
import unittest

from bean.optimization.sponge_td import SpongeTD
from bean.optimization.sponge_intuition import SpongeIntuition
from bean.optimization.intuition_maze import KeyDoor, split, run, sha, ACTIONS


class IntuitionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def policy(self, name):
        p = SpongeTD(self.root / (name + ".sqlite"), actions=ACTIONS,
                     alpha=.24, gamma=.96, epsilon=.1, seed=43)
        self.addCleanup(p.close)
        return p

    def test_intuition_is_domain_neutral_and_does_not_change_weights(self):
        p = self.policy("read_only")
        p.learn(("task", 1), 0, 3, None, True)
        before = sha(p.q)
        reader = SpongeIntuition(p, seed=1, visit_penalty=2,
                                 revisit_penalty=1)
        first = reader.choose(("task", 1), location_ref="node1",
                              legal_actions=[0, 1], candidate_destinations={
                                  0: "node2", 1: "node3"})
        second = reader.choose(("task", 1), location_ref="node1",
                               legal_actions=[0, 1], candidate_destinations={
                                   0: "node2", 1: "node3"})
        self.assertEqual(first, 0)
        self.assertEqual(second, 1)
        self.assertEqual(before, sha(p.q))
        self.assertEqual(reader.last_decision["source"],
                         "SpongeTD Q-value plus episodic novelty")

    def test_no_implicit_learning_on_unseen_observation(self):
        p = self.policy("cold")
        r = SpongeIntuition(p, seed=10)
        r.choose({"different": ["schema", 2]}, location_ref=["unknown", 5],
                 legal_actions=[1, 2], candidate_destinations={})
        self.assertEqual(p.q, {})

    def test_invalid_input_is_rejected(self):
        p = self.policy("bad")
        with self.assertRaises(ValueError):
            SpongeIntuition(p, visit_penalty=float("nan"))
        with self.assertRaises(ValueError):
            SpongeIntuition(p, lookback=0)
        r = SpongeIntuition(p)
        for wrong in ([], [True], [0, 0], [10], [0, -1]):
            with self.assertRaises(ValueError):
                r.choose(("state",), location_ref="here", legal_actions=wrong)
        with self.assertRaises(ValueError):
            r.choose(("state",), location_ref="here", legal_actions=[0],
                     candidate_destinations={1: "bad"})

    def test_seed_splits_are_disjoint_and_maps_are_reproducible(self):
        a, b, c = split("train", 60), split("validation", 30), split("holdout", 40)
        self.assertFalse(set(a) & set(b))
        self.assertFalse(set(a) & set(c))
        self.assertFalse(set(b) & set(c))
        for seed in c[:10]:
            p, q = KeyDoor(seed), KeyDoor(seed)
            self.assertEqual((p.n, p.walls, p.start, p.key, p.exit),
                             (q.n, q.walls, q.start, q.key, q.exit))

    def test_actual_journal_checkpoint_and_compressed_event_recovery(self):
        result = run(self.root / "experiment", training=70,
                     validation=32, holdout=40)
        self.assertTrue(result["policy"]["exact_restart_verified"])
        self.assertEqual(result["selection"]["best"]["count"], 32)
        self.assertEqual(result["holdout"]["trained_intuition"]["count"], 40)
        self.assertTrue(result["ledger"]["lossless_roundtrip"])
        self.assertEqual(result["ledger"]["rows"], 70+32*18+32+40*4)
        self.assertEqual(result["manifest"]["train_count"], 70)
        self.assertTrue((self.root / "experiment" / "events.jsonl.gz").is_file())
        self.assertEqual(
            json.loads((self.root / "experiment" / "scoreboard.json").read_text())["schema"],
            "bean.intuition.lab027.v1")

    def test_repeating_seeded_experiment_reproduces_event_hashes(self):
        first = run(self.root / "first", training=60,
                    validation=30, holdout=35)
        second = run(self.root / "second", training=60,
                     validation=30, holdout=35)
        self.assertEqual(first["ledger"], second["ledger"])
        self.assertEqual(first["policy"]["sha256"], second["policy"]["sha256"])
        self.assertEqual(first["holdout"], second["holdout"])


if __name__ == "__main__":
    unittest.main()
