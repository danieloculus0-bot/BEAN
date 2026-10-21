"""Read-only scoreboard and immutable Q-episode receipt checks."""
from __future__ import annotations
import json
import tempfile
import unittest
from pathlib import Path

from bean.memory.store import MemoryStore
from bean.evaluation.emperor_gauntlet_ledger import (
    import_ledger, import_policy, scoreboard, validate_episode, validate_policy
)


def receipt(kind="training", kills=1, seed=73):
    return {
        "kind": kind, "seed": seed, "sourceCommit": "fixture-commit",
        "kills": kills, "wave": 1, "steps": 2, "reason": "", "reward": 3.5,
        "trace": {"version": 1, "seed": seed, "states": ["s0", "s1"],
                  "rows": [[0, 0, 1500, 1, 0, 0, 100, 100],
                           [1, 4, 2000, 0, 1, kills, 80, 90]]}
    }


class EmperorLedgerTest(unittest.TestCase):
    def test_valid_and_tampered_episodes(self):
        self.assertEqual(validate_episode(receipt())["kills"], 1)
        bad = receipt()
        bad["kills"] = 7
        with self.assertRaisesRegex(ValueError, "terminal scored kills"):
            validate_episode(bad)
        bad = receipt()
        bad["trace"]["rows"][0][1] = 999
        with self.assertRaisesRegex(ValueError, "Q transition"):
            validate_episode(bad)
        bad = receipt()
        bad["trace"]["rows"].pop()
        with self.assertRaisesRegex(ValueError, "decision trace"):
            validate_episode(bad)

    def test_policy_requires_real_q_table_shape(self):
        p = {"version": 1, "updates": 42, "table": {"key": [0.0]*15}}
        self.assertEqual(validate_policy(p)["updates"], 42)
        p["table"]["key"] = [0.0]*14
        with self.assertRaisesRegex(ValueError, "action vector"):
            validate_policy(p)

    def test_durable_ingestion_is_idempotent_and_scoreboard_keeps_cohorts(self):
        with tempfile.TemporaryDirectory() as folder:
            tmp = Path(folder)
            store = MemoryStore(str(tmp/"bean_memory.db"))
            source = tmp/"episodes.jsonl"
            episodes = [
                receipt("training", 2, 1), receipt("training", 5, 2),
                receipt("random-control", 1, 3),
                receipt("learned-holdout", 4, 3)
            ]
            source.write_text("\n".join(json.dumps(r) for r in episodes)+"\n")
            try:
                self.assertEqual(import_ledger(store, source)["imported"], 4)
                self.assertEqual(import_ledger(store, source)["imported"], 0)
                p = tmp/"policy.json"
                p.write_text(json.dumps({"version": 1, "updates": 27,
                                         "table": {"s0": [0.2]*15}}))
                import_policy(store, p, "fixture-commit")
                summary = scoreboard(store, "fixture-commit")
                self.assertEqual(summary["training_episodes"], 2)
                self.assertEqual(summary["best_training_kills"], 5)
                self.assertEqual(summary["average_training_kills"], 3.5)
                self.assertEqual(summary["learned_holdout_mean"], 4)
                self.assertEqual(summary["random_control_mean"], 1)
                self.assertEqual(summary["policy_receipts"][0]["updates"], 27)
                self.assertEqual(scoreboard(store, "other")["training_episodes"], 0)
            finally:
                store.close()


if __name__ == "__main__":
    unittest.main()
