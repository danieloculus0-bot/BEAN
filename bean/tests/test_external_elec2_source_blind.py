"""Review-only Elec2 source-blind temporal controls, with matched feedback.

Tests whether recent disclosed target labels alone explain performance attributed
to price-proxy transfer. Reuses the existing external Elec2 stream, chronological
windows and baseline scores. No production BEAN memory or policy changes.

python -m unittest -v bean.tests.test_external_elec2_source_blind
BEAN_EXTERNAL_STREAM=1 python -m bean.tests.test_external_elec2_source_blind --report
"""
from __future__ import annotations

from hashlib import sha256
import json
import os
import sys
import unittest

from bean.tests.test_cross_domain_drift_probes import PROBE_INDICES
from bean.tests.test_external_elec2_transfer import _fetch, _parse_arff, _run
from bean.tests.test_external_elec2_conditional_baseline import (
    EXPECTED_DATA_SHA, _digest, _window as _conditional_window,
    _replay as _conditional_replay,
)

SCHEMA = "bean.external_elec2_source_blind_control.v1"
POLICIES = ("last_disclosed_label", "recent_four_majority")


def _decide(history):
    """Predict using disclosed target history only, never the source proxy."""
    if not history or any(x not in ("flip", "hold") for x in history):
        raise ValueError("invalid disclosed label history")
    recent = history[-4:]
    return {
        "last_disclosed_label": recent[-1],
        "recent_four_majority": (
            "flip" if recent.count("flip") > recent.count("hold") else "hold"
        ),  # fixed tie = hold
    }


def _window(data, start):
    if len(data[start:start + 24]) != 24:
        raise ValueError("incomplete chronological window")
    calibration = [target for _, target in data[start:start + 4]]
    history = list(calibration)
    cases = []
    for i, (source, target) in enumerate(data[start + 4:start + 24]):
        before = list(history)
        predictions = _decide(before)  # source is deliberately not an input
        probe = i in PROBE_INDICES
        disclosed = target if probe else None
        if probe:
            history = (history + [disclosed])[-4:]
        case = {
            "i": i, "source_proxy": source,
            "history_before": before, "predictions": predictions,
            "feedback_observed": disclosed, "scorer_only_target": target,
            "is_feedback_probe": probe, "history_after": list(history),
        }
        case["sha256"] = _digest(case)
        cases.append(case)
    scores = {
        name: sum(c["predictions"][name] == c["scorer_only_target"]
                  for c in cases if not c["is_feedback_probe"])
        for name in POLICIES
    }
    return {
        "start_index": start, "calibration_targets": calibration,
        "final_history": history, "feedback_labels": 4 + len(PROBE_INDICES),
        "scored_cases": 20 - len(PROBE_INDICES), "scores": scores,
        "cases": cases,
    }


def _replay(window):
    """Reconstruct decisions after a serialized restart from disclosed labels."""
    history = list(window["calibration_targets"])
    if len(history) != 4:
        raise AssertionError("wrong calibration budget")
    observed_probes = 0
    for i, case in enumerate(window["cases"]):
        if case["i"] != i:
            raise AssertionError("case order mismatch")
        if case["sha256"] != _digest({k: v for k, v in case.items()
                                      if k != "sha256"}):
            raise AssertionError("case receipt digest mismatch")
        if case["history_before"] != history:
            raise AssertionError("history before prediction mismatch")
        if case["predictions"] != _decide(history):
            raise AssertionError("decision replay mismatch")
        if case["is_feedback_probe"] != (i in PROBE_INDICES):
            raise AssertionError("feedback schedule mismatch")
        if case["is_feedback_probe"]:
            observed = case["feedback_observed"]
            if observed not in ("flip", "hold"):
                raise AssertionError("invalid disclosed probe label")
            history = (history + [observed])[-4:]
            observed_probes += 1
        elif case["feedback_observed"] is not None:
            raise AssertionError("scorer-only label leaked into policy")
        if case["history_after"] != history:
            raise AssertionError("history after feedback mismatch")
    if observed_probes != len(PROBE_INDICES) or history != window["final_history"]:
        raise AssertionError("feedback count or final state mismatch")
    return True


def _wins_ties_losses(values):
    return {
        "wins": sum(v > 0 for v in values),
        "ties": sum(v == 0 for v in values),
        "losses": sum(v < 0 for v in values),
    }


def _report(data, dataset_sha):
    base = _run(data, dataset_sha)
    periods = {}
    for name, original in base["periods"].items():
        windows = []
        for existing in original["windows"]:
            start = existing["start_index"]
            blind = _window(data, start)
            conditional = _conditional_window(data, start)
            if not _replay(json.loads(json.dumps(blind))):
                raise AssertionError("source-blind replay failed")
            if not _conditional_replay(conditional):
                raise AssertionError("conditional baseline replay failed")
            if blind["feedback_labels"] != conditional["feedback_labels"]:
                raise AssertionError("unmatched feedback budget")
            windows.append({
                "start_index": start,
                "source_blind": blind,
                "conditional_correct": conditional["correct"],
                "rolling_four_correct": existing["scores"]["rolling_four"],
                "constant_down_correct": existing["scores"]["constant_down"],
            })
        summary = {}
        for policy in POLICIES:
            values = [w["source_blind"]["scores"][policy] for w in windows]
            deltas = {}
            for comparator, key in (
                ("conditional_frequency", "conditional_correct"),
                ("rolling_four", "rolling_four_correct"),
                ("constant_down", "constant_down_correct"),
            ):
                paired = [value - w[key] for value, w in zip(values, windows)]
                deltas[comparator] = {
                    "per_window": paired,
                    "mean_delta_correct": sum(paired) / len(paired),
                    **_wins_ties_losses(paired),
                }
            summary[policy] = {
                "mean_correct_out_of_16": sum(values) / len(values),
                "paired_comparisons": deltas,
            }
        periods[name] = {"summary": summary, "windows": windows}
    report = {
        "schema": SCHEMA,
        "source_sha": os.environ.get("BEAN_SOURCE_SHA", "not_supplied"),
        "dataset_url": base["dataset_url"],
        "dataset_sha256": dataset_sha,
        "dataset_rows": len(data),
        "windows_per_period": 16,
        "feedback_labels_per_window": 8,
        "scored_cases_per_window": 16,
        "policy": "Last disclosed target and majority of last four disclosed targets; tie=hold",
        "periods": periods,
        "limitations": [
            "Historical Elec2 is one correlated market stream, not cross-domain intelligence",
            "No BEAN semantic recall, model inference, or learned transferable skills",
            "All adaptive policies receive four calibration and four probe labels",
            "Constant DOWN uses zero labels and is not budget matched",
            "Scorer-only targets are retained for audit but never update policy state",
            "Serialized receipt replay is not a deployed Jetson process restart",
            "No canonical event store, model, Axiom, or physical hardware changed",
        ],
    }
    report["report_sha256"] = _digest(report)
    return report


class SourceBlindControls(unittest.TestCase):
    @staticmethod
    def _fictional():
        return [("flip" if i % 2 else "hold",
                 "flip" if i % 3 else "hold") for i in range(24)]

    def test_matched_feedback_and_serialized_restart(self):
        data = self._fictional()
        first = _window(data, 0)
        self.assertEqual((first["feedback_labels"], first["scored_cases"]), (8, 16))
        self.assertTrue(_replay(json.loads(json.dumps(first))))
        self.assertEqual(first, _window(data, 0))

    def test_hidden_scoring_labels_are_not_training_data(self):
        data = self._fictional()
        changed = list(data)
        for i in range(20):
            if i not in PROBE_INDICES:
                source, target = changed[4 + i]
                changed[4 + i] = (source, "hold" if target == "flip" else "flip")
        a, b = _window(data, 0), _window(changed, 0)
        self.assertEqual(a["final_history"], b["final_history"])
        for x, y in zip(a["cases"], b["cases"]):
            for key in ("history_before", "predictions",
                        "feedback_observed", "history_after"):
                self.assertEqual(x[key], y[key])
        for policy in POLICIES:
            self.assertEqual(a["scores"][policy] + b["scores"][policy], 16)

    def test_source_proxy_cannot_affect_source_blind_predictions(self):
        data = self._fictional()
        altered = [("hold" if source == "flip" else "flip", target)
                   for source, target in data]
        a, b = _window(data, 0), _window(altered, 0)
        self.assertEqual(a["scores"], b["scores"])
        for x, y in zip(a["cases"], b["cases"]):
            self.assertEqual(x["predictions"], y["predictions"])
            self.assertEqual(x["history_after"], y["history_after"])

    def test_adversarial_change_retains_negative_evidence(self):
        data = [("flip", "flip")] * 4 + [("flip", "hold")] * 20
        result = _window(data, 0)
        self.assertLess(result["scores"]["last_disclosed_label"], 16)
        self.assertLess(result["scores"]["recent_four_majority"], 16)
        self.assertTrue(_replay(result))

    @unittest.skipUnless(os.environ.get("BEAN_EXTERNAL_STREAM") == "1",
                         "external data opt-in")
    def test_external_elec2_source_blind_comparisons(self):
        raw = _fetch()
        dataset_sha = sha256(raw).hexdigest()
        self.assertEqual(dataset_sha, EXPECTED_DATA_SHA, "dataset revision changed")
        report = _report(_parse_arff(raw), dataset_sha)
        self.assertEqual(len(report["periods"]), 2)
        for period in report["periods"].values():
            self.assertEqual(len(period["windows"]), 16)
            for window in period["windows"]:
                self.assertTrue(_replay(window["source_blind"]))
                self.assertEqual(window["source_blind"]["feedback_labels"], 8)
            for policy in POLICIES:
                for comparison in period["summary"][policy]["paired_comparisons"].values():
                    self.assertEqual(sum(comparison[k] for k in ("wins", "ties", "losses")), 16)
        self.assertEqual(
            report["report_sha256"],
            _digest({k: v for k, v in report.items() if k != "report_sha256"}),
        )


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
