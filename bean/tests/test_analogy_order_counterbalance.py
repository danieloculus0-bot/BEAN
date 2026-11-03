"""Counterbalanced negative control for BEAN's existing lexical analogy recall.

Same candidate evidence, same query, only lesson insertion order changes.
This measures order sensitivity, not semantic understanding or AGI.
"""
from pathlib import Path
import tempfile
import unittest

from bean.learning.reasoning_service import NativeReasoningService


class AnalogyOrderCounterbalanceTests(unittest.TestCase):
    QUERY = "High pressure increases flow"
    CANDIDATES = {
        "supports": ("fluid", "High pressure increases flow"),
        "contradicts": ("electrical", "High pressure does not increase flow"),
    }

    def _run_order(self, order):
        with tempfile.TemporaryDirectory() as folder:
            db = Path(folder) / "native.sqlite"
            core = NativeReasoningService(db, model=None)
            try:
                ids = {}
                for label in order:
                    domain, statement = self.CANDIDATES[label]
                    ids[label] = core.retain_skill(
                        domain=domain, name="flow observation",
                        steps=[statement], passed=True,
                        evidence_refs=["synthetic:" + label],
                    )["lesson_id"]
                before = len(core.bank.journal.events())
                hits = core.recall_analogies(domain="target", query=self.QUERY)
                self.assertEqual(len(core.bank.journal.events()), before)
                self.assertEqual(len(hits), 2)
                self.assertEqual(hits[0]["matched_terms"], hits[1]["matched_terms"])
                self.assertEqual(
                    {h["lesson_id"] for h in hits}, set(ids.values()))
                self.assertTrue(all(
                    h["independently_verified_transfer"] is False
                    and h["safe_to_apply_without_target_test"] is False
                    for h in hits))
                first = next(label for label, identity in ids.items()
                             if identity == hits[0]["lesson_id"])
            finally:
                core.close()
            restarted = NativeReasoningService(db, model=None)
            try:
                replay = restarted.recall_analogies(
                    domain="target", query=self.QUERY)
                self.assertEqual(
                    [h["lesson_id"] for h in replay],
                    [h["lesson_id"] for h in hits])
                self.assertEqual(
                    [h["evidence_refs"] for h in replay],
                    [h["evidence_refs"] for h in hits])
            finally:
                restarted.close()
            return first

    def test_reversing_insertion_order_reverses_top_candidate(self):
        # Fixed evidence and query. The most recent equal-overlap lesson wins.
        self.assertEqual(
            self._run_order(("supports", "contradicts")), "contradicts")
        self.assertEqual(
            self._run_order(("contradicts", "supports")), "supports")


if __name__ == "__main__":
    unittest.main()
