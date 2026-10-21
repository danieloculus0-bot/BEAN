"""Focused contract checks for BEAN-visible historical scoring and rewards."""
import tempfile
import unittest
from pathlib import Path

from bean.optimization.scoreboard_context import (
    RewardTrial, apply_once, record_reward, score_reward, scoreboard_context,
)

RECEIPT = "a" * 64

def example(**changes):
    data=dict(experiment="lab009",metric="frozen_accuracy",condition_id="fixture-v1",
              baseline_run="baseline",candidate_run="frozen",baseline=0,
              candidate=2,direction="higher",matched_cases=3,expected_cases=3,
              evaluation_sha256=RECEIPT,
              evidence_ref="https://github.com/danieloculus0-bot/BEAN-AI-Bridge-/actions/runs/39534731732")
    data.update(changes)
    return RewardTrial(**data)


class LearnerProbe:
    def __init__(self): self.calls=[]
    def observe(self, state, action, reward, next_state, done):
        self.calls.append((state,action,reward,next_state,done))


class ScoreboardRewardTests(unittest.TestCase):
    def test_visible_existing_real_repository_scoreboards(self):
        root = Path(__file__).resolve().parents[2]/"research"/"persistent_ledger"
        result=scoreboard_context(root)
        labels={x["schema"] for x in result["entries"]}
        self.assertIn("bean.lab009.scoring.v1", labels)
        self.assertIn("bean.scoreboard.experimental.v1", labels)
        self.assertIn("bean.core.matrix.scoreboard.v1", labels)
        lab=next(e for e in result["entries"] if e["schema"]=="bean.lab009.scoring.v1")
        self.assertEqual(lab["metrics"]["baseline_correct"],0)
        self.assertEqual(lab["metrics"]["frozen_post_restart_correct"],2)
        self.assertEqual(lab["metrics"]["online_post_investigation_correct"],3)
        self.assertEqual(lab["metrics"]["total_cases"],3)
        self.assertEqual(result["entries_omitted"],0)
        self.assertIn("not a live model score",result["agent_note"])

    def test_reward_positive_zero_negative(self):
        self.assertAlmostEqual(score_reward(example())["reward"],1.0)
        self.assertEqual(score_reward(example(candidate=0))["reward"],0)
        self.assertLess(score_reward(example(baseline=2,candidate=1))["reward"],0)
        self.assertGreater(score_reward(example(metric="latency_ms",baseline=60,
                                                candidate=20,direction="lower"))["reward"],0)

    def test_no_reward_for_incomplete_or_same_run(self):
        self.assertIsNone(score_reward(example(matched_cases=2))["reward"])
        self.assertFalse(score_reward(example(matched_cases=2))["eligible"])
        self.assertIsNone(score_reward(example(candidate_run="baseline"))["reward"])

    def test_one_receipt_and_no_repeated_reward(self):
        with tempfile.TemporaryDirectory() as tmp:
            first=record_reward(tmp,example())
            second=record_reward(tmp,example())
            self.assertTrue(first["new_reward"])
            self.assertFalse(second["new_reward"])
            self.assertEqual(list((Path(tmp)/"reward_receipts").glob("*.json")).__len__(),1)
            agent=LearnerProbe()
            self.assertTrue(apply_once(agent,first,state=(0,0,0),action=1,next_state=(1,1,1),done=False))
            self.assertFalse(apply_once(agent,second,state=(0,0,0),action=1,next_state=(1,1,1),done=False))
            self.assertEqual(len(agent.calls),1)
            self.assertEqual(agent.calls[0][2],first["reward"])

    def test_missing_ledger_is_not_a_fake_zero(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(FileNotFoundError):
                scoreboard_context(Path(tmp)/"missing")

    def test_invalid_evidence_and_nans_rejected(self):
        with self.assertRaises(ValueError): score_reward(example(evaluation_sha256="x"))
        with self.assertRaises(ValueError): score_reward(example(candidate=float("nan")))
        with self.assertRaises(ValueError): score_reward(example(evidence_ref="untrusted"))
        with self.assertRaises(ValueError): score_reward(example(matched_cases=5))
        with self.assertRaises(ValueError): score_reward(example(direction="maximize"))

    def test_bad_scoreboard_does_not_silently_pass(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/"scoreboard.json"
            p.write_text('{"nothing":0}')
            with self.assertRaisesRegex(ValueError,"invalid scoreboard"):scoreboard_context(tmp)


if __name__=="__main__":
    unittest.main()
