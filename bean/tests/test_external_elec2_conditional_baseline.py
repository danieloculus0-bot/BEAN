"""Review-only Elec2 falsification: budget-matched online conditional-frequency learner.

No production BEAN policy or memory store is modified. A Laplace-smoothed
source-conditional Bernoulli predictor learns only from four calibration labels
and four predeclared delayed probes, matching the feedback-gated baselines.
Scorer-only outcomes never enter its state. Real Elec2 is opt-in in CI.
"""
from __future__ import annotations

from hashlib import sha256
import json
import os
import sys
import unittest

from bean.tests.test_cross_domain_drift_probes import PROBE_INDICES
from bean.tests.test_external_elec2_transfer import _fetch, _parse_arff, _run

SCHEMA = "bean.external_elec2_conditional_control.v1"
EXPECTED_DATA_SHA = "2d86fbc74c69a5c04bcde0119bce280dd6d8efa0115987edc75b77ccf024d7f2"


def _digest(obj):
    return sha256(json.dumps(obj, sort_keys=True, separators=(",", ":"),
                             allow_nan=False).encode("utf-8")).hexdigest()


def _new_counts():
    return {"flip": [1, 1], "hold": [1, 1]}  # fixed Beta(1,1) prior per source


def _learn(counts, source, target):
    counts[source][int(target == "flip")] += 1


def _choose(counts, source):
    # Predeclared tie: hold. No labels beyond disclosed observations.
    return "flip" if counts[source][1] > counts[source][0] else "hold"


def _window(data, start):
    if len(data[start:start + 24]) != 24:
        raise ValueError("incomplete chronological window")
    counts = _new_counts()
    for source, target in data[start:start + 4]:
        _learn(counts, source, target)
    initial = {key: list(value) for key, value in counts.items()}
    cases = []
    for i, (source, target) in enumerate(data[start + 4:start + 24]):
        before = {key: list(value) for key, value in counts.items()}
        predicted = _choose(counts, source)
        probe = i in PROBE_INDICES
        disclosed = target if probe else None
        if probe:
            _learn(counts, source, disclosed)
        case = {
            "i": i, "source_proxy": source,
            "prediction_before_feedback": predicted,
            "feedback_observed": disclosed,
            "scorer_only_target": target,
            "is_feedback_probe": probe,
            "counts_before": before,
            "counts_after": {key: list(value) for key, value in counts.items()},
        }
        case["sha256"] = _digest(case)
        cases.append(case)
    correct = sum(c["prediction_before_feedback"] == c["scorer_only_target"]
                  for c in cases if not c["is_feedback_probe"])
    return {"start_index": start, "calibration": data[start:start + 4],
            "initial_counts": initial, "final_counts": counts,
            "feedback_labels": 8, "scored_cases": 16, "correct": correct,
            "cases": cases}


def _replay(window):
    counts = _new_counts()
    for source, target in window["calibration"]:
        _learn(counts, source, target)
    if counts != window["initial_counts"]:
        raise AssertionError("calibration state mismatch")
    for case in window["cases"]:
        if case["sha256"] != _digest({k: v for k, v in case.items() if k != "sha256"}):
            raise AssertionError("case receipt digest mismatch")
        if counts != case["counts_before"]:
            raise AssertionError("predecision state mismatch")
        if _choose(counts, case["source_proxy"]) != case["prediction_before_feedback"]:
            raise AssertionError("prediction replay mismatch")
        if case["is_feedback_probe"]:
            _learn(counts, case["source_proxy"], case["feedback_observed"])
        elif case["feedback_observed"] is not None:
            raise AssertionError("scorer-only label disclosed")
        if counts != case["counts_after"]:
            raise AssertionError("postfeedback state mismatch")
    if counts != window["final_counts"]:
        raise AssertionError("final state mismatch")
    return True


def _report(data, dataset_sha):
    base = _run(data, dataset_sha)
    periods = {}
    for name, original in base["periods"].items():
        windows = [_window(data, w["start_index"]) for w in original["windows"]]
        if not all(_replay(w) for w in windows):
            raise AssertionError("replay failed")
        scores = [w["correct"] for w in windows]
        paired = [s - w["scores"]["rolling_four"]
                  for s, w in zip(scores, original["windows"])]
        periods[name] = {
            "mean_correct_out_of_16": sum(scores) / len(scores),
            "rolling_four_mean_correct_out_of_16": original["mean_correct_out_of_16"]["rolling_four"],
            "paired_conditional_minus_rolling": paired,
            "windows": windows,
        }
    result = {
        "schema": SCHEMA, "source_sha": os.environ.get("BEAN_SOURCE_SHA", "not_supplied"),
        "dataset_url": base["dataset_url"], "dataset_sha256": dataset_sha,
        "dataset_rows": len(data), "source_evaluation_schema": base["schema"],
        "feedback_budget_per_window": 8, "scored_cases_per_window": 16,
        "model": "Beta(1,1) source-conditional counts, fixed tie=hold, no hyperparameter fitting",
        "periods": periods,
        "limitations": [
            "Only one external historical electricity dataset; not cross-domain intelligence",
            "Source proxy is a price comparison, not BEAN semantic retrieval",
            "Small four-calibration/four-probe budget; labels never update from scoring cases",
            "Chronological windows within one dataset are correlated, not independent domains",
            "JSON replay checks an isolated test policy, not a native Jetson restart",
            "No model/provider runtime or canonical BEAN memory modified",
        ],
    }
    result["report_sha256"] = _digest(result)
    return result


class ConditionalFrequencyControls(unittest.TestCase):
    def test_feedback_budget_and_restart_replay(self):
        data = [("flip" if i % 2 else "hold", "flip" if i % 3 else "hold")
                for i in range(24)]
        w = _window(data, 0)
        self.assertEqual((w["feedback_labels"], w["scored_cases"]), (8, 16))
        self.assertTrue(_replay(json.loads(json.dumps(w))))
        self.assertEqual(w, _window(data, 0))

    def test_hidden_labels_cannot_change_predictions_or_learning(self):
        data = [("flip" if i % 2 else "hold", "flip" if i % 3 else "hold")
                for i in range(24)]
        changed = list(data)
        for i in range(20):
            if i not in PROBE_INDICES:
                source, label = changed[4 + i]
                changed[4 + i] = (source, "hold" if label == "flip" else "flip")
        a, b = _window(data, 0), _window(changed, 0)
        self.assertEqual(a["final_counts"], b["final_counts"])
        for x, y in zip(a["cases"], b["cases"]):
            for key in ("prediction_before_feedback", "feedback_observed",
                        "counts_before", "counts_after"):
                self.assertEqual(x[key], y[key])
        self.assertEqual(a["correct"] + b["correct"], 16)

    def test_adversarial_negative_transfer_retained(self):
        # Calibration says flip; later hidden cases are hold. A naive learned
        # conditional majority fails rather than magically detecting drift.
        data = [("flip", "flip")] * 4 + [("flip", "hold")] * 20
        w = _window(data, 0)
        self.assertLess(w["correct"], 16)  # constant hold baseline scores 16
        self.assertTrue(_replay(w))

    @unittest.skipUnless(os.environ.get("BEAN_EXTERNAL_STREAM") == "1", "external data opt-in")
    def test_independent_elec2_conditional_control(self):
        raw = _fetch()
        dataset_sha = sha256(raw).hexdigest()
        self.assertEqual(dataset_sha, EXPECTED_DATA_SHA, "external dataset revision changed")
        report = _report(_parse_arff(raw), dataset_sha)
        self.assertEqual(report["dataset_rows"], 45312)
        self.assertEqual(set(report["periods"]), {"earlier", "later_ood"})
        self.assertEqual(report["report_sha256"], _digest({k: v for k, v in report.items()
                                                         if k != "report_sha256"}))
        self.assertTrue(all(_replay(w) for p in report["periods"].values()
                            for w in p["windows"]))


if __name__ == "__main__":
    if sys.argv[1:] == ["--report"]:
        raw = _fetch()
        dataset_sha = sha256(raw).hexdigest()
        if dataset_sha != EXPECTED_DATA_SHA:
            raise ValueError("external dataset revision changed")
        print(json.dumps(_report(_parse_arff(raw), dataset_sha),
                         sort_keys=True, indent=2))
    else:
        unittest.main()
