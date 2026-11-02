"""Oracle-firewall negative control for BEAN's synthetic drift evaluation.

This checks whether scorer-only target labels can secretly influence decisions.
It is NOT an externally sourced benchmark, a learned model, or a Jetson result.
Run: python -m unittest -v bean.tests.test_cross_domain_oracle_firewall
Receipt: python -m bean.tests.test_cross_domain_oracle_firewall --report
"""
from __future__ import annotations

from hashlib import sha256
import json
import os
import sys
import unittest
from unittest.mock import patch

import bean.tests.test_cross_domain_stochastic_drift as drift
from bean.tests.test_cross_domain_negative_transfer import SEEDS, _cohort, _opposite
from bean.tests.test_cross_domain_feedback_gate import _split
from bean.tests.test_cross_domain_drift_probes import PROBE_INDICES

SCHEMA = "bean.synthetic_oracle_firewall.v1"
SEED = drift.SEED_START + 7
SCENARIO = "abrupt_reversal_noisy"


def _paired_runs():
    # The existing cohort exercises native BEAN retrieval and SQLite/SHA
    # journal close/reopen. All labels below are fictional scorer outputs.
    calibration, heldout = _split(_cohort("aligned", SEEDS["aligned"]))
    original_oracle = drift._target
    baseline = drift._trial(calibration, heldout, SCENARIO, SEED)

    def altered_run(flip_stream_index):
        call_count = 0

        def alternate(source, probability, rng):
            nonlocal call_count
            position = call_count
            call_count += 1
            # Consume the exact same RNG draw as the unchanged scorer.
            observed = original_oracle(source, probability, rng)
            stream_index = position - len(calibration)
            if stream_index >= 0 and flip_stream_index(stream_index):
                return _opposite(observed)
            return observed

        with patch.object(drift, "_target", side_effect=alternate):
            result = drift._trial(calibration, heldout, SCENARIO, SEED)
        if call_count != len(calibration) + len(heldout):
            raise AssertionError("oracle call budget changed")
        return result

    hidden_changed = altered_run(lambda i: i not in PROBE_INDICES)
    first_probe_changed = altered_run(lambda i: i == PROBE_INDICES[0])
    return baseline, hidden_changed, first_probe_changed


def run_report():
    baseline, hidden, probe = _paired_runs()
    cases = []
    for a, b, c in zip(baseline["cases"], hidden["cases"], probe["cases"]):
        cases.append({
            "case_id": a["case_id"],
            "source_lesson_id": a["source_lesson_id"],
            "evidence_ref": a["evidence_ref"],
            "stream_index": a["stream_index"],
            "is_feedback_probe": a["is_feedback_probe"],
            "original_scorer_target": a["scorer_only_target"],
            "hidden_label_perturbation_target": b["scorer_only_target"],
            "probe_label_perturbation_target": c["scorer_only_target"],
            "original_decisions": a["decisions_before_feedback"],
            "hidden_label_decisions": b["decisions_before_feedback"],
            "probe_label_decisions": c["decisions_before_feedback"],
            "original_receipt_sha256": a["receipt_sha256"],
            "hidden_label_receipt_sha256": b["receipt_sha256"],
            "probe_label_receipt_sha256": c["receipt_sha256"],
        })
    canonical = json.dumps(cases, sort_keys=True, separators=(",", ":"))
    return {
        "schema": SCHEMA,
        "source_sha": os.environ.get("BEAN_SOURCE_SHA", "not_supplied"),
        "scenario": SCENARIO,
        "seed": SEED,
        "feedback_probe_indices": list(PROBE_INDICES),
        "source_retrieval_restart_verified": True,
        "original_scores": baseline["scores"],
        "hidden_label_perturbation_scores": hidden["scores"],
        "probe_label_perturbation_scores": probe["scores"],
        "case_sha256": sha256(canonical.encode()).hexdigest(),
        "cases": cases,
        "limitations": [
            "Synthetic oracle perturbation, not independent task acquisition",
            "This checks evaluation leakage only, not semantic transfer",
            "Scorer labels remain in CI receipts for audit, not policy inputs",
            "No model training, device run, canonical event writes, or production policy",
        ],
    }


class OracleFirewallControls(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.baseline, cls.hidden, cls.probe = _paired_runs()

    def test_hidden_scored_labels_cannot_change_policy_actions(self):
        a, b = self.baseline, self.hidden
        self.assertEqual(a["calibration"], b["calibration"])
        self.assertEqual(a["labels_consumed"], b["labels_consumed"])
        self.assertEqual(a["switches"], b["switches"])
        self.assertEqual(len(a["cases"]), 20)
        for original, altered in zip(a["cases"], b["cases"]):
            self.assertEqual(original["case_id"], altered["case_id"])
            self.assertEqual(original["decisions_before_feedback"],
                             altered["decisions_before_feedback"])
            self.assertEqual(original["orientation_before"],
                             altered["orientation_before"])
            self.assertEqual(original["orientation_after"],
                             altered["orientation_after"])
            self.assertEqual(original["feedback_observed"],
                             altered["feedback_observed"])
            if original["is_feedback_probe"]:
                self.assertEqual(original["scorer_only_target"],
                                 altered["scorer_only_target"])
                self.assertEqual(original["receipt_sha256"],
                                 altered["receipt_sha256"])
            else:
                self.assertNotEqual(original["scorer_only_target"],
                                    altered["scorer_only_target"])
                self.assertNotEqual(original["receipt_sha256"],
                                    altered["receipt_sha256"])
                for policy in drift.POLICIES:
                    self.assertNotEqual(original["correct"][policy],
                                        altered["correct"][policy])
        for policy in drift.POLICIES:
            self.assertEqual(a["scores"][policy] + b["scores"][policy], 16)

    def test_disclosed_probe_label_changes_only_future_adaptive_state(self):
        a, c = self.baseline, self.probe
        self.assertEqual(a["calibration"], c["calibration"])
        first = PROBE_INDICES[0]
        self.assertEqual(a["cases"][first]["decisions_before_feedback"],
                         c["cases"][first]["decisions_before_feedback"])
        self.assertNotEqual(a["cases"][first]["feedback_observed"],
                            c["cases"][first]["feedback_observed"])
        self.assertNotEqual(
            a["cases"][first]["orientation_after"]["one_error_probe_gate"],
            c["cases"][first]["orientation_after"]["one_error_probe_gate"])
        self.assertNotEqual(
            a["cases"][first + 1]["orientation_before"]["one_error_probe_gate"],
            c["cases"][first + 1]["orientation_before"]["one_error_probe_gate"])
        for original, altered in zip(a["cases"], c["cases"]):
            for policy in ("no_retrieval", "naive_copy", "frozen_feedback_gate"):
                self.assertEqual(original["decisions_before_feedback"][policy],
                                 altered["decisions_before_feedback"][policy])
        self.assertEqual(a["labels_consumed"], c["labels_consumed"])

    def test_report_roundtrip_and_negative_evidence(self):
        report = run_report()
        self.assertEqual(report["schema"], SCHEMA)
        self.assertEqual(len(report["cases"]), 20)
        self.assertEqual(json.loads(json.dumps(report)), report)
        self.assertEqual(len(report["case_sha256"]), 64)
        self.assertTrue(all(row["evidence_ref"].startswith("fixture:")
                            for row in report["cases"]))


if __name__ == "__main__":
    if sys.argv[1:] == ["--report"]:
        print(json.dumps(run_report(), sort_keys=True, indent=2))
    else:
        unittest.main()
