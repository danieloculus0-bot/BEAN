"""Prequential, budgeted feedback probe for synthetic cross-domain drift.

python -m unittest -v bean.tests.test_cross_domain_drift_probes
python -m bean.tests.test_cross_domain_drift_probes --report

This is a toy policy and constructed target oracle, NOT BEAN Core's deployed
decision logic, learned AGI, or a real-world benchmark. Source precedents are
retrieved by the existing native service and replayed from its SQLite journal.
"""
from __future__ import annotations

from hashlib import sha256
import json
import os
import sys
import unittest

from bean.tests.test_cross_domain_negative_transfer import SEEDS, _cohort, _opposite
from bean.tests.test_cross_domain_feedback_gate import _split, _choose, _predict

SCHEMA = "bean.synthetic_prequential_drift_probes.v1"
PROBE_INDICES = (1, 6, 11, 16)
SCENARIOS = (
    "aligned", "inverted", "reversal_at_start", "reversal_midstream",
    "single_probe_noise", "alternating_ood",
)


def _oracle(source_action, scenario, index):
    """Scorer-owned constructed outcome; never an input to a prediction."""
    invert = (
        scenario in ("inverted", "reversal_at_start")
        or (scenario == "reversal_midstream" and index >= 10)
        or (scenario == "single_probe_noise" and index == 6)
        or (scenario == "alternating_ood" and index % 2 == 1)
    )
    return _opposite(source_action) if invert else source_action


def _run_scenario(calibration, heldout, scenario):
    # The first four observations are disjoint from the streaming cases.
    feedback = [{
        "case_id": row["case_id"],
        "source_action": row["copied_action"],
        "observed_target": (
            _opposite(row["copied_action"]) if scenario == "inverted"
            else row["copied_action"]),
    } for row in calibration]
    initial = _choose(feedback)
    current = initial
    consecutive_errors = 0
    switches = []
    rows = []
    for index, row in enumerate(heldout):
        source_action = row["copied_action"]
        # All predictions happen before any target feedback is disclosed.
        decisions = {
            "no_retrieval": "hold",
            "naive_copy": source_action,
            "frozen_feedback_gate": _predict(source_action, initial),
            "online_probe_gate": _predict(source_action, current),
        }
        truth = _oracle(source_action, scenario, index)
        probe = index in PROBE_INDICES
        event = {
            "case_id": row["case_id"],
            "source_lesson_id": row["source_lesson_id"],
            "evidence_ref": row["evidence_ref"],
            "lexical_tie_count": row["tie_count"],
            "stream_index": index,
            "is_feedback_probe": probe,
            "orientation_before_feedback": current,
            "decisions_before_feedback": decisions,
            "target_revealed_to_policy": truth if probe else None,
            "scorer_target": truth,
            "correct": {name: decision == truth
                        for name, decision in decisions.items()},
        }
        if probe:
            # Feedback arrives after the probe's decision, and can only
            # influence later cases. Probe outcomes are NOT scored.
            consecutive_errors = (consecutive_errors + 1
                                  if decisions["online_probe_gate"] != truth else 0)
            if consecutive_errors >= 2:
                current = "invert" if current == "copy" else "copy"
                switches.append(index)
                consecutive_errors = 0
        event["orientation_after_feedback"] = current
        event["receipt_sha256"] = sha256(json.dumps(
            {k: v for k, v in event.items() if k != "receipt_sha256"},
            sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        rows.append(event)
    scored = [row for row in rows if not row["is_feedback_probe"]]
    names = ("no_retrieval", "naive_copy", "frozen_feedback_gate",
             "online_probe_gate")
    return {
        "initial_orientation": initial,
        "feedback_budget_calibration": len(feedback),
        "feedback_budget_stream": len(PROBE_INDICES),
        "stream_count": len(rows),
        "scored_count": len(scored),
        "switches_after_probe_indices": switches,
        "scores": {name: sum(row["correct"][name] for row in scored)
                   for name in names},
        "cases": rows,
    }


def run_report():
    # Existing _cohort uses real NativeReasoningService, SQLite reopen/replay,
    # and the original SHA-chained reasoning journal.
    source = _cohort("aligned", SEEDS["aligned"])
    calibration, heldout = _split(source)
    scenarios = {name: _run_scenario(calibration, heldout, name)
                 for name in SCENARIOS}
    payload = json.dumps(scenarios, sort_keys=True, separators=(",", ":"))
    return {
        "schema": SCHEMA,
        "source_sha": os.environ.get("BEAN_SOURCE_SHA", "not_supplied"),
        "source_cohort_seed": SEEDS["aligned"],
        "source_retrieval_restart_replay_verified": True,
        "calibration_budget": len(calibration),
        "stream_feedback_budget": len(PROBE_INDICES),
        "probe_indices_predeclared": list(PROBE_INDICES),
        "probe_decisions_excluded_from_scores": True,
        "feedback_arrives_after_prediction": True,
        "scenarios": scenarios,
        "case_sha256": sha256(payload.encode()).hexdigest(),
        "limitations": [
            "Target oracle is constructed; results cannot establish general intelligence",
            "Detector is a two-consecutive-probe-error toy orientation switch",
            "Only source retrieval has SQLite restart verification",
            "Policy state is ephemeral; no persistent online adaptation installed",
            "Probes are predetermined, not actively selected or externally sampled",
            "No external models, real Jetson, or independently sourced tasks evaluated",
        ],
    }


class PrequentialDriftProbeControls(unittest.TestCase):
    def test_budget_no_probe_leakage_and_receipt_provenance(self):
        report = run_report()
        for scenario in report["scenarios"].values():
            rows = scenario["cases"]
            self.assertEqual(len(rows), 20)
            self.assertEqual(scenario["scored_count"], 16)
            self.assertEqual(sum(r["is_feedback_probe"] for r in rows), 4)
            self.assertEqual(len({r["case_id"] for r in rows}), 20)
            self.assertTrue(all(r["source_lesson_id"].startswith("bean.lesson.")
                                and r["evidence_ref"].startswith("fixture:")
                                and r["lexical_tie_count"] == 1 for r in rows))
            self.assertTrue(all(
                (r["target_revealed_to_policy"] is not None)
                == r["is_feedback_probe"] for r in rows))
            self.assertTrue(all(len(r["receipt_sha256"]) == 64 for r in rows))
            for i, row in enumerate(rows):
                if not row["is_feedback_probe"]:
                    self.assertEqual(row["orientation_before_feedback"],
                                     row["orientation_after_feedback"])
                if i:
                    self.assertEqual(row["orientation_before_feedback"],
                                     rows[i - 1]["orientation_after_feedback"])
        self.assertTrue(report["source_retrieval_restart_replay_verified"])

    def test_reversal_gain_and_negative_controls(self):
        cases = run_report()["scenarios"]
        early = cases["reversal_at_start"]["scores"]
        late = cases["reversal_midstream"]["scores"]
        self.assertGreater(early["online_probe_gate"],
                           early["frozen_feedback_gate"])
        self.assertGreater(late["online_probe_gate"],
                           late["frozen_feedback_gate"])
        self.assertEqual(cases["aligned"]["switches_after_probe_indices"], [])
        self.assertEqual(cases["inverted"]["switches_after_probe_indices"], [])
        self.assertEqual(cases["single_probe_noise"]["switches_after_probe_indices"], [])
        self.assertEqual(cases["alternating_ood"]["switches_after_probe_indices"], [])
        self.assertEqual(cases["alternating_ood"]["scores"]["online_probe_gate"],
                         cases["alternating_ood"]["scores"]["frozen_feedback_gate"])
        self.assertTrue(cases["reversal_at_start"]["switches_after_probe_indices"])

    def test_replay_and_roundtrip(self):
        first, second = run_report(), run_report()
        self.assertEqual(first["case_sha256"], second["case_sha256"])
        self.assertEqual(first["scenarios"], second["scenarios"])
        self.assertEqual(json.loads(json.dumps(first)), first)


if __name__ == "__main__":
    if sys.argv[1:] == ["--report"]:
        print(json.dumps(run_report(), sort_keys=True, indent=2))
    else:
        unittest.main()
