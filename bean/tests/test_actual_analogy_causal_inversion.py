"""Falsification diagnostic against the actual PR #214 analogy retriever.

Synthetic causal opposites are deliberately given equal lexical evidence.
These assertions document a known limitation, NOT successful causal reasoning.
No live model, network, Jetson, or second memory store is involved.
"""
from pathlib import Path
import tempfile
import unittest

from bean.learning.reasoning_service import NativeReasoningService


class ActualAnalogyCausalInversionTests(unittest.TestCase):
    def test_opposite_causal_precedents_are_not_distinguished(self):
        with tempfile.TemporaryDirectory() as folder:
            db = Path(folder) / "native.sqlite"
            core = NativeReasoningService(db, model=None)
            try:
                supporting = core.retain_skill(
                    domain="hydraulics", name="pressure opens valve",
                    steps=["When pressure rises, valve opens"],
                    passed=True, evidence_refs=["synthetic:positive"],
                )["lesson_id"]
                opposing = core.retain_skill(
                    domain="pneumatics", name="pressure opens valve",
                    steps=["When valve opens, pressure rises"],
                    passed=True, evidence_refs=["synthetic:reverse"],
                )["lesson_id"]
                query = "When pressure rises, valve opens"
                before = len(core.bank.journal.events())
                hits = core.recall_analogies(domain="process", query=query)
                self.assertEqual({h["lesson_id"] for h in hits},
                                 {supporting, opposing})
                self.assertEqual(len(hits[0]["matched_terms"]),
                                 len(hits[1]["matched_terms"]))
                self.assertEqual(hits[0]["lesson_id"], opposing)
                self.assertTrue(all(not h["independently_verified_transfer"]
                                    for h in hits))
                self.assertEqual(before, len(core.bank.journal.events()))
            finally:
                core.close()
            restarted = NativeReasoningService(db, model=None)
            try:
                again = restarted.recall_analogies(
                    domain="process", query="When pressure rises, valve opens")
                self.assertEqual([h["lesson_id"] for h in again],
                                 [opposing, supporting])
                self.assertEqual([h["evidence_refs"] for h in again],
                                 [["synthetic:reverse"], ["synthetic:positive"]])
            finally:
                restarted.close()

    def test_lexical_tie_can_rank_contradictory_precedent_first(self):
        with tempfile.TemporaryDirectory() as folder:
            core = NativeReasoningService(Path(folder) / "native.sqlite",
                                          model=None)
            try:
                positive = core.retain_skill(
                    domain="fluid", name="flow observation",
                    steps=["High pressure increases flow"],
                    passed=True, evidence_refs=["synthetic:positive"],
                )["lesson_id"]
                negative = core.retain_skill(
                    domain="electrical", name="flow observation",
                    steps=["High pressure does not increase flow"],
                    passed=True, evidence_refs=["synthetic:negative"],
                )["lesson_id"]
                hits = core.recall_analogies(
                    domain="target",
                    query="High pressure increases flow")
                self.assertEqual([h["lesson_id"] for h in hits], [negative, positive])
                self.assertEqual(hits[0]["matched_terms"], hits[1]["matched_terms"])
                self.assertNotIn("not", hits[0]["matched_terms"])
                self.assertEqual(hits[0]["evidence_refs"], ["synthetic:negative"])
                self.assertFalse(hits[0]["safe_to_apply_without_target_test"])
            finally:
                core.close()


if __name__ == "__main__":
    unittest.main()
