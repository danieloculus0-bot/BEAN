"""Evidence-bound counsel choices, replay and no-unnecessary-model regression.

These fixtures are host statements, not authenticated experts or proof of AGI.
"""
from pathlib import Path
import tempfile
import unittest
from types import SimpleNamespace

from bean.learning import NativeReasoningService
from bean.learning.judgment import choose_counsel
from bean.learning.reasoning_service import register_native_reasoning_handlers


def candidate(kind="established", answer="Use the standard procedure",
              source_ref="standard:rev-1", **changes):
    row = dict(
        kind=kind, answer=answer, source_ref=source_ref,
        evidence_refs=["fixture:record-1"], adequate=True, in_scope=True,
        current=True, source_checked=True, confidence="high",
        qualified=(kind == "expert"), corroborated=True,
    )
    row.update(changes)
    return row


class Inbox:
    def __init__(self):
        self.handlers = {}

    def register(self, name, callback):
        self.handlers[name] = callback

    def call(self, name, **args):
        return self.handlers[name](SimpleNamespace(args=args), "fixture-session")


class JudgmentTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.path = Path(temporary.name) / "counsel.sqlite"
        self.service = NativeReasoningService(self.path)
        self.addCleanup(self.service.close)
        self.inbox = Inbox()
        register_native_reasoning_handlers(self.inbox, self.service)

    def decide(self, candidates, **kwargs):
        return self.service.judge(
            domain="quality", task_ref="fixture-1", query="Which method?",
            candidates=candidates, **kwargs)

    def test_adequate_standard_beats_needless_invention_without_model(self):
        existing = candidate()
        new = candidate("self", "Invent a different method",
                        "self:idea-1")
        result = self.inbox.call(
            "reasoning_reason", domain="quality", task_ref="fixture-1",
            query="Which method?", candidates=[new, existing])
        self.assertEqual(result["answer"], existing["answer"])
        self.assertEqual(result["decision"]["source_kind"], "established")
        self.assertEqual(result["decision"]["decision"], "adopt")
        self.assertFalse(result["model_invoked"])
        self.assertEqual(self.service.status()["inference_receipts"], 0)
        self.assertEqual(self.service.status()["judgment_receipts"], 1)

    def test_medium_confidence_adequate_standard_precedes_self_high(self):
        # An adequate conventional approach need not outperform novelty.
        result = self.decide([
            candidate("self", "Experiment", "self:new", confidence="high"),
            candidate("established", "Known workable method", "qms:approved",
                      confidence="medium"),
        ])
        self.assertEqual(result["decision"], "adopt")
        self.assertEqual(result["source_kind"], "established")
        self.assertEqual(result["answer"], "Known workable method")

    def test_qualified_expert_can_be_deferred_to_when_supported(self):
        result = self.decide([
            candidate("self", "My guess", "self:guess",
                      confidence="low", corroborated=False),
            candidate("expert", "Use qualified inspection",
                      "specialist:report-1"),
        ])
        self.assertEqual(result["decision"], "adopt")
        self.assertEqual(result["source_kind"], "expert")
        self.assertFalse(result["external_truth_verified"])
        self.assertEqual(result["source_metadata_origin"],
                         "host_attested_not_independently_authenticated")

    def test_unqualified_or_stale_counsel_is_not_automatically_true(self):
        unqualified = candidate("expert", qualified=False)
        result = self.decide([unqualified])
        self.assertEqual(result["decision"], "explore")
        stale = candidate("established", current=False)
        result = self.decide([stale], stakes="high")
        self.assertEqual(result["decision"], "defer")
        self.assertIsNone(result["answer"])

    def test_uncertain_qualified_counsel_prompts_review(self):
        result = self.decide([
            candidate("expert", source_checked=False, confidence="medium"),
        ])
        self.assertEqual(result["decision"], "defer")
        self.assertEqual(result["next_step"], "request_review_or_verification")

    def test_high_stakes_require_host_claimed_corroboration(self):
        result = self.decide([
            candidate("established", corroborated=False),
        ], stakes="high")
        self.assertEqual(result["decision"], "defer")
        result = self.decide([candidate()], stakes="high")
        self.assertEqual(result["decision"], "adopt")
        self.assertFalse(result["external_truth_verified"])

    def test_possible_conflict_never_silently_selects_one(self):
        result = self.decide([
            candidate(), candidate("expert", answer="Different conclusion",
                                   source_ref="specialist:report-1")
        ], conflicting_evidence=True)
        self.assertEqual(result["decision"], "defer")
        self.assertIn("host_reported_conflict", result["reasons"])
        result = self.decide([
            candidate(), candidate(answer="Another answer",
                                   source_ref="standard:rev-2")
        ])
        self.assertEqual(result["decision"], "defer")
        self.assertIn("potential_peer_disagreement", result["reasons"])

    def test_outcome_feedback_persists_after_restart_and_deduplicates(self):
        decision = self.inbox.call("reasoning_judge", domain="quality",
            task_ref="fixture-1", query="Which method?", candidates=[candidate()])
        data = dict(receipt_id=decision["receipt_id"], outcome="refuted",
                    evidence_refs=["fixture:holdout-failure"],
                    note="Failed the observed check")
        receipt = self.inbox.call("reasoning_judgment_feedback", **data)
        self.assertTrue(receipt["new_feedback"])
        self.assertFalse(
            self.inbox.call("reasoning_judgment_feedback", **data)["new_feedback"])
        self.assertEqual(self.service.status()["judgment_outcomes"], 1)
        self.service.close()
        reopened = NativeReasoningService(self.path)
        try:
            self.assertEqual(reopened.status()["judgment_receipts"], 1)
            self.assertEqual(reopened.status()["judgment_outcomes"], 1)
            self.assertEqual(len(reopened.bank.journal.events()), 2)
        finally:
            reopened.close()

    def test_invalid_input_fails_before_writing(self):
        for broken in (
            candidate(confidence="invented"),
            candidate(source_checked="yes"),
            candidate(evidence_refs=[]),
        ):
            with self.assertRaises(ValueError):
                self.decide([broken])
        with self.assertRaises(ValueError):
            self.service.judgment_feedback(
                receipt_id="0" * 64, outcome="supported",
                evidence_refs=["fixture:no-original"])
        self.assertEqual(self.service.status()["judgment_receipts"], 0)

    def test_no_candidate_means_investigation_not_invented_answer(self):
        result = choose_counsel(domain="d", task_ref="t", query="q", candidates=[])
        self.assertEqual(result["decision"], "explore")
        self.assertIsNone(result["answer"])
        self.assertFalse(result["model_invoked"])


if __name__ == "__main__":
    unittest.main()
