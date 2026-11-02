"""External SCAN compositional holdout: evidence-linked retrieval versus structure.

This is a *falsification* benchmark, not an agent policy or a model.
The SCAN add-primitive-jump split is independently authored by Lake & Baroni.
Only training labels enter the lesson bank. Test outputs are scorer-only.
No dataset is committed, and no new memory/journal/backend is created.

BEAN_EXTERNAL_SCAN=1 python -m unittest -v bean.tests.test_external_scan_composition
python -m bean.tests.test_external_scan_composition --report
"""
from __future__ import annotations

from hashlib import sha1, sha256
import json
import os
from pathlib import Path
import re
import sys
import tempfile
import unittest
from urllib.request import Request, urlopen

from bean.learning.reasoning_service import NativeReasoningService

SCHEMA = "bean.external_scan_composition.v1"
SOURCE = "https://github.com/brendenlake/SCAN"
ROOT = "https://raw.githubusercontent.com/brendenlake/SCAN/master/add_prim_split/"
FILES = {
    "train": ("tasks_train_addprim_jump.txt",
              "87ed95fdc6851931ac9bf2f8932f245e75352ea5"),
    "test": ("tasks_test_addprim_jump.txt",
             "242eb2c7effc8673010868b854bc8e0a4c42c42c"),
}
SEED = "bean-scan-v1-20261102"
LESSON_BUDGET = 1024
TEST_BUDGET = 96
RETRIEVAL_BUDGET = 10
MAX_BYTES = 8_000_000
PRIMITIVES = ("walk", "run", "look")
POLICIES = ("primitive_jump", "native_copy", "native_template",
            "matched_template", "full_train_template")


def _digest(value):
    return sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                             ensure_ascii=True).encode()).hexdigest()


def _git_blob(raw):
    return sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()


def _fetch():
    results, hashes = {}, {}
    for name, (filename, expected_blob) in FILES.items():
        request = Request(ROOT + filename,
                          headers={"User-Agent": "BEAN-public-research/1.0"})
        with urlopen(request, timeout=30) as response:
            raw = response.read(MAX_BYTES + 1)
        if len(raw) > MAX_BYTES or _git_blob(raw) != expected_blob:
            raise ValueError("SCAN source changed or exceeded byte budget: " + name)
        results[name] = _parse(raw)
        hashes[name] = {"git_blob_sha1": expected_blob,
                        "download_sha256": sha256(raw).hexdigest(),
                        "unique_commands": len(results[name])}
    if set(results["train"]) & set(results["test"]):
        raise ValueError("SCAN train/test command overlap")
    return results, hashes


def _parse(raw):
    result = {}
    for line in raw.decode("utf-8").splitlines():
        match = re.fullmatch(r"IN: (.+?) OUT: ([A-Z_ ]+)", line.strip())
        if not match:
            raise ValueError("Invalid SCAN source row")
        command, output = match.groups()
        if command in result and result[command] != output:
            raise ValueError("Conflicting labels in source data")
        result[command] = output
    if not result:
        raise ValueError("Empty SCAN source")
    return result


def _select(mapping, count, tag):
    return sorted(mapping, key=lambda command: (
        sha256((SEED + ":" + tag + ":" + command).encode()).hexdigest(),
        command))[:count]


def _train_subset(train):
    if "jump" not in train or train["jump"] != "I_JUMP":
        raise ValueError("SCAN jump primitive missing from training")
    # Preserve the atomic primitive, without using held-out queries or labels.
    other = {command: output for command, output in train.items()
             if command != "jump"}
    commands = ["jump"] + _select(other, LESSON_BUDGET - 1, "training")
    if len(commands) != LESSON_BUDGET:
        raise ValueError("Insufficient unique training examples")
    return {command: train[command] for command in commands}


def _surrogates(command):
    if "jump" not in command.split():
        return ()
    # Avoid replacing an existing second verb's actions.
    return tuple((command.replace("jump", primitive),
                  "I_" + primitive.upper()) for primitive in PRIMITIVES
                 if primitive not in command.split())


def _transfer(source_output, source_action):
    return " ".join("I_JUMP" if token == source_action else token
                    for token in source_output.split())


def _template(command, source):
    for replacement, action in _surrogates(command):
        if replacement in source:
            return _transfer(source[replacement], action), replacement
    return None, None


def _predict(command, hits, by_id, selected, full_train):
    top = by_id.get(hits[0]["lesson_id"]) if hits else None
    native_copy = top[1] if top else None
    native_template = None
    native_source = None
    allowed = dict(_surrogates(command))
    for hit in hits:
        source = by_id.get(hit["lesson_id"])
        if source and source[0] in allowed:
            native_template = _transfer(source[1], allowed[source[0]])
            native_source = hit["lesson_id"]
            break
    matched, matched_command = _template(command, selected)
    full, full_command = _template(command, full_train)
    return {
        "primitive_jump": "I_JUMP",
        "native_copy": native_copy,
        "native_template": native_template,
        "matched_template": matched,
        "full_train_template": full,
    }, {"native_lesson_id": native_source,
        "matched_training_command": matched_command,
        "full_training_command": full_command}


def _case(command, truth, hits, by_id, selected, full_train):
    # The scorer-only label is passed AFTER all predictions are fixed.
    predictions, evidence = _predict(command, hits, by_id, selected, full_train)
    row = {
        "command": command,
        "predictions": predictions,
        "evidence": evidence,
        "retrieval_ids": [hit["lesson_id"] for hit in hits],
        "retrieval_terms": [hit["matched_terms"] for hit in hits],
        "retrieval_unverified": all(
            hit["independently_verified_transfer"] is False
            and hit["safe_to_apply_without_target_test"] is False
            for hit in hits),
        "scorer_only_output": truth,
        "correct": {name: prediction == truth for name, prediction
                    in predictions.items()},
    }
    row["case_sha256"] = _digest(row)
    return row


def run_report(train, test, hashes):
    selected = _train_subset(train)
    commands = _select(test, TEST_BUDGET, "heldout")
    if len(commands) != TEST_BUDGET:
        raise ValueError("Insufficient held-out cases")
    rows = []
    with tempfile.TemporaryDirectory() as tmp:
        db = Path(tmp) / "scan-native.sqlite"
        core = NativeReasoningService(db, model=None)
        by_id = {}
        for command, output in selected.items():
            ref = "scan:train:" + sha256(command.encode()).hexdigest()[:24]
            lesson = core.propose_instruction(
                domain="scan-training",
                instruction="SCAN training command " + command + " => " + output,
                evidence_refs=[ref, "scan:gitblob:" + FILES["train"][1]])
            by_id[lesson["lesson_id"]] = (command, output)
        original_hits = []
        for command in commands:
            hits = core.recall_analogies(
                domain="scan-heldout", query=command, limit=RETRIEVAL_BUDGET)
            if any(hit["lesson_id"] not in by_id
                   or "scan:gitblob:" + FILES["train"][1] not in hit["evidence_refs"]
                   for hit in hits):
                raise AssertionError("Unproven native retrieval provenance")
            original_hits.append([hit["lesson_id"] for hit in hits])
            rows.append(_case(command, test[command], hits, by_id,
                              selected, train))
        before = len(core.bank.journal.events())
        core.close()
        reopened = NativeReasoningService(db, model=None)
        try:
            for command, ids in zip(commands[:12], original_hits[:12]):
                replay = reopened.recall_analogies(
                    domain="scan-heldout", query=command, limit=RETRIEVAL_BUDGET)
                if [hit["lesson_id"] for hit in replay] != ids:
                    raise AssertionError("Restart changed retrieval ranking")
            if len(reopened.bank.journal.events()) != before:
                raise AssertionError("Read-only replay appended journal events")
        finally:
            reopened.close()
    scores = {policy: sum(row["correct"][policy] for row in rows)
              for policy in POLICIES}
    coverage = {policy: sum(row["predictions"][policy] is not None
                            for row in rows) for policy in POLICIES}
    return {
        "schema": SCHEMA,
        "source_revision": os.environ.get("BEAN_SOURCE_SHA", "not_supplied"),
        "benchmark": SOURCE,
        "split": "add_prim_jump",
        "source_hashes": hashes,
        "selection_seed": SEED,
        "training_lessons": LESSON_BUDGET,
        "training_total": len(train),
        "heldout_cases": TEST_BUDGET,
        "retrieval_budget_per_case": RETRIEVAL_BUDGET,
        "scores_exact_match": scores,
        "coverage": coverage,
        "paired_native_minus_matched": [
            int(row["correct"]["native_template"]) -
            int(row["correct"]["matched_template"]) for row in rows],
        "negative_transfer_cases": [
            row["command"] for row in rows
            if row["correct"]["matched_template"]
            and not row["correct"]["native_template"]],
        "case_receipts": rows,
        "case_receipts_sha256": _digest(rows),
        "sqlite_restart_retrieval_verified": True,
        "limitations": [
            "SCAN is an externally authored but synthetic language benchmark",
            "Training and test share one compositional grammar, not distinct industries",
            "No learned semantic embedding, neural weights or general agent policy",
            "Template replacement is an explicitly hand-coded diagnostic",
            "Full-training template control uses more source examples than native",
            "Native top-ten retrieval may omit a structurally matching example",
            "One predeclared hash-selected held-out cohort, not a confidence interval",
            "SQLite restart tested on a temporary research database, not Jetson",
            "Dataset-provided labels are not independent physical-world outcomes",
        ],
    }


class ScanCompositionControls(unittest.TestCase):
    def test_parser_blob_pin_and_rejections(self):
        raw = b"IN: jump OUT: I_JUMP\nIN: walk twice OUT: I_WALK I_WALK\n"
        self.assertEqual(_parse(raw)["jump"], "I_JUMP")
        self.assertEqual(len(_git_blob(raw)), 40)
        with self.assertRaises(ValueError):
            _parse(b"IN: jump OUT: I_JUMP\nIN: jump OUT: I_WALK\n")

    def test_structural_transfer_and_hidden_label_firewall(self):
        source = {"walk around right": "I_TURN_RIGHT I_WALK I_TURN_RIGHT I_WALK I_TURN_RIGHT I_WALK I_TURN_RIGHT I_WALK",
                  "run and walk": "I_RUN I_WALK"}
        expected, ref = _template("jump around right", source)
        self.assertEqual(ref, "walk around right")
        self.assertEqual(expected, "I_TURN_RIGHT I_JUMP I_TURN_RIGHT I_JUMP I_TURN_RIGHT I_JUMP I_TURN_RIGHT I_JUMP")
        self.assertEqual(_template("jump and walk", source), (None, None))
        fake_hits = []
        first = _case("jump around right", "I_JUMP", fake_hits, {}, source, source)
        changed = _case("jump around right", "I_TURN_RIGHT I_JUMP", fake_hits, {}, source, source)
        self.assertEqual(first["predictions"], changed["predictions"])
        self.assertNotEqual(first["correct"], changed["correct"])

    def test_train_selection_does_not_depend_on_test_labels(self):
        train = {"jump": "I_JUMP", **{
            "walk " + str(i): "I_WALK" for i in range(1200)}}
        chosen = _train_subset(train)
        self.assertEqual(len(chosen), LESSON_BUDGET)
        self.assertEqual(chosen, _train_subset(dict(reversed(list(train.items())))))
        self.assertEqual(chosen["jump"], "I_JUMP")

    @unittest.skipUnless(os.environ.get("BEAN_EXTERNAL_SCAN") == "1",
                         "public SCAN download opt-in")
    def test_external_scan_heldout(self):
        data, hashes = _fetch()
        report = run_report(data["train"], data["test"], hashes)
        self.assertEqual(len(report["case_receipts"]), TEST_BUDGET)
        self.assertTrue(report["sqlite_restart_retrieval_verified"])
        self.assertEqual(report["case_receipts_sha256"],
                         _digest(report["case_receipts"]))
        self.assertTrue(all(row["retrieval_unverified"]
                            for row in report["case_receipts"]))


if __name__ == "__main__":
    if sys.argv[1:] == ["--report"]:
        data, hashes = _fetch()
        print(json.dumps(run_report(data["train"], data["test"], hashes),
                         sort_keys=True, indent=2))
    else:
        unittest.main()
