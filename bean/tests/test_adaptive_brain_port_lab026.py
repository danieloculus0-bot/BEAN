"""Native BEAN strategy decisions: no Ollama, HTTP, or language-model calls."""
from __future__ import annotations

import tempfile
from pathlib import Path
import unittest

from bean.learning.experimental import ExperienceBank, Lesson
from bean.learning.brain_port import (
    record_observed_outcomes, choose_from_outcomes, brain_decision,
    connector_presentation_packet,
)


class NativeBrainPortTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.db = Path(tmp.name) / "brain.sqlite"
        self.bank = ExperienceBank(self.db)
        self.addCleanup(self.bank.close)
        for arm in ("reflection", "skill", "prompt"):
            self.bank.add(Lesson(arm + "-sorting", arm, "sorting",
                                 arm + " learned pattern",
                                 ("fixture:development:" + arm,),
                                 "Development-only sample"))
        self.bank.add(Lesson("welding-reference", "reflection", "welding",
                             "unrelated weld rule", ("fixture:development:welding",),
                             "Unrelated development sample"))

    @staticmethod
    def outcomes(reflection_wins=True):
        rows = []
        for task in ("selection-A", "selection-B"):
            for arm in ("cold", "reflection", "skill", "prompt", "placebo"):
                rows.append({
                    "task_id": task, "arm": arm, "replicate": 0,
                    "passed": bool(arm == "reflection" and reflection_wins),
                    "evidence_ref": "host-receipt:" + task + ":" + arm,
                })
        return rows

    def test_bean_selects_and_replays_without_any_model(self):
        decision = choose_from_outcomes(
            self.bank, domain="sorting", rows=self.outcomes(),
            evaluator_id="offline-benchmark-v1", dataset_id="selection-only-v1")
        self.assertEqual(decision["arm"], "reflection")
        self.assertEqual(decision["provider_kind"], "observed_outcomes")
        self.assertEqual(decision["model_id"], "no_language_model")
        packet = brain_decision(self.bank, domain="sorting", task_ref="task-19")
        self.assertEqual(packet["selected_strategy"], "reflection")
        self.assertEqual(packet["lessons"][0]["evidence_refs"],
                         ["fixture:development:reflection"])
        self.assertFalse(packet["model_invoked"])
        self.assertFalse(packet["host_action_executed"])
        presentation = connector_presentation_packet(packet)
        self.assertEqual(presentation["mode"], "render_only")
        self.assertEqual(presentation["decision"], packet)

        # A fresh process can recover the selection using the same SQLite file.
        self.bank.close()
        replay = ExperienceBank(self.db)
        try:
            self.assertEqual(brain_decision(
                replay, domain="sorting", task_ref="task-after-restart"
            )["selected_strategy"], "reflection")
        finally:
            replay.close()

    def test_winner_not_forced_if_no_observed_gain(self):
        selection = choose_from_outcomes(
            self.bank, domain="sorting", rows=self.outcomes(reflection_wins=False),
            evaluator_id="host-v1", dataset_id="selection-only")
        self.assertEqual(selection["arm"], "cold")
        packet = brain_decision(self.bank, domain="sorting", task_ref="case")
        self.assertEqual(packet["lessons"], [])

    def test_missing_or_duplicate_evidence_does_not_create_a_trial(self):
        original = len(self.bank.journal.events())
        rows = self.outcomes()
        for corrupt in (rows[:-1], rows + [rows[0]], [
            {**r, "passed": 1} if r["arm"] == "cold" else r
            for r in rows], [
            {**r, "evidence_ref": ""} if r["arm"] == "cold" else r
            for r in rows]):
            with self.assertRaises(ValueError):
                record_observed_outcomes(
                    self.bank, domain="sorting", rows=corrupt,
                    evaluator_id="host-v1", dataset_id="selection-only")
        self.assertEqual(len(self.bank.journal.events()), original)

    def test_unknown_decision_cannot_be_invented_by_connector(self):
        with self.assertRaisesRegex(ValueError, "No measured strategy"):
            brain_decision(self.bank, domain="sorting", task_ref="unknown")
        with self.assertRaises(ValueError):
            connector_presentation_packet({
                "schema": "bean.connector.presentation.v1",
                "decision_source": "invented",
            })

    def test_receipt_is_recorded_then_selected_not_reverse(self):
        receipt = record_observed_outcomes(
            self.bank, domain="sorting", rows=self.outcomes(),
            evaluator_id="host-v1", dataset_id="selection-only")
        self.assertEqual(receipt["verdict"],
                         "host_observed_results_not_independently_authenticated")
        self.assertEqual(self.bank.journal.events()[-1]["kind"], "trial")
        self.assertEqual(receipt["scores"]["reflection"], 2)
        self.assertEqual(receipt["scores"]["placebo"], 0)


if __name__ == "__main__":
    unittest.main()
