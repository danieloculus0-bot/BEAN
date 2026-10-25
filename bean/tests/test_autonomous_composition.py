"""Actual BEAN Core composition experiments: no model, no trading, no claims of AGI.

Independent source rules are learned in separate domains. A target task then
requires combining BOTH outputs with a join chosen by the bounded BEAN search.
Holdout answers are not supplied to learn_composition. Repeated probes are
pure symbolic task evaluation on unseen input structures and values.
"""
from __future__ import annotations

import json
from pathlib import Path
import random
import tempfile
import unittest

from bean.learning.reasoning_service import (
    NativeReasoningService, register_native_reasoning_handlers,
)


TAG_TRAIN = [
    {"question": "ORCHID-7 tags A3 B9 C5", "answer": "BCA"},
    {"question": "ORCHID-7 tags X7 Q1 D5", "answer": "XDQ"},
    {"question": "ORCHID-7 tags K2 L8 M4", "answer": "LMK"},
]
GAUGE_TRAIN = [
    {"question": "HARBOR-4 A=12 B=7 C=19", "answer": "A"},
    {"question": "HARBOR-4 D=10 E=20 F=15", "answer": "F"},
    {"question": "HARBOR-4 G=15 H=22 J=4", "answer": "G"},
]


def question(pairs, gauges):
    return json.dumps({"parts": [
        "TASK-1 tags " + " ".join(k + str(v) for k, v in pairs),
        "TASK-2 " + " ".join(k + "=" + str(v) for k, v in gauges),
    ]}, sort_keys=True)


def target(pairs, gauges):
    ranked = "".join(k for k, _ in sorted(pairs, key=lambda item: -item[1]))
    med = sorted(gauges, key=lambda item: item[1])[1][0]
    return str(ranked.index(med) + 1)


DEV = [
    ([("A", 3), ("B", 9), ("C", 5)],
     [("A", 12), ("B", 7), ("C", 19)]),
    ([("D", 7), ("E", 2), ("F", 9)],
     [("D", 5), ("E", 7), ("F", 3)]),
    ([("G", 8), ("H", 5), ("J", 2)],
     [("G", 7), ("H", 10), ("J", 3)]),
    ([("K", 2), ("L", 7), ("M", 5)],
     [("K", 9), ("L", 4), ("M", 12)]),
]


class CompositionTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.db = Path(temp.name) / "bean-experience.sqlite3"
        self.core = NativeReasoningService(self.db, model=None)
        self.addCleanup(self.core.close)

    def seed_parents(self):
        a = self.core.learn_local(
            domain="tag-sorting", task_ref="primitive-a",
            examples=TAG_TRAIN, evidence_refs=["development:tags"])
        b = self.core.learn_local(
            domain="gauge-median", task_ref="primitive-b",
            examples=GAUGE_TRAIN, evidence_refs=["development:gauges"])
        self.assertEqual(a["operation"], "digit_desc")
        self.assertEqual(b["operation"], "median")
        return a, b

    def train(self, cases=DEV, domain="mixed-transfer"):
        return self.core.learn_composition(
            domain=domain, task_ref="dev-composition-only",
            examples=[{"question": question(t, g), "answer": target(t, g)}
                      for t, g in cases],
            evidence_refs=["development:paired-rule-examples"])

    def test_discovers_unique_two_rule_program_and_reuses_after_restart(self):
        parents = self.seed_parents()
        candidate = self.train()
        self.assertEqual(candidate["status"], "learned_composition")
        self.assertEqual(candidate["join"], "rank_second_in_first")
        self.assertEqual(set(candidate["parent_rule_ids"]),
                         {a["rule_id"] for a in parents})
        self.assertGreater(candidate["programs_examined"], 1)
        self.assertFalse(candidate["independent_validation"])
        self.assertEqual(self.core.status()["native_composed_rules"], 1)

        rng = random.Random(20261025)
        unseen_receipts = set()
        for i in range(48):
            labels = rng.sample("ABCEFGHJKLMNPRSTVWXYZ", 3)
            pairs = list(zip(labels, rng.sample(range(1, 10), 3)))
            gauges = list(zip(labels, rng.sample(range(-90, 90), 3)))
            q = question(pairs, gauges)
            result = self.core.reason_auto(
                domain="mixed-transfer", task_ref="blind-" + str(i), query=q)
            self.assertEqual(result["status"], "locally_solved")
            self.assertEqual(result["answer"], target(pairs, gauges))
            self.assertFalse(result["model_invoked"])
            self.assertFalse(result["development_overlap"])
            self.assertEqual(len(result["rules_used"]), 2)
            self.assertEqual(result["trace"][-1], "apply:rank_second_in_first")
            unseen_receipts.add(result["receipt_id"])
        self.assertEqual(len(unseen_receipts), 48)
        self.assertEqual(self.core.status()["native_symbolic_inferences"], 48)
        self.assertEqual(self.core.status()["inference_receipts"], 48)

        before = self.core.bank.journal.events()[-1]["hash"]
        self.core.close()
        reopened = NativeReasoningService(self.db, model=None)
        try:
            self.assertEqual(reopened.status()["native_composed_rules"], 1)
            q = question([("R", 2), ("S", 8), ("T", 5)],
                         [("R", 6), ("S", 3), ("T", 10)])
            saved = reopened.reason_auto(
                domain="mixed-transfer", task_ref="recovered", query=q)
            self.assertEqual(saved["answer"], target(
                [("R", 2), ("S", 8), ("T", 5)],
                [("R", 6), ("S", 3), ("T", 10)]))
            self.assertNotEqual(before, saved["journal_tip"])
            self.assertFalse(saved["model_invoked"])
            feedback = reopened.feedback(
                receipt_id=saved["receipt_id"], expected=saved["answer"],
                evidence_refs=["host:heldout-manually-scored"])
            self.assertTrue(feedback["matched"])
            self.assertEqual(feedback["outcome_origin"], "host_reported")
        finally:
            reopened.close()

    def test_cannot_synthesize_without_retained_independent_parents(self):
        result = self.train()
        self.assertEqual(result["status"], "abstain")
        self.assertEqual(result["reason"], "no_supported_composition")
        self.assertEqual(self.core.status()["native_composed_rules"], 0)
        self.core.learn_local(
            domain="only-one-skill", task_ref="first",
            examples=TAG_TRAIN, evidence_refs=["development:tags"])
        self.assertEqual(self.train()["status"], "abstain")
        self.assertEqual(self.core.status()["native_composed_rules"], 0)

    def test_conflicting_demonstrations_and_repeated_questions_are_not_learned(self):
        self.seed_parents()
        dev = [{"question": question(t, g), "answer": "UNSUPPORTED"}
               for t, g in DEV]
        refused = self.core.learn_composition(
            domain="mixed-transfer", task_ref="bad-dev",
            examples=dev, evidence_refs=["source:deliberate-error"])
        self.assertEqual(refused["status"], "abstain")
        self.assertEqual(refused["reason"], "no_supported_composition")
        bad = [{"question": question(*DEV[0]), "answer": "3"}] * 4
        with self.assertRaisesRegex(ValueError, "different question fingerprints"):
            self.core.learn_composition(
                domain="mixed-transfer", task_ref="copied-question",
                examples=bad, evidence_refs=["source:duplicate"])
        self.assertEqual(self.core.status()["native_composed_rules"], 0)

    def test_two_supported_but_contradictory_plans_abstain(self):
        self.seed_parents()
        self.assertEqual(self.train()["status"], "learned_composition")
        alternate = self.core.learn_composition(
            domain="mixed-transfer", task_ref="dev-other-answer",
            examples=[{
                "question": question(t, g),
                "answer": "".join(k for k, v in
                                  sorted(t, key=lambda item: -item[1])) + "|" +
                          sorted(g, key=lambda item: item[1])[1][0],
            } for t, g in DEV],
            evidence_refs=["development:competing-program"])
        self.assertEqual(alternate["status"], "learned_composition")
        self.assertEqual(alternate["join"], "first_then_second")
        self.assertEqual(self.core.status()["native_composed_rules"], 2)
        result = self.core.reason_auto(
            domain="mixed-transfer", task_ref="new-conflict",
            query=question([("R", 3), ("S", 5), ("T", 8)],
                           [("R", 6), ("S", 2), ("T", 4)]))
        self.assertEqual(result["status"], "abstain")
        self.assertEqual(result["reason"], "conflicting_or_inapplicable_compositions")
        self.assertIsNone(result["answer"])

    def test_wrong_structure_and_missing_join_match_fail_closed(self):
        self.seed_parents()
        self.assertEqual(self.train()["status"], "learned_composition")
        q = question([("A", 3), ("B", 5), ("C", 8)],
                     [("K", 4), ("L", 9), ("M", 6)])
        result = self.core.reason_auto(
            domain="mixed-transfer", task_ref="missing-label", query=q)
        self.assertEqual(result["status"], "abstain")
        self.assertEqual(result["reason"], "conflicting_or_inapplicable_compositions")
        other = self.core.reason_auto(
            domain="mixed-transfer", task_ref="wrong-format",
            query='{"parts": ["tags A2 B9 C5", "unknown free text"]}')
        self.assertEqual(other["status"], "abstain")
        self.assertEqual(self.core.status()["native_composed_rules"], 1)

    def test_registered_in_native_runtime_and_never_calls_model(self):
        self.seed_parents()
        self.train()
        class Inbox:
            def __init__(self):
                self.handlers = {}
            def register(self, name, handler):
                self.handlers[name] = handler
        box = Inbox()
        register_native_reasoning_handlers(box, self.core)
        self.assertIn("reasoning_learn_composition", box.handlers)
        self.assertIn("reasoning_composed", box.handlers)
        self.assertIn("reasoning_auto", box.handlers)
        self.assertFalse(self.core.status()["model_configured"])


if __name__ == "__main__":
    unittest.main()
