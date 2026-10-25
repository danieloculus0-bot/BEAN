"""BEAN experimental strategy learning tests: actual journal replay and controls.

These are offline deterministic fixtures, not neural learning evidence.
"""
from __future__ import annotations
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from bean.learning.experimental import (
    ExperienceBank, Lesson, TrialCase, run_paired_trial,
)
from bean.learning.strategy_selection import choose_strategy
from bean.learning.live_lab026 import run_local_trial


class SourceInspiredFixture:
    provider_kind = "synthetic_fixture"
    model_id = "source-inspired-controlled-fixture-v1"

    def __init__(self, *args, **kwargs):
        self.requests = []

    def complete(self, question, context):
        self.requests.append((question, context))
        if "Use these development examples:" in question:
            return "WELD_ONLY" if "join steel" in question else "SORT_ASC"
        if question.startswith("sort ") and "SORT_ASC" in context:
            return ",".join(sorted(question[5:].split(",")))
        return "unknown"


class StrategySelectionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.bank = ExperienceBank(self.root / "policy.sqlite")
        self.addCleanup(self.bank.close)
        for arm in ("reflection", "skill", "prompt"):
            self.bank.add(Lesson(
                "sorting-" + arm, arm, "sorting", "SORT_ASC",
                ("synthetic:development",), "A mocked sorting failure"))
        self.bank.add(Lesson("unrelated", "reflection", "welding", "WELD_ONLY",
                             ("synthetic:unrelated",), "Unrelated mocked welding event"))
        self.model = SourceInspiredFixture()

    def trial(self):
        return run_paired_trial(
            bank=self.bank,
            cases=[TrialCase("sel-1", "sorting", "sort c,a", "a,c"),
                   TrialCase("sel-2", "sorting", "sort z,x", "x,z")],
            model=self.model,
            judge=lambda expected, answer: expected == answer,
            arms=("cold", "reflection", "skill", "prompt", "placebo"),
            replicates=2)

    def test_measured_reflection_skill_prompt_selection_replays_across_restart(self):
        scored = self.trial()
        choice = choose_strategy(self.bank, scored, "sorting")
        self.assertEqual(choice["arm"], "reflection")  # stable tie
        self.assertEqual(choice["scores"], {
            "cold": 0, "placebo": 0, "reflection": 4, "skill": 4, "prompt": 4,
        })
        self.assertFalse(choice["independent_learning_proof"])
        self.bank.close()
        restored = ExperienceBank(self.root / "policy.sqlite")
        try:
            self.assertEqual(restored.selected_arm("sorting"), "reflection")
            final = run_paired_trial(
                bank=restored,
                cases=[TrialCase("hold-1", "sorting", "sort q,b", "b,q")],
                model=self.model,
                judge=lambda expected, answer: expected == answer,
                arms=("cold", "placebo", "adaptive"), replicates=2)
            self.assertEqual(final["scores"], {
                "cold": 0, "placebo": 0, "adaptive": 2,
            })
            self.assertEqual(final["verdict"], "synthetic_fixture_not_learning_proof")
        finally:
            restored.close()

    def test_cannot_select_from_changed_or_unrecorded_trial_receipt(self):
        receipt = self.trial()
        altered = copy.deepcopy(receipt)
        altered["scores"]["reflection"] = 100
        with self.assertRaisesRegex(ValueError, "match BEAN"):
            choose_strategy(self.bank, altered, "sorting")
        fake = copy.deepcopy(receipt)
        fake["receipt_hash"] = "invented"
        with self.assertRaisesRegex(ValueError, "match BEAN"):
            choose_strategy(self.bank, fake, "sorting")

    def test_selection_requires_irrelevant_domain_placebo(self):
        receipt = self.trial()
        separate = ExperienceBank(self.root / "no-placebo.sqlite")
        try:
            for arm in ("reflection", "skill", "prompt"):
                separate.add(Lesson("only-" + arm, arm, "sorting",
                                    "SORT_ASC", ("synthetic:dev",), "fixture"))
            with self.assertRaisesRegex(ValueError, "recorded trial"):
                separate.record_selection({
                    "schema": "bean.lab026.strategy_choice.v1", "arm": "reflection",
                    "domain": "sorting", "source_trial_hash": "made-up"
                })
            with self.assertRaisesRegex(ValueError, "match BEAN"):
                choose_strategy(separate, receipt, "sorting")
        finally:
            separate.close()


class LiveOrchestrationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.dev = {
            "schema": "bean.lab026.development.v1",
            "cases": [
                {"id": "dev-1", "domain": "sorting", "question": "sort k,e",
                 "observed": "unknown", "expected": "e,k", "evidence_ref": "dev:a"},
                {"id": "dev-2", "domain": "sorting", "question": "sort c,b",
                 "observed": "unknown", "expected": "b,c", "evidence_ref": "dev:b"},
                {"id": "unrelated-1", "domain": "welding", "question": "join steel plates",
                 "observed": "unknown", "expected": "welded", "evidence_ref": "dev:c"},
            ],
        }
        self.selection = {
            "schema": "bean.lab026.selection.v1",
            "cases": [
                {"id": "selection-1", "domain": "sorting", "question": "sort f,a", "expected": "a,f"},
                {"id": "selection-2", "domain": "sorting", "question": "sort z,m", "expected": "m,z"},
            ],
        }
        self.holdout = {
            "schema": "bean.lab026.holdout.v1",
            "cases": [
                {"id": "hold-1", "domain": "sorting", "question": "sort t,q", "expected": "q,t"},
                {"id": "hold-2", "domain": "sorting", "question": "sort n,l", "expected": "l,n"},
            ],
        }

    def files(self, *, selection=None):
        for name, data in (("development", self.dev), ("holdout", self.holdout),
                           ("selection", selection if selection is not None else self.selection)):
            (self.root / (name + ".json")).write_text(json.dumps(data))
        return (self.root / "development.json", self.root / "selection.json",
                self.root / "holdout.json")

    def test_from_three_source_approaches_to_restarted_holdout_receipt(self):
        dev, selected, hold = self.files()
        with patch("bean.learning.live_lab026.LocalOllamaTrialModel",
                   SourceInspiredFixture):
            result = run_local_trial(
                development_path=dev, selection_path=selected,
                holdout_path=hold, output=self.root / "run",
                domain="sorting", replicates=2)
        self.assertEqual(result["selected_strategy"]["arm"], "reflection")
        self.assertTrue(result["selection_survived_restart"])
        self.assertTrue(result["placebo_context_present"])
        self.assertEqual(result["trial_receipt"]["scores"]["adaptive"], 4)
        self.assertEqual(result["trial_receipt"]["scores"]["cold"], 0)
        self.assertEqual(result["trial_receipt"]["scores"]["placebo"], 0)
        self.assertFalse(result["learning_proven"])
        bank = ExperienceBank(self.root / "run" / "persistent_adaptive_ledger.sqlite")
        try:
            self.assertEqual(bank.selected_arm("sorting"), "reflection")
            self.assertEqual(len(bank.lessons()), 6)
        finally:
            bank.close()

    def test_reject_same_questions_under_different_ids_across_splits(self):
        dev, selected, hold = self.files()
        self.selection["cases"][0]["question"] = "sort k,e"
        self.files(selection=self.selection)
        with self.assertRaisesRegex(ValueError, "distinct from development"):
            run_local_trial(development_path=dev, selection_path=selected,
                            holdout_path=hold, output=self.root / "reject",
                            domain="sorting")

    def test_reject_adaptive_selection_without_irrelevant_placebo(self):
        self.dev["cases"] = self.dev["cases"][:2]
        dev, selected, hold = self.files()
        with patch("bean.learning.live_lab026.LocalOllamaTrialModel",
                   SourceInspiredFixture):
            with self.assertRaisesRegex(ValueError, "requires unrelated-domain"):
                run_local_trial(development_path=dev, selection_path=selected,
                                holdout_path=hold, output=self.root / "reject",
                                domain="sorting")


if __name__ == "__main__":
    unittest.main()
