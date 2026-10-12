"""Focused Bridge-side test of real Sponge reward learning and scored memory."""
import hashlib
import tempfile
import unittest
from pathlib import Path

from bean.optimization.sponge_td import SpongeTD, score_memory
from bean.memory.compression import file_memory, recover_memory


class SpongeBridgeTests(unittest.TestCase):
    def test_delayed_reward_and_restart(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "experience.sqlite"
            agent = SpongeTD(path, actions=("wait", "move"), epsilon=0, alpha=.5, gamma=.9)
            # Transition reward delayed by one step: 'move' first earns zero,
            # then in the next state action 'move' earns 10.
            for _ in range(50):
                agent.learn("future", 1, 10, None, True)
                agent.learn("start", 1, 0, "future", False)
                agent.learn("start", 0, -1, None, True)
            self.assertEqual(agent.choose("start", explore=False), 1)
            self.assertGreater(agent.values("start")[1], 0)
            receipt = agent.checkpoint(baseline=1, candidate=2, samples=200,
                                       evaluation_sha256=hashlib.sha256(b"sealed-test-receipt").hexdigest())
            self.assertTrue(receipt["promotable"])
            tip = agent.journal.export()["tip"]
            agent.close()
            restarted = SpongeTD(path, actions=("wait", "move"), epsilon=0, alpha=.5, gamma=.9)
            self.assertEqual(restarted.journal.export()["tip"], tip)
            self.assertEqual(restarted.choose("start", explore=False), 1)
            self.assertEqual(restarted.checkpoints, 1)
            restarted.close()

    def test_validation_before_filing(self):
        with tempfile.TemporaryDirectory() as tmp:
            agent = SpongeTD(Path(tmp) / "learning.sqlite")
            with self.assertRaises(ValueError):
                agent.checkpoint(baseline=1, candidate=2, samples=0,
                                 evaluation_sha256="0" * 64)
            self.assertEqual(agent.journal.export()["attempts"], 0)
            agent.close()

    def test_scored_memory_tamper_and_abstention(self):
        poor = file_memory({"policy": {"left": 0}}, accuracy=0, relevance=0,
                           provenance=0, sample_count=200)
        self.assertEqual(recover_memory(poor), {"policy": {"left": 0}})
        with self.assertRaises(ValueError):
            recover_memory(poor, require_eligible=True)
        good = file_memory({"policy": {"left": 1}}, accuracy=1, relevance=1,
                           provenance=1, sample_count=200)
        self.assertEqual(recover_memory(good, require_eligible=True),
                         {"policy": {"left": 1}})
        altered = dict(good)
        altered["score"] = dict(good["score"])
        altered["score"]["value"] = 0
        with self.assertRaises(ValueError):
            recover_memory(altered)


if __name__ == "__main__":
    unittest.main()
