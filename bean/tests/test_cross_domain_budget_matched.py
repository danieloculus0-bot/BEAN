"""Matched-feedback-budget control for BEAN's synthetic transfer drift experiments.

Run: python -m unittest -v bean.tests.test_cross_domain_budget_matched
Report: python -m bean.tests.test_cross_domain_budget_matched --report

The comparator is a four-observation rolling-majority rule. It receives
exactly the same four calibration labels and four delayed probe labels as
the existing drift gates. This is an evaluation control, NOT a Core policy,
a learned language model, an external benchmark, or a Jetson test.
"""
from __future__ import annotations

from hashlib import sha256
import json
import os
import sys
import unittest

from bean.tests.test_cross_domain_negative_transfer import SEEDS, _cohort, _opposite
from bean.tests.test_cross_domain_feedback_gate import _split, _predict
from bean.tests import test_cross_domain_stochastic_drift as drift

SCHEMA = "bean.synthetic_budget_matched_transfer.v1"
WINDOW = 4
POLICY = "rolling_four_feedback"
SEED_START = drift.SEED_START
TRIALS = drift.TRIALS


def _orientation(observations):
    """Estimate source/target relation from the last four *disclosed* labels."""
    recent = observations[-WINDOW:]
    matches = sum(source == target for source, target in recent)
    mismatches = len(recent) - matches
    return "copy" if matches > mismatches else ("invert" if mismatches > matches else "hold")


def _visible_calibration(calibration):
    return [(row["source_action"], row["observed_target"]) for row in calibration]


def _decide_visible(calibration, cases, *, prior=None):
    """No access to scorer_only_target, correct, or any future probe labels.

    The caller may resume after a simulated restart using only the last
    four disclosed observations, never a hidden scorer target.
    """
    observations = list(prior) if prior is not None else _visible_calibration(calibration)
    decisions = []
    before = []
    after = []
    for row in cases:
        source = row["decisions_before_feedback"]["naive_copy"]
        orientation = _orientation(observations)
        before.append(orientation)
        decisions.append(_predict(source, orientation))
        feedback = row["feedback_observed"]
        if feedback is not None:
            observations.append((source, feedback))
            observations = observations[-WINDOW:]
        after.append(_orientation(observations))
    return {
        "decisions": decisions,
        "orientation_before": before,
        "orientation_after": after,
        "recent_observations": observations[-WINDOW:],
    }


def _score_trial(trial):
    cases = trial["cases"]
    projected = _decide_visible(trial["calibration"], cases)
    # The scorer reads hidden labels only AFTER the complete decision sequence.
    correct = sum(
        predicted == row["scorer_only_target"]
        for predicted, row in zip(projected["decisions"], cases)
        if not row["is_feedback_probe"]
    )
    labels = len(trial["calibration"]) + sum(
        row["feedback_observed"] is not None for row in cases
    )
    if labels != 8:
        raise AssertionError("feedback budget drifted")
    receipts = []
    for row, prediction, before, after in zip(
        cases, projected["decisions"], projected["orientation_before"],
        projected["orientation_after"],
    ):
        receipt = {
            "case_id": row["case_id"],
            "source_lesson_id": row["source_lesson_id"],
            "evidence_ref": row["evidence_ref"],
            "source_receipt_sha256": row["receipt_sha256"],
            "stream_index": row["stream_index"],
            "is_feedback_probe": row["is_feedback_probe"],
            "orientation_before": before,
            "prediction_before_feedback": prediction,
            "feedback_observed": row["feedback_observed"],
            "orientation_after": after,
            "scorer_only_target": row["scorer_only_target"],
            "correct_if_scored": None if row["is_feedback_probe"]
                else prediction == row["scorer_only_target"],
        }
        receipt["sha256"] = sha256(json.dumps(
            receipt, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        receipts.append(receipt)
    return {
        "seed": trial["seed"],
        "scenario": trial["scenario"],
        "score": correct,
        "labels_consumed": labels,
        "net_utility": correct - labels * drift.COST_PER_LABEL,
        "comparators": dict(trial["scores"]),
        "paired_delta_vs_two_error": correct - trial["scores"]["two_error_probe_gate"],
        "paired_delta_vs_one_error": correct - trial["scores"]["one_error_probe_gate"],
        "paired_delta_vs_frozen": correct - trial["scores"]["frozen_feedback_gate"],
        "receipts": receipts,
    }


def run_report():
    # Native _cohort exercises real BEAN retrieval, SQLite close/reopen,
    # and the existing ExperienceBank SHA journal replay assertions.
    calibration, heldout = _split(_cohort("aligned", SEEDS["aligned"]))
    scenarios = {}
    for scenario in drift.SCENARIOS:
        trials = [
            _score_trial(drift._trial(calibration, heldout, scenario, SEED_START + seed))
            for seed in range(TRIALS)
        ]
        scores = [row["score"] for row in trials]
        scenarios[scenario] = {
            "trials": trials,
            "mean_correct_out_of_16": round(sum(scores) / len(scores), 5),
            "mean_paired_delta_vs_two_error": round(
                sum(t["paired_delta_vs_two_error"] for t in trials) / len(trials), 5),
            "mean_paired_delta_vs_one_error": round(
                sum(t["paired_delta_vs_one_error"] for t in trials) / len(trials), 5),
            "wins_ties_losses_vs_two_error": [
                sum(t["paired_delta_vs_two_error"] > 0 for t in trials),
                sum(t["paired_delta_vs_two_error"] == 0 for t in trials),
                sum(t["paired_delta_vs_two_error"] < 0 for t in trials),
            ],
        }
    payload = json.dumps(scenarios, sort_keys=True, separators=(",", ":"))
    return {
        "schema": SCHEMA,
        "source_sha": os.environ.get("BEAN_SOURCE_SHA", "not_supplied"),
        "native_retrieval_restart_verified": True,
        "policy": POLICY,
        "calibration_labels": 4,
        "delayed_probe_labels": 4,
        "scored_cases_per_trial": 16,
        "seed_start": SEED_START,
        "seeds_per_scenario": TRIALS,
        "case_sha256": sha256(payload.encode()).hexdigest(),
        "scenarios": scenarios,
        "limitations": [
            "Targets and drift regimes are synthetic, not independently sourced tasks",
            "Rolling-majority is a fixed heuristic, not learned general intelligence",
            "All policies share labels, but this control uses a different update rule",
            "No external model, Jetson, motor, production memory or event writes",
        ],
    }


class BudgetMatchedControls(unittest.TestCase):
    def test_causal_firewall_and_restart_replay(self):
        calibration = [
            {"source_action": "hold", "observed_target": "hold"},
            {"source_action": "flip", "observed_target": "flip"},
            {"source_action": "hold", "observed_target": "hold"},
            {"source_action": "flip", "observed_target": "flip"},
        ]
        rows = []
        for index in range(8):
            rows.append({
                "decisions_before_feedback": {"naive_copy": "hold" if index % 2 else "flip"},
                "feedback_observed": ("hold" if index % 2 else "flip")
                    if index in (1, 3, 5, 7) else None,
                "scorer_only_target": "hold",
                "correct": {"naive_copy": False},
            })
        original = _decide_visible(calibration, rows)
        changed = [dict(row, scorer_only_target="flip", correct={}) for row in rows]
        self.assertEqual(original, _decide_visible(calibration, changed))
        prefix = _decide_visible(calibration, rows[:4])
        suffix = _decide_visible(calibration, rows[4:],
                                 prior=prefix["recent_observations"])
        self.assertEqual(original["decisions"],
                         prefix["decisions"] + suffix["decisions"])
        self.assertEqual(original["recent_observations"],
                         suffix["recent_observations"])
        # Disclosed feedback is allowed to change subsequent decisions.
        flipped = [dict(row) for row in rows]
        flipped[1]["feedback_observed"] = _opposite(rows[1]["feedback_observed"])
        self.assertNotEqual(original["recent_observations"],
                            _decide_visible(calibration, flipped)["recent_observations"])

    def test_native_paired_budget_and_negative_evidence(self):
        report = run_report()
        self.assertEqual(report["calibration_labels"] + report["delayed_probe_labels"], 8)
        for scenario in report["scenarios"].values():
            self.assertEqual(len(scenario["trials"]), TRIALS)
            self.assertEqual(sum(scenario["wins_ties_losses_vs_two_error"]), TRIALS)
            for trial in scenario["trials"]:
                self.assertEqual(trial["labels_consumed"], 8)
                self.assertEqual(len(trial["receipts"]), 20)
                self.assertEqual(sum(row["correct_if_scored"] is not None
                                     for row in trial["receipts"]), 16)
                self.assertTrue(all(row["evidence_ref"].startswith("fixture:")
                                    and len(row["sha256"]) == 64
                                    for row in trial["receipts"]))
        self.assertEqual(json.loads(json.dumps(report)), report)

    def test_deterministic_case_digest(self):
        first, second = run_report(), run_report()
        self.assertEqual(first["case_sha256"], second["case_sha256"])


if __name__ == "__main__":
    if sys.argv[1:] == ["--report"]:
        print(json.dumps(run_report(), sort_keys=True, indent=2))
    else:
        unittest.main()
