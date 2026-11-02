"""Second independent domain for BEAN's feedback-transfer falsification suite.

UCI Occupancy Detection (Candanedo, 2016; CC BY 4.0), original test
segments only. Compare a fixed light-sensor heuristic with unchanged
budget-matched source-blind and online feedback controls. Not semantic
analogy, BEAN inference, model training, or a Jetson experiment.

BEAN_EXTERNAL_OCCUPANCY=1 python -m bean.tests.test_external_occupancy_transfer --report
"""
from __future__ import annotations

import csv
from datetime import datetime
from hashlib import sha256
from io import BytesIO, StringIO
import json
import math
import os
import sys
import unittest
from urllib.request import Request, urlopen
from zipfile import ZipFile, BadZipFile

from bean.tests.test_cross_domain_drift_probes import PROBE_INDICES
from bean.tests.test_external_elec2_transfer import _window as _proxy_window
from bean.tests.test_external_elec2_conditional_baseline import (
    _window as _conditional_window, _replay as _conditional_replay, _digest,
)
from bean.tests.test_external_elec2_source_blind import (
    _window as _blind_window, _replay as _blind_replay,
)

SCHEMA = "bean.external_occupancy_second_domain.v1"
DATA_URL = "https://archive.ics.uci.edu/static/public/357/occupancy+detection.zip"
DATA_CITATION = "Candanedo (2016), UCI Occupancy Detection, doi:10.24432/C5X01N"
DATA_LICENSE = "CC BY 4.0"
MAX_DOWNLOAD_BYTES = 3_000_000
MAX_MEMBER_BYTES = 2_000_000
REQUIRED = ("datatest.txt", "datatest2.txt")
WINDOWS = 16
SIZE = 24
POLICIES = (
    "constant_empty", "light_ge_100_lux", "rolling_four",
    "conditional_frequency", "last_disclosed_label", "recent_four_majority",
)


def _fetch():
    request = Request(DATA_URL, headers={"User-Agent": "BEAN-public-research/1.0"})
    with urlopen(request, timeout=30) as response:
        raw = response.read(MAX_DOWNLOAD_BYTES + 1)
    if len(raw) > MAX_DOWNLOAD_BYTES:
        raise ValueError("occupancy archive exceeds download budget")
    return raw


def _members(raw, *, nested=False):
    """Read selected files only; never extract ZIP paths to disk."""
    try:
        with ZipFile(BytesIO(raw)) as archive:
            result = {}
            inner = []
            for info in archive.infolist():
                name = info.filename.rsplit("/", 1)[-1].lower()
                if info.is_dir():
                    continue
                if name in REQUIRED:
                    if name in result or info.file_size > MAX_MEMBER_BYTES:
                        raise ValueError("duplicate or oversized occupancy file")
                    result[name] = archive.read(info)
                elif name.endswith(".zip"):
                    if info.file_size > MAX_DOWNLOAD_BYTES:
                        raise ValueError("oversized nested occupancy archive")
                    inner.append(archive.read(info))
            if all(name in result for name in REQUIRED):
                return {name: result[name] for name in REQUIRED}
            if not nested and len(inner) == 1:
                return _members(inner[0], nested=True)
            raise ValueError("expected two official UCI occupancy test files")
    except BadZipFile as exc:
        raise ValueError("invalid UCI occupancy ZIP") from exc


def _parse_csv(raw):
    reader = csv.reader(StringIO(raw.decode("utf-8-sig")))
    header = [item.strip().lower() for item in next(reader)]
    if header and header[0] in ("", "id", "index"):
        header = header[1:]
        drop_index = True
    else:
        drop_index = False
    if set(header) != {
        "date", "temperature", "humidity", "light", "co2",
        "humidityratio", "occupancy",
    } or len(header) != 7:
        raise ValueError("unexpected UCI occupancy column schema")
    output = []
    last_time = None
    for fields in reader:
        if not fields:
            continue
        if drop_index:
            if len(fields) != 8:
                raise ValueError("invalid indexed occupancy row")
            fields = fields[1:]
        elif len(fields) == 8:
            # Original UCI files have an unlabeled leading row index.
            fields = fields[1:]
        if len(fields) != 7 or any(v.strip() in ("", "?") for v in fields):
            raise ValueError("invalid or missing occupancy observation")
        item = dict(zip(header, fields))
        timestamp = datetime.fromisoformat(item["date"].strip())
        if last_time is not None and timestamp < last_time:
            raise ValueError("nonchronological occupancy source")
        last_time = timestamp
        light = float(item["light"])
        if not math.isfinite(light) or light < 0:
            raise ValueError("invalid light measurement")
        if item["occupancy"].strip() not in ("0", "1"):
            raise ValueError("invalid occupancy target")
        # Fixed physical proxy, predeclared without looking at labels.
        output.append(("flip" if light >= 100.0 else "hold",
                       "flip" if item["occupancy"].strip() == "1" else "hold"))
    if not output:
        raise ValueError("empty occupancy source")
    return output


def _parse_archive(raw):
    members = _members(raw)
    data = {name: _parse_csv(members[name]) for name in REQUIRED}
    digests = {name: sha256(members[name]).hexdigest() for name in REQUIRED}
    return data, digests


def _window(data, start):
    base = _proxy_window(data, start)
    blind = _blind_window(data, start)
    conditional = _conditional_window(data, start)
    if not _blind_replay(json.loads(json.dumps(blind))):
        raise AssertionError("source-blind restart replay mismatch")
    if not _conditional_replay(json.loads(json.dumps(conditional))):
        raise AssertionError("conditional restart replay mismatch")
    if (blind["feedback_labels"], conditional["feedback_labels"],
            base["calibration_labels"] + base["probe_labels"]) != (8, 8, 8):
        raise AssertionError("unequal adaptive feedback budgets")
    if (blind["scored_cases"], conditional["scored_cases"],
            base["scored_cases"]) != (16, 16, 16):
        raise AssertionError("unequal scored cases")
    scores = {
        "constant_empty": base["scores"]["constant_down"],
        "light_ge_100_lux": base["scores"]["naive_price_proxy"],
        "rolling_four": base["scores"]["rolling_four"],
        "conditional_frequency": conditional["correct"],
        **blind["scores"],
    }
    return {
        "start_index": start, "scores": scores,
        "feedback_labels_adaptive": 8, "scored_cases": 16,
        "source_receipts": base["receipts"],
        "conditional_receipts": conditional["cases"],
        "source_blind_receipts": blind["cases"],
        "replay_verified": True,
    }


def _report(data, member_hashes, archive_hash):
    periods = {}
    for name in REQUIRED:
        stream = data[name]
        starts = [len(stream) // 3 + i * SIZE for i in range(WINDOWS)]
        if starts[-1] + SIZE > len(stream):
            raise ValueError("insufficient observations for disjoint windows")
        windows = [_window(stream, start) for start in starts]
        summary = {
            policy: sum(w["scores"][policy] for w in windows) / WINDOWS
            for policy in POLICIES
        }
        paired = {
            policy: [w["scores"][policy] -
                     w["scores"]["last_disclosed_label"] for w in windows]
            for policy in POLICIES if policy != "last_disclosed_label"
        }
        periods[name] = {
            "rows": len(stream), "member_sha256": member_hashes[name],
            "windows": windows, "mean_correct_out_of_16": summary,
            "paired_minus_last_disclosed_label": paired,
        }
    result = {
        "schema": SCHEMA,
        "source_sha": os.environ.get("BEAN_SOURCE_SHA", "not_supplied"),
        "dataset_url": DATA_URL, "dataset_citation": DATA_CITATION,
        "license": DATA_LICENSE, "archive_sha256": archive_hash,
        "light_proxy": "occupied iff Light >= 100 lux (fixed, not tuned)",
        "windows_per_segment": WINDOWS,
        "calibration_labels": 4, "probe_labels": len(PROBE_INDICES),
        "probe_indices": list(PROBE_INDICES), "scored_cases_per_window": 16,
        "periods": periods,
        "limitations": [
            "Second real domain, but only one room and two correlated time series",
            "UCI test segments are independently collected, not independent novel tasks",
            "Light threshold is a hand-coded feature proxy, not semantic BEAN recall",
            "No online model weights, autonomous task discovery or policy deployment",
            "No source-data revision pin before first independently observed download",
            "Only serialized experimental replay, not actual Jetson process restart",
            "Fixed proxies use zero feedback; adaptive controls use eight labels",
        ],
    }
    result["report_sha256"] = _digest(result)
    return result


class ExternalOccupancySecondDomain(unittest.TestCase):
    @staticmethod
    def _fictional():
        return [("flip" if i % 2 else "hold",
                 "flip" if i % 3 else "hold") for i in range(SIZE)]

    def test_parser_and_rejections(self):
        from zipfile import ZIP_DEFLATED
        buf = BytesIO()
        with ZipFile(buf, "w", ZIP_DEFLATED) as archive:
            for name in REQUIRED:
                archive.writestr(name,
                    '"date","Temperature","Humidity","Light","CO2","HumidityRatio","Occupancy"\n'
                    '"140","2015-02-02 14:19:00",23.7,26.2,585.2,749.2,0.0047,1\n'
                    '"141","2015-02-02 14:20:00",23.7,26.2,0,749.2,0.0047,0\n')
        data, digests = _parse_archive(buf.getvalue())
        self.assertEqual(data["datatest.txt"], [("flip", "flip"), ("hold", "hold")])
        self.assertEqual(len(digests["datatest2.txt"]), 64)
        with self.assertRaises(ValueError):
            _parse_csv(b"date,Light,Occupancy\n2020-01-01,10,0\n")
        with self.assertRaises(ValueError):
            _parse_csv(
                b'date,Temperature,Humidity,Light,CO2,HumidityRatio,Occupancy\n'
                b'2020-01-01,20,40,?,500,0.005,1\n')

    def test_budget_replay_and_oracle_firewall(self):
        data = self._fictional()
        changed = list(data)
        for i in range(20):
            if i not in PROBE_INDICES:
                source, target = changed[4 + i]
                changed[4 + i] = (source, "hold" if target == "flip" else "flip")
        a, b = _window(data, 0), _window(changed, 0)
        self.assertEqual(a["feedback_labels_adaptive"], 8)
        self.assertEqual(a["scored_cases"], 16)
        for key in ("source_receipts", "conditional_receipts", "source_blind_receipts"):
            for x, y in zip(a[key], b[key]):
                predictions = ("predictions", "prediction_before_feedback")
                for field in predictions:
                    if field in x:
                        self.assertEqual(x[field], y[field])
                self.assertEqual(x["feedback_observed"], y["feedback_observed"])
        self.assertEqual(a, _window(data, 0))

    def test_adversarial_negative_transfer(self):
        data = [("flip", "flip")] * 4 + [("flip", "hold")] * 20
        result = _window(data, 0)
        self.assertEqual(result["scores"]["light_ge_100_lux"], 0)
        self.assertEqual(result["scores"]["constant_empty"], 16)
        self.assertTrue(result["replay_verified"])

    @unittest.skipUnless(os.environ.get("BEAN_EXTERNAL_OCCUPANCY") == "1",
                         "external UCI occupancy data opt-in")
    def test_independent_occupancy_segments(self):
        raw = _fetch()
        data, member_hashes = _parse_archive(raw)
        self.assertGreater(len(data["datatest.txt"]), 2500)
        self.assertGreater(len(data["datatest2.txt"]), 9000)
        report = _report(data, member_hashes, sha256(raw).hexdigest())
        for period in report["periods"].values():
            self.assertEqual(len(period["windows"]), WINDOWS)
            for window in period["windows"]:
                self.assertEqual(window["feedback_labels_adaptive"], 8)
                self.assertTrue(window["replay_verified"])
        self.assertEqual(report["report_sha256"],
                         _digest({k: v for k, v in report.items()
                                  if k != "report_sha256"}))


if __name__ == "__main__":
    if sys.argv[1:] == ["--report"]:
        raw = _fetch()
        data, member_hashes = _parse_archive(raw)
        print(json.dumps(_report(data, member_hashes, sha256(raw).hexdigest()),
                         sort_keys=True, indent=2))
    else:
        unittest.main()
