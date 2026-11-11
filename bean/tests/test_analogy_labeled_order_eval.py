"""Labeled, counterbalanced *diagnostic* of native cross-domain recall.

Synthetic examples only. This is not a claim of semantic transfer or AGI.
The labels are assigned before retrieval and do not come from the retriever.
"""
from pathlib import Path
import tempfile
import unittest

from bean.learning.reasoning_service import NativeReasoningService


class LabeledAnalogyOrderEvaluation(unittest.TestCase):
    QUERY = "High pressure increases flow"
    # Independent synthetic causal labels. Both examples share the same topic.
    CANDIDATES = {
        "supports": ("fluid", "High pressure increases flow"),
        "contradicts": ("electrical", "High pressure does not increase flow"),
    }

    def _trial(self, order):
        with tempfile.TemporaryDirectory() as folder:
            db = Path(folder) / "native.sqlite"
            service = NativeReasoningService(db, model=None)
            try:
                ids = {}
                for label in order:
                    domain, statement = self.CANDIDATES[label]
                    ids[label] = service.retain_skill(
                        domain=domain, name="flow observation",
                        steps=[statement], passed=True,
                        evidence_refs=["synthetic:" + label],
                    )["lesson_id"]
                ranked = service.recall_analogies(domain="target", query=self.QUERY)
                self.assertEqual(len(ranked), 2)
                self.assertTrue(all(
                    hit["independently_verified_transfer"] is False
                    for hit in ranked
                ))
                self.assertEqual(
                    {hit["lesson_id"] for hit in ranked}, set(ids.values()))
                # Freeze a copy of the observed ranking before restarting.
                ranked_ids = [hit["lesson_id"] for hit in ranked]
            finally:
                service.close()
            replay = NativeReasoningService(db, model=None)
            try:
                self.assertEqual(
                    [hit["lesson_id"] for hit in replay.recall_analogies(
                        domain="target", query=self.QUERY)], ranked_ids)
            finally:
                replay.close()
            chosen = next(label for label, identity in ids.items()
                          if identity == ranked_ids[0])
            return int(chosen == "supports")

    def test_labeled_paired_controls(self):
        # Equal candidate evidence; only order changes. A lexical/recency
        # ranker should not be credited with validated causal transfer.
        observations = [
            self._trial(("supports", "contradicts")),
            self._trial(("contradicts", "supports")),
        ]
        self.assertEqual(observations, [0, 1])
        # These are diagnostic fixture scores, NOT population estimates.
        actual_top1 = sum(observations)
        oracle_top1 = len(observations)  # upper bound using withheld labels
        abstain_top1 = 0  # no-recall control cannot select a precedent
        self.assertEqual((actual_top1, oracle_top1, abstain_top1), (1, 2, 0))
        self.assertLess(actual_top1, oracle_top1)
        # Two counterbalanced runs are correlated, not two independent tasks.


if __name__ == "__main__":
    unittest.main()
