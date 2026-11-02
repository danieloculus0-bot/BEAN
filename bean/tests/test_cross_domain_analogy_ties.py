"""Synthetic ambiguity controls for opt-in cross-domain precedent recall.

A lexical tie is evidence of ambiguous retrieval, NOT proof that either
source procedure works in the target domain. No model, hardware or network.
"""
from pathlib import Path
import tempfile
import unittest

from bean.learning.reasoning_service import NativeReasoningService


class SyntheticModel:
    model_id = "synthetic-tie-provider"
    provider_kind = "synthetic_fixture"
    adapter_name = "local_llamacpp"

    def __init__(self):
        self.calls = []

    def complete(self, query, context):
        self.calls.append((query, context))
        return "No target-domain result has been observed."


class CrossDomainTieTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.path = Path(tmp.name) / "reasoning.sqlite"
        self.model = SyntheticModel()
        self.core = NativeReasoningService(self.path, model=self.model)
        self.addCleanup(self.core.close)
        # Both fictional procedures have the same four query tokens but
        # opposite advice. Neither is validated for the target game.
        self.first = self.core.retain_skill(
            domain="toy-maze", name="first",
            steps=["Compare tokens before choosing route"],
            passed=True, evidence_refs=["fixture:toy-maze-a"])["lesson_id"]
        self.second = self.core.retain_skill(
            domain="card-game", name="second",
            steps=["Never compare tokens before choosing route"],
            passed=True, evidence_refs=["fixture:card-game-b"])["lesson_id"]
        self.core.retain_skill(
            domain="board-game", name="local",
            steps=["Compare tokens before choosing route"],
            passed=True, evidence_refs=["fixture:local-only"])
        self.query = "compare tokens choosing route"

    def test_tie_detected_even_when_result_limit_hides_other_candidate(self):
        before = len(self.core.bank.journal.events())
        candidates = self.core.recall_analogies(
            domain="board-game", query=self.query, limit=2)
        self.assertEqual({x["lesson_id"] for x in candidates},
                         {self.first, self.second})
        self.assertTrue(all(x["lexical_tie_count"] == 2 for x in candidates))
        self.assertTrue(all(x["independently_verified_transfer"] is False
                            for x in candidates))
        self.assertEqual({x["evidence_refs"][0] for x in candidates},
                         {"fixture:toy-maze-a", "fixture:card-game-b"})
        top = self.core.recall_analogies(
            domain="board-game", query=self.query, limit=1)
        self.assertEqual(len(top), 1)
        self.assertEqual(top[0]["lexical_tie_count"], 2)
        self.assertEqual(len(self.core.bank.journal.events()), before)

    def test_tie_evidence_reaches_real_opt_in_provider_and_persists(self):
        result = self.core.reason(
            domain="board-game", task_ref="fictional-tie",
            query=self.query, include_analogies=True)
        self.assertEqual(len(self.model.calls), 1)
        context = self.model.calls[0][1]
        self.assertIn('"lexical_tie_count": 2', context)
        self.assertIn(self.first, context)
        self.assertIn(self.second, context)
        self.assertIn("UNVERIFIED", context)
        recorded = [e["data"] for e in self.core.bank.journal.events()
                    if e["kind"] == "inference"][-1]
        self.assertTrue(recorded["cross_domain_lexical_tie_present"])
        self.assertFalse(recorded["cross_domain_transfer_verified"])
        self.assertEqual(recorded["receipt_id"], result["receipt_id"])

        self.core.close()
        reopened = NativeReasoningService(self.path, model=None)
        try:
            candidates = reopened.recall_analogies(
                domain="board-game", query=self.query, limit=1)
            self.assertEqual(candidates[0]["lexical_tie_count"], 2)
            replay = [e["data"] for e in reopened.bank.journal.events()
                      if e["kind"] == "inference"][-1]
            self.assertEqual(replay["receipt_id"], result["receipt_id"])
            self.assertTrue(replay["cross_domain_lexical_tie_present"])
        finally:
            reopened.close()

    def test_negative_controls_do_not_claim_a_transfer(self):
        self.assertEqual(self.core.recall_analogies(
            domain="board-game", query="violet lanterns"), [])
        self.assertEqual(self.core.recall_analogies(
            domain="board-game", query="tokens"), [])
        # A unique lexical hit is not evidence of semantic correctness.
        unique = self.core.recall_analogies(
            domain="card-game", query="never compare tokens", limit=2)
        self.assertTrue(all(x["independently_verified_transfer"] is False
                            for x in unique))
        cold = self.core.reason(
            domain="board-game", task_ref="no-precedent",
            query=self.query, include_analogies=False)
        self.assertNotIn("POSSIBLE_OTHER_DOMAIN_PRECEDENTS",
                         self.model.calls[-1][1])
        record = [e["data"] for e in self.core.bank.journal.events()
                  if e["kind"] == "inference"][-1]
        self.assertNotIn("cross_domain_lexical_tie_present", record)
        self.assertFalse(cold["verified_outcome"])


if __name__ == "__main__":
    unittest.main()
