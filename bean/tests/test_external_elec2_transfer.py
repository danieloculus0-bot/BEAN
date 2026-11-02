"""Read-only external-stream falsification of BEAN's toy transfer gates.

Usage: python -m unittest -v bean.tests.test_external_elec2_transfer
       BEAN_EXTERNAL_STREAM=1 python -m bean.tests.test_external_elec2_transfer --report

The independently collected Elec2 stream is ODC-PDDL on DataHub/OpenML.
No dataset rows are committed. These are simple deterministic heuristics, NOT
BEAN model inference, native semantic transfer, or a Jetson benchmark.
"""
from __future__ import annotations

import csv
from hashlib import sha256
import json
import os
import sys
import unittest
from urllib.request import Request, urlopen

from bean.tests.test_cross_domain_budget_matched import _orientation
from bean.tests.test_cross_domain_feedback_gate import _predict
from bean.tests.test_cross_domain_stochastic_drift import _update, _replay
from bean.tests.test_cross_domain_drift_probes import PROBE_INDICES

SCHEMA = "bean.external_elec2_transfer_probe.v1"
DATA_URL = "https://www.openml.org/data/download/2419/electricity-normalized.arff"
DATA_LICENSE = "ODC-PDDL (DataHub OpenML electricity dataset)"
MAX_BYTES = 5_000_000
WINDOWS_PER_PERIOD = 16
WINDOW_SIZE = 24
POLICIES = ("constant_down", "naive_price_proxy", "frozen_four", "rolling_four", "two_error_probe")


def _parse_arff(raw):
    """Parse the 9-column Elec2 ARFF, preserving chronological order."""
    text = raw.decode("utf-8-sig")
    attributes = []
    in_data = False
    rows = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("%"):
            continue
        if not in_data:
            if line.lower().startswith("@attribute"):
                parts = line.split(None, 2)
                if len(parts) < 3:
                    raise ValueError("malformed ARFF attribute")
                attributes.append(parts[1].strip("'\"").lower())
            elif line.lower() == "@data":
                in_data = True
            continue
        if line.startswith("{"):
            raise ValueError("sparse ARFF not supported")
        fields = next(csv.reader([line], skipinitialspace=True))
        if len(fields) != len(attributes) or "?" in fields:
            raise ValueError("invalid or missing Elec2 observation")
        item = dict(zip(attributes, (v.strip().strip("'\"") for v in fields)))
        label = item["class"].upper()
        if label not in ("UP", "DOWN"):
            raise ValueError("unexpected Elec2 class")
        nsw, vic = float(item["nswprice"]), float(item["vicprice"])
        rows.append(("flip" if nsw >= vic else "hold",
                     "flip" if label == "UP" else "hold"))
    if not in_data or len(attributes) != 9 or not {"nswprice", "vicprice", "class"} <= set(attributes):
        raise ValueError("unexpected Elec2 ARFF schema")
    if not rows:
        raise ValueError("empty Elec2 data")
    return rows


def _fetch():
    """No silent fixture fallback when the external source is unavailable."""
    request = Request(DATA_URL, headers={"User-Agent": "BEAN-research-readonly/1.0"})
    with urlopen(request, timeout=30) as response:
        raw = response.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES:
        raise ValueError("Elec2 download exceeded byte budget")
    return raw


def _window(data, start):
    """Prediction before probe feedback; scorer-only labels never enter state."""
    calibration = data[start:start + 4]
    heldout = data[start + 4:start + WINDOW_SIZE]
    if len(heldout) != 20:
        raise ValueError("incomplete stream window")
    observed = list(calibration)
    frozen = _orientation(observed)
    two_orientation, two_errors = frozen, 0
    receipts = []
    for i, (source, target) in enumerate(heldout):
        rolling = _orientation(observed)
        decisions = {
            "constant_down": "hold",
            "naive_price_proxy": source,
            "frozen_four": _predict(source, frozen),
            "rolling_four": _predict(source, rolling),
            "two_error_probe": _predict(source, two_orientation),
        }
        before = {"two_error_probe_gate": two_orientation}
        disclosed = target if i in PROBE_INDICES else None
        if disclosed is not None:
            observed.append((source, disclosed))
            observed = observed[-4:]
            two_orientation, two_errors, _ = _update(
                two_orientation, two_errors, decisions["two_error_probe"], disclosed, 2)
        row = {
            "stream_index": i, "source_proxy": source,
            "decisions_before_feedback": {"two_error_probe_gate": decisions["two_error_probe"]},
            "orientation_before": before,
            "orientation_after": {"two_error_probe_gate": two_orientation},
            "feedback_observed": disclosed,
            "scorer_only_target": target,
            "predictions": decisions,
            "is_feedback_probe": disclosed is not None,
        }
        row["sha256"] = sha256(json.dumps(row, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        receipts.append(row)
    state, errors, _ = _replay(frozen, receipts, 2)
    if (state, errors) != (two_orientation, two_errors):
        raise AssertionError("detector replay differs from online state")
    scores = {name: sum(row["predictions"][name] == row["scorer_only_target"]
                        for row in receipts if not row["is_feedback_probe"])
              for name in POLICIES}
    return {"start_index": start, "calibration_labels": 4, "probe_labels": len(PROBE_INDICES),
            "scored_cases": 20 - len(PROBE_INDICES), "scores": scores,
            "receipts": receipts, "replay_verified": True}


def _run(data, dataset_sha):
    if len(data) < 2500:
        raise ValueError("not enough Elec2 observations for disjoint chronological evaluation")
    starts = {
        "earlier": [len(data) // 5 + i * WINDOW_SIZE for i in range(WINDOWS_PER_PERIOD)],
        "later_ood": [len(data) * 4 // 5 + i * WINDOW_SIZE for i in range(WINDOWS_PER_PERIOD)],
    }
    periods = {}
    for name, indices in starts.items():
        windows = [_window(data, start) for start in indices]
        summaries = {policy: round(sum(w["scores"][policy] for w in windows) / len(windows), 5)
                     for policy in POLICIES}
        periods[name] = {"windows": windows, "mean_correct_out_of_16": summaries,
                         "paired_rolling_minus_two_error": [
                             w["scores"]["rolling_four"] - w["scores"]["two_error_probe"]
                             for w in windows]}
    payload = json.dumps(periods, sort_keys=True, separators=(",", ":"))
    return {"schema": SCHEMA, "source_sha": os.environ.get("BEAN_SOURCE_SHA", "not_supplied"),
            "dataset_url": DATA_URL, "dataset_license": DATA_LICENSE,
            "dataset_sha256": dataset_sha, "dataset_rows": len(data),
            "windows_per_period": WINDOWS_PER_PERIOD, "calibration_labels_per_window": 4,
            "probe_labels_per_window": len(PROBE_INDICES), "scored_cases_per_window": 16,
            "source_proxy": "UP iff normalized NSW price >= normalized Victoria price",
            "periods": periods, "case_sha256": sha256(payload.encode()).hexdigest(),
            "limitations": ["External Elec2 is real historical market data, not novel agent tasks",
                            "The fixed price proxy is not a retrieved BEAN semantic precedent",
                            "Simple frozen heuristics, not trained or deployed BEAN policies",
                            "Four calibration and four probe labels for adaptive policies; naive/constant use zero",
                            "Windows are chronological and disjoint, but not independent market episodes",
                            "Only in-memory detector replay; no Jetson or persistent detector integration"]}


class ExternalElec2Controls(unittest.TestCase):
    def test_parser_fixture_and_rejection(self):
        raw = (b"@relation electricity\n@attribute date numeric\n@attribute day numeric\n"
               b"@attribute period numeric\n@attribute nswprice numeric\n"
               b"@attribute nswdemand numeric\n@attribute vicprice numeric\n"
               b"@attribute vicdemand numeric\n@attribute transfer numeric\n"
               b"@attribute class {UP,DOWN}\n@data\n"
               b"1,1,1,0.8,0.2,0.1,0.3,0.1,UP\n"
               b"2,2,2,0.1,0.2,0.8,0.3,0.1,DOWN\n")
        self.assertEqual(_parse_arff(raw), [("flip", "flip"), ("hold", "hold")])
        with self.assertRaises(ValueError):
            _parse_arff(raw.replace(b"0.8,0.2", b"?,0.2"))

    def test_probe_only_feedback_and_replay(self):
        data = [("flip" if i % 2 else "hold", "flip" if i % 3 else "hold")
                for i in range(24)]
        first = _window(data, 0)
        self.assertEqual(first["probe_labels"], 4)
        self.assertEqual(first["scored_cases"], 16)
        self.assertTrue(first["replay_verified"])
        self.assertEqual(first, _window(data, 0))
        self.assertEqual(sum(r["is_feedback_probe"] for r in first["receipts"]), 4)

    def test_hidden_scoring_labels_cannot_change_decisions(self):
        data = [("flip" if i % 2 else "hold", "flip" if i % 3 else "hold")
                for i in range(24)]
        changed = list(data)
        for i in range(20):
            if i not in PROBE_INDICES:
                source, label = changed[4 + i]
                changed[4 + i] = (source, "hold" if label == "flip" else "flip")
        original, flipped = _window(data, 0), _window(changed, 0)
        for a, b in zip(original["receipts"], flipped["receipts"]):
            self.assertEqual(a["predictions"], b["predictions"])
            self.assertEqual(a["orientation_before"], b["orientation_before"])
            self.assertEqual(a["orientation_after"], b["orientation_after"])
            self.assertEqual(a["feedback_observed"], b["feedback_observed"])
        for policy in POLICIES:
            self.assertEqual(original["scores"][policy] + flipped["scores"][policy], 16)

    @unittest.skipUnless(os.environ.get("BEAN_EXTERNAL_STREAM") == "1", "external data opt-in")
    def test_independent_elec2_stream(self):
        raw = _fetch()
        report = _run(_parse_arff(raw), sha256(raw).hexdigest())
        self.assertGreaterEqual(report["dataset_rows"], 45000)
        self.assertEqual(len(report["periods"]), 2)
        self.assertEqual(len(report["dataset_sha256"]), 64)
        self.assertEqual(json.loads(json.dumps(report)), report)


if __name__ == "__main__":
    if sys.argv[1:] == ["--report"]:
        raw = _fetch()
        print(json.dumps(_run(_parse_arff(raw), sha256(raw).hexdigest()), sort_keys=True, indent=2))
    else:
        unittest.main()
