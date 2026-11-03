"""Independent source-replay auditor for BEAN's SCAN reverse-order receipts.

This verifier does not import the candidate, its source selector or its
prediction functions. It downloads and checks the independently published,
pinned SCAN split and reconstructs all held-out answers, paired scores,
source memberships, failure cases and receipt digests.

python -m bean.tests.test_scan_reverse_order_audit reverse-scan-receipt.json
"""
from __future__ import annotations

from hashlib import sha1, sha256
import json
from pathlib import Path
import re
import sys
import unittest
from urllib.request import Request, urlopen

SCHEMA = "bean.scan_reverse_order.v1"
SEED = "bean-scan-reverse-order-independent-20261102"
ROOT = "https://raw.githubusercontent.com/brendenlake/SCAN/master/add_prim_split/"
PINNED = {
    "train": ("tasks_train_addprim_jump.txt",
              "87ed95fdc6851931ac9bf2f8932f245e75352ea5"),
    "test": ("tasks_test_addprim_jump.txt",
             "242eb2c7effc8673010868b854bc8e0a4c42c42c"),
}
POLICIES = ("learned", "phrase", "blind")


def digest(value):
    return sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                             ensure_ascii=True).encode()).hexdigest()


def source_ref(command):
    return "scan:train:" + sha256(command.encode()).hexdigest()[:24]


def source_data():
    sources, hashes = {}, {}
    for key, (filename, blob) in PINNED.items():
        with urlopen(Request(ROOT + filename, headers={
                "User-Agent": "BEAN-independent-SCAN-audit/1.0"}), timeout=30) as r:
            raw = r.read(8_000_001)
        if len(raw) > 8_000_000 or sha1(
                b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest() != blob:
            raise ValueError("Source blob mismatch: " + key)
        parsed = {}
        for line in raw.decode("utf-8").splitlines():
            match = re.fullmatch(r"IN: (.+?) OUT: ([A-Z_ ]+)", line.strip())
            if not match:
                raise ValueError("Malformed SCAN line")
            command, output = match.groups()
            if command in parsed:
                raise ValueError("Repeated source command")
            parsed[command] = output
        sources[key] = parsed
        hashes[key] = {
            "git_blob_sha1": blob, "download_sha256": sha256(raw).hexdigest(),
            "unique_commands": len(parsed),
        }
    if set(sources["train"]) & set(sources["test"]):
        raise ValueError("Train/test overlap")
    return sources, hashes


def eligible(train, test):
    universe = dict(train)
    universe.update(test)
    selected = []
    for command, output in test.items():
        if command.count(" after ") != 1:
            continue
        left, right = command.split(" after ")
        if left not in universe or right not in universe:
            continue
        a, b = universe[left], universe[right]
        if a != b and output == b + " " + a and output != a + " " + b:
            selected.append(command)
    return sorted(selected, key=lambda c: (
        sha256((SEED + ":" + c).encode()).hexdigest(), c))


def audit(report, sources, hashes):
    if report.get("schema") != SCHEMA or report.get("selection_seed") != SEED:
        raise ValueError("Schema or selection seed changed")
    if report.get("source_hashes") != hashes:
        raise ValueError("Source hashes changed")
    train, test = sources["train"], sources["test"]
    training = report["training_rows"]
    if (len(training) != 1024 or report.get("training_budget") != 1024
            or len({row[0] for row in training}) != 1024):
        raise ValueError("Source budget or uniqueness mismatch")
    if any(not isinstance(row, list) or len(row) != 2
           or train.get(row[0]) != row[1] for row in training):
        raise ValueError("Source-only training mismatch")
    if report["training_rows_sha256"] != digest(training):
        raise ValueError("Training archive SHA mismatch")
    candidates = eligible(train, test)
    if report.get("eligible_pool") != len(candidates):
        raise ValueError("Eligible pool mismatch")
    commands = candidates[:96]
    rows = report["case_receipts"]
    if len(commands) != 96 or len(rows) != 96 or report.get("holdout_budget") != 96:
        raise ValueError("Incomplete held-out cohort")
    if report.get("case_receipts_sha256") != digest(rows):
        raise ValueError("Case archive SHA mismatch")
    if not report.get("snapshot_restart_verified") or not report.get(
            "native_sqlite_restart_verified"):
        raise ValueError("Missing restart checks")
    states = report["state_sha256"]
    if set(states) != set(POLICIES) or any(
            not re.fullmatch(r"[0-9a-f]{64}", value)
            for value in states.values()):
        raise ValueError("Invalid model hashes")
    valid_refs = {source_ref(row[0]) for row in training}
    scores = {p: 0 for p in POLICIES}
    coverage = {p: 0 for p in POLICIES}
    failures = []
    paired_blind, paired_phrase = [], []
    for command, row in zip(commands, rows):
        left, right = command.split(" after ")
        if (row.get("command") != command or row.get("left") != left
                or row.get("right") != right
                or row.get("scorer_only_output") != test[command]
                or row.get("state_sha256") != states):
            raise ValueError("Held-out truth, order or state mismatch")
        if (set(row["predictions"]) != set(POLICIES)
                or set(row["correct"]) != set(POLICIES)
                or set(row["evidence_refs"]) != set(POLICIES)
                or set(row["reasons"]) != set(POLICIES)
                or set(row["composed"]) != set(POLICIES)):
            raise ValueError("Missing paired policy")
        for p in POLICIES:
            if not set(row["evidence_refs"][p]).issubset(valid_refs):
                raise ValueError("Fabricated evidence reference")
            if type(row["composed"][p]) is not bool:
                raise ValueError("Malformed composed flag")
            prediction = row["predictions"][p]
            if prediction is not None and not isinstance(prediction, str):
                raise ValueError("Malformed prediction")
            correct = prediction == test[command]
            if row["correct"][p] is not correct:
                raise ValueError("Incorrect score flag")
            scores[p] += int(correct)
            coverage[p] += int(prediction is not None)
        paired_blind.append(int(row["correct"]["learned"]) -
                            int(row["correct"]["blind"]))
        paired_phrase.append(int(row["correct"]["learned"]) -
                             int(row["correct"]["phrase"]))
        if not row["correct"]["learned"]:
            failures.append({"command": command, "reason": row["reasons"]["learned"]})
        if row["case_sha256"] != digest({
                key: value for key, value in row.items() if key != "case_sha256"}):
            raise ValueError("Case receipt SHA mismatch")
    if (scores != report["scores_exact_match"]
            or coverage != report["coverage"]
            or paired_blind != report["paired_learned_minus_blind"]
            or paired_phrase != report["paired_learned_minus_phrase"]
            or failures != report["candidate_failures"]):
        raise ValueError("Aggregate scores or negative evidence mismatch")
    return {"cases_verified": len(rows), "eligible_pool": len(candidates),
            "scores": scores, "coverage": coverage,
            "candidate_failures_preserved": len(failures),
            "case_receipts_sha256": report["case_receipts_sha256"]}


class IndependentAuditControls(unittest.TestCase):
    def test_reverse_order_scorer_excludes_same_action(self):
        train = {"walk": "I_WALK", "run": "I_RUN"}
        test = {"walk after run": "I_RUN I_WALK",
                "run after walk": "I_WALK I_RUN",
                "walk after walk": "I_WALK I_WALK"}
        self.assertEqual(set(eligible(train, test)),
                         {"walk after run", "run after walk"})

    def test_digest_detects_mutation(self):
        row = {"command": "walk after run", "correct": {"learned": True}}
        before = digest(row)
        row["correct"]["learned"] = False
        self.assertNotEqual(before, digest(row))


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python -m bean.tests.test_scan_reverse_order_audit REPORT.json")
    report = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    data, hashes = source_data()
    print(json.dumps(audit(report, data, hashes), sort_keys=True))
