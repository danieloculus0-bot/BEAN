"""Blind holdout probes for native Core rule induction, inference and judgment.

Offline deterministic evaluation: disjoint labels/numbers, counterfactual
interventions, conflicting policies, restart, and justified abstention.
Passing shows bounded symbolic reasoning behavior, NOT open-domain AGI or
independent expertise verification. No provider or wallet API calls.
"""
from __future__ import annotations

from pathlib import Path
import random
import tempfile
import unittest

from bean.learning.reasoning_service import NativeReasoningService
from bean.learning.judgment import choose_counsel


TAG_DEV = (
    {"question": "ORCHID-7 tags A3 B9 C5", "answer": "BCA"},
    {"question": "ORCHID-7 tags X7 Q1 D5", "answer": "XDQ"},
    {"question": "ORCHID-7 tags K2 L8 M4", "answer": "LMK"},
)
GAUGE_DEV = (
    {"question": "HARBOR-4 A=12 B=7 C=19", "answer": "A"},
    {"question": "HARBOR-4 D=10 E=20 F=15", "answer": "F"},
    {"question": "HARBOR-4 G=15 H=22 J=4", "answer": "G"},
)


class BlindLocalReasoningTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.database = Path(temp.name) / "blind-core.sqlite3"
        self.core = NativeReasoningService(self.database, model=None)
        self.addCleanup(self.core.close)

    def teach(self, domain, examples):
        return self.core.learn_local(
            domain=domain, task_ref="development-only-v1",
            examples=list(examples),
            evidence_refs=["fixture:blind-development-split-v1"],
        )

    def test_unseen_tags_and_counterfactual_label_reordering(self):
        r = self.teach("tag-routing", TAG_DEV)
        self.assertEqual(r["operation"], "digit_desc")
        rng = random.Random(20261025)
        observed = set()
        for idx in range(32):
            labels = rng.sample("NOPRSTUVWYZ", 5)
            values = rng.sample(range(0, 10), 5)
            pairs = list(zip(labels, values))
            query = "NOVEL-" + str(idx) + " tags " + " ".join(
                k + str(v) for k, v in pairs)
            expect = "".join(k for k, _ in sorted(pairs, key=lambda item: -item[1]))
            answer = self.core.reason_auto(
                domain="tag-routing", task_ref="blind-" + str(idx), query=query)
            self.assertEqual(answer["status"], "locally_solved")
            self.assertEqual(answer["answer"], expect)
            self.assertIn("apply:digit_desc", answer["trace"])
            self.assertFalse(answer["model_invoked"])
            self.assertFalse(answer["verified_outcome"])
            observed.add(answer["receipt_id"])
        self.assertEqual(len(observed), 32)
        self.assertEqual(self.core.status()["native_symbolic_inferences"], 32)

        first = self.core.reason_local(
            domain="tag-routing", task_ref="intervention-a",
            query="NOVEL-EDIT tags A1 B8 C4")
        altered = self.core.reason_local(
            domain="tag-routing", task_ref="intervention-b",
            query="NOVEL-EDIT tags A9 B2 C4")
        self.assertEqual(first["answer"], "BCA")
        self.assertEqual(altered["answer"], "ACB")
        self.assertNotEqual(first["answer"], altered["answer"])

        self.core.close()
        revived = NativeReasoningService(self.database, model=None)
        try:
            again = revived.reason_auto(
                domain="tag-routing", task_ref="post-restart",
                query="NOVEL-POST tags P2 Q9 R5")
            self.assertEqual(again["status"], "locally_solved")
            self.assertEqual(again["answer"], "QRP")
            self.assertFalse(again["model_invoked"])
        finally:
            revived.close()

    def test_unseen_measurements_negative_values_and_honest_abstain(self):
        result = self.teach("gauge", GAUGE_DEV)
        self.assertEqual(result["operation"], "median")
        rng = random.Random(7331)
        for i in range(24):
            values = rng.sample(range(-70, 90), 3)
            labels = rng.sample("KLMNPRSTUV", 3)
            samples = list(zip(labels, values))
            result = self.core.reason_local(
                domain="gauge", task_ref="heldout-" + str(i),
                query="HARBOR-UNSEEN " + " ".join(
                    k + "=" + str(v) for k, v in samples))
            self.assertEqual(result["status"], "locally_solved")
            self.assertEqual(result["answer"],
                sorted(samples, key=lambda item: item[1])[1][0])
        unknown = self.core.reason_auto(
            domain="gauge", task_ref="unknown-domain-grammar",
            query="What caused the customer return?")
        self.assertEqual(unknown["status"], "abstain")
        self.assertIsNone(unknown["answer"])
        even = self.core.reason_local(
            domain="gauge", task_ref="unsupported-even-median",
            query="HARBOR-4 A=3 B=8 C=5 D=11")
        self.assertEqual(even["status"], "abstain")
        wrong_domain = self.core.reason_local(
            domain="unknown", task_ref="same-structure",
            query="HARBOR-4 A=3 B=8 C=5")
        self.assertEqual(wrong_domain["status"], "abstain")

    def test_conflicting_retained_rules_refuse_to_pick_one(self):
        r = self.teach("contradiction-domain", TAG_DEV)
        self.assertEqual(r["operation"], "digit_desc")
        new_dev = [
            {"question": "SORT A9 B2 C5", "answer": "ABC"},
            {"question": "SORT D4 E8 F1", "answer": "DEF"},
            {"question": "SORT M7 N1 P6", "answer": "MNP"},
        ]
        opposing = self.teach("contradiction-domain", new_dev)
        self.assertEqual(opposing["status"], "learned_local_rule")
        self.assertEqual(opposing["operation"], "letter_asc")
        heldout = self.core.reason_auto(
            domain="contradiction-domain", task_ref="heldout-conflict",
            query="SORT Z3 Y8 X1")
        self.assertEqual(heldout["status"], "abstain")
        self.assertEqual(heldout["reason"], "conflicting_or_inapplicable_rules")
        self.assertIsNone(heldout["answer"])
        self.assertEqual(self.core.status()["native_symbolic_rules"], 2)


class EvidenceCounselTests(unittest.TestCase):
    def test_existing_good_answer_beats_new_self_guess_and_uncertainty_defers(self):
        def option(kind, answer, name, **kwargs):
            return {
                "kind": kind, "answer": answer, "source_ref": name,
                "evidence_refs": ["host:attested-evidence"],
                "confidence": kwargs.get("confidence", "high"),
                "adequate": kwargs.get("adequate", True),
                "in_scope": True, "current": True, "source_checked": True,
                "qualified": kind == "expert", "corroborated": kwargs.get(
                    "corroborated", True),
            }

        established = option("established", "Use existing validated procedure", "SOP")
        self_guess = option("self", "Invent a new algorithm", "BEAN")
        expert = option("expert", "Use subject-matter expert counsel", "SME")
        for values in ([self_guess, expert, established],
                       [expert, established, self_guess]):
            got = choose_counsel(
                domain="inspection", task_ref="blind-case", query="Select approach",
                candidates=values)
            self.assertEqual(got["decision"], "adopt")
            self.assertEqual(got["answer"], established["answer"])
            self.assertFalse(got["external_truth_verified"])
            self.assertEqual(got["source_metadata_origin"],
                             "host_attested_not_independently_authenticated")

        defer = choose_counsel(
            domain="inspection", task_ref="conflict-case", query="Proceed?",
            stakes="high", conflicting_evidence=True,
            candidates=[established, expert])
        self.assertEqual(defer["decision"], "defer")
        self.assertIsNone(defer["answer"])
        unsupported = choose_counsel(
            domain="inspection", task_ref="weak-expert", query="Proceed?",
            stakes="high",
            candidates=[option("expert", "Unverified advice", "SME",
                               corroborated=False)])
        self.assertEqual(unsupported["decision"], "defer")


if __name__ == "__main__":
    unittest.main()
