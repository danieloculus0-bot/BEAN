"""Synthetic target-feedback test following cross-domain counterfactual twins.

Run: python -m unittest -v bean.tests.test_cross_domain_feedback_gate
Report: python -m bean.tests.test_cross_domain_feedback_gate --report

This measures a deliberately small *frozen toy policy*, not an improvement to
BEAN's native decision policy. Only four target feedback labels are available
at calibration; held-out outcomes are revealed solely to the scorer. The
retriever and its SQLite/SHA-journal restart check are reused unchanged.
"""
from __future__ import annotations

from hashlib import sha256
import json
import os
import sys
import unittest

from bean.tests.test_cross_domain_negative_transfer import (
    COUNT, SEEDS, _cohort, _opposite,
)

SCHEMA = "bean.synthetic_target_feedback_transfer.v1"
FEEDBACK_BUDGET = 4
REGIMES = ("aligned", "inverted", "reversal_ood", "unstructured")


def _split(rows):
    """Predeclare disjoint, action-balanced feedback and held-out cases."""
    by_action = {action: [row for row in rows if row["copied_action"] == action]
                 for action in ("hold", "flip")}
    if any(len(items) != COUNT // 2 for items in by_action.values()):
        raise AssertionError("Expected a balanced source cohort")
    calibration = by_action["hold"][:2] + by_action["flip"][:2]
    selected = {row["case_id"] for row in calibration}
    heldout = [row for row in rows if row["case_id"] not in selected]
    if len(calibration) != FEEDBACK_BUDGET or len(heldout) != COUNT - FEEDBACK_BUDGET:
        raise AssertionError("Feedback/held-out partition changed")
    return calibration, heldout


def _target(row, regime, *, is_feedback, heldout_inverted):
    source = row["copied_action"]
    if regime == "aligned":
        return source
    if regime == "inverted":
        return _opposite(source)
    if regime == "reversal_ood":
        return source if is_feedback else _opposite(source)
    if regime == "unstructured":
        # Two matches and two mismatches in calibration; held-out mask is
        # separately predeclared and balanced within each source action.
        if is_feedback:
            return source if row["feedback_match"] else _opposite(source)
        return _opposite(source) if row["case_id"] in heldout_inverted else source
    raise ValueError("Unknown target regime")


def _choose(feedback):
    """Frozen after exactly four observed source/target action pairs."""
    if len(feedback) != FEEDBACK_BUDGET:
        raise ValueError("Incorrect target feedback budget")
    matches = sum(row["source_action"] == row["observed_target"]
                  for row in feedback)
    if matches == FEEDBACK_BUDGET:
        return "copy"
    if matches == 0:
        return "invert"
    return "hold"


def _predict(source_action, policy):
    if policy == "copy":
        return source_action
    if policy == "invert":
        return _opposite(source_action)
    if policy == "hold":
        return "hold"
    raise ValueError("Unknown policy")


def run_report():
    # NativeReasoningService.recall_analogies is invoked here; _cohort also
    # closes/reopens its real SQLite ExperienceBank and checks SHA replay.
    rows = _cohort("aligned", SEEDS["aligned"])
    calibration, heldout = _split(rows)
    # Keep the mixed regime deterministic without deriving its target labels
    # from lexical match quality. Five flips per source-action stratum.
    heldout_inverted = {
        row["case_id"]
        for action in ("hold", "flip")
        for row in [r for r in heldout if r["copied_action"] == action][:5]
    }
    regimes = {}
    for regime in REGIMES:
        feedback = []
        for index, row in enumerate(calibration):
            tagged = dict(row, feedback_match=(index % 2 == 0))
            feedback.append({
                "case_id": row["case_id"],
                "source_lesson_id": row["source_lesson_id"],
                "evidence_ref": row["evidence_ref"],
                "source_action": row["copied_action"],
                "observed_target": _target(
                    tagged, regime, is_feedback=True,
                    heldout_inverted=heldout_inverted),
            })
        learned_choice = _choose(feedback)
        scored = []
        for row in heldout:
            truth = _target(row, regime, is_feedback=False,
                            heldout_inverted=heldout_inverted)
            decisions = {
                "no_retrieval": "hold",
                "naive_copy": row["copied_action"],
                "feedback_gate": _predict(row["copied_action"], learned_choice),
            }
            scored.append({
                "case_id": row["case_id"],
                "source_lesson_id": row["source_lesson_id"],
                "evidence_ref": row["evidence_ref"],
                "tie_count": row["tie_count"],
                "hidden_target_revealed_after_decision": truth,
                "decisions": decisions,
                "correct": {name: action == truth
                            for name, action in decisions.items()},
            })
        scores = {name: sum(row["correct"][name] for row in scored)
                  for name in ("no_retrieval", "naive_copy", "feedback_gate")}
        regimes[regime] = {
            "feedback": feedback,
            "frozen_feedback_policy": learned_choice,
            "heldout_cases": scored,
            "scores": scores,
            "heldout_count": len(scored),
        }
    payload = json.dumps(regimes, sort_keys=True, separators=(",", ":"))
    return {
        "schema": SCHEMA,
        "source_sha": os.environ.get("BEAN_SOURCE_SHA", "not_supplied"),
        "source_cohort_seed": SEEDS["aligned"],
        "feedback_budget_per_regime": FEEDBACK_BUDGET,
        "heldout_cases_per_regime": COUNT - FEEDBACK_BUDGET,
        "retrieval_budget_per_case": 1,
        "oracle_access": "feedback_only_during_calibration; heldout_scoring_only",
        "source_retrieval_restart_replay_verified": True,
        "regimes": regimes,
        "case_sha256": sha256(payload.encode()).hexdigest(),
        "limitations": [
            "All targets are synthetic, deliberately constructed, and not blind external tasks",
            "One-bit orientation adaptation, not BEAN policy learning or model training",
            "Stationary regimes favor the toy gate by construction",
            "Post-calibration reversal defeats the gate; no drift detector is implemented",
            "Source retrieval replay is real local SQLite in CI, not Jetson execution",
        ],
    }


class TargetFeedbackTransferControls(unittest.TestCase):
    def test_disjoint_budget_and_provenance(self):
        report = run_report()
        for item in report["regimes"].values():
            feedback = item["feedback"]
            heldout = item["heldout_cases"]
            self.assertEqual(len(feedback), FEEDBACK_BUDGET)
            self.assertEqual(len(heldout), COUNT - FEEDBACK_BUDGET)
            self.assertFalse({r["case_id"] for r in feedback} &
                             {r["case_id"] for r in heldout})
            self.assertTrue(all(row["source_lesson_id"].startswith("bean.lesson.")
                                and row["evidence_ref"].startswith("fixture:")
                                and row["tie_count"] == 1 for row in heldout))
            self.assertEqual(set(item["scores"]),
                             {"no_retrieval", "naive_copy", "feedback_gate"})
        self.assertTrue(report["source_retrieval_restart_replay_verified"])

    def test_stationary_benefit_and_nonstationary_failure_are_retained(self):
        report = run_report()["regimes"]
        expected = {
            "aligned": ("copy", 10, 20, 20),
            "inverted": ("invert", 10, 0, 20),
            "reversal_ood": ("copy", 10, 0, 0),
            "unstructured": ("hold", 10, 10, 10),
        }
        for regime, (choice, baseline, naive, gated) in expected.items():
            item = report[regime]
            self.assertEqual(item["frozen_feedback_policy"], choice)
            self.assertEqual(item["scores"], {
                "no_retrieval": baseline,
                "naive_copy": naive,
                "feedback_gate": gated,
            })

    def test_replay_determinism_and_report_roundtrip(self):
        first, second = run_report(), run_report()
        self.assertEqual(first["case_sha256"], second["case_sha256"])
        self.assertEqual(first["regimes"], second["regimes"])
        self.assertEqual(json.loads(json.dumps(first)), first)
        with self.assertRaises(ValueError):
            _choose([])


if __name__ == "__main__":
    if sys.argv[1:] == ["--report"]:
        print(json.dumps(run_report(), sort_keys=True, indent=2))
    else:
        unittest.main()
