"""Research-only SCAN action-slot induction, with matched 1,024-example controls.

Learns reusable input/output skeletons from paired source examples, rather than
hand-coding SCAN's jump substitution. Exact skeleton lookup is NOT a learned
grammar or a general reasoning policy. Native BEAN's journal remains canonical.
External data are pinned by the existing SCAN loader; no dataset is committed.

BEAN_EXTERNAL_SCAN=1 python -m unittest -v bean.tests.test_scan_induced_slots
python -m bean.tests.test_scan_induced_slots --report
"""
from __future__ import annotations

from hashlib import sha256
import json
import os
from pathlib import Path
import re
import sys
import tempfile
import unittest

from bean.learning.reasoning_service import NativeReasoningService
from bean.tests.test_external_scan_composition import (
    FILES, LESSON_BUDGET, RETRIEVAL_BUDGET, SOURCE, TEST_BUDGET,
    _digest, _fetch, _predict, _select,
)

SCHEMA = "bean.scan_induced_slots.v1"
SLOT = "__ACTION_SLOT__"
COHORTS = ("original_hash_holdout", "fresh_disjoint_hash_holdout")
POLICIES = ("primitive_jump", "native_copy", "native_template",
            "matched_template", "full_train_template", "induced_slots")


def _training(train):
    """Reserve objectively identified atomic pairs, then hash-select the rest.

    Both the learned model and every control receive this EXACT same 1,024
    examples. Atomic anchors are selected by syntax, not by the held-out verb.
    """
    atomic = {command: output for command, output in train.items()
              if re.fullmatch(r"[a-z]+", command)
              and re.fullmatch(r"I_[A-Z]+", output)}
    if not 2 <= len(atomic) <= 32:
        raise ValueError("Insufficient or excessive source atomic anchors")
    remaining = {command: output for command, output in train.items()
                 if command not in atomic}
    selected = {command: atomic[command] for command in sorted(atomic)}
    selected.update({command: remaining[command] for command in
                     _select(remaining, LESSON_BUDGET - len(atomic), "training")})
    if len(selected) != LESSON_BUDGET:
        raise AssertionError("Training budget changed")
    return selected


class InducedSlots:
    """One-slot anti-unification over observed atomic input/output pairs.

    No command grammar, special verb, target label, learned weights, or
    model service is embedded here. Ambiguous source patterns abstain.
    """

    def __init__(self, training, source_blob):
        self.source_blob = source_blob
        self.atomic = {command: output for command, output in training.items()
                       if re.fullmatch(r"[a-z]+", command)
                       and re.fullmatch(r"I_[A-Z]+", output)}
        if len(self.atomic) < 2:
            raise ValueError("Need multiple observed atomic action mappings")
        self.templates = {}
        for command, output in sorted(training.items()):
            words = command.split()
            roles = set(words) & self.atomic.keys()
            if len(roles) != 1:
                continue
            role = next(iter(roles))
            action = self.atomic[role]
            output_words = output.split()
            if action not in output_words:
                continue
            key = tuple(SLOT if word == role else word for word in words)
            value = tuple(SLOT if word == action else word
                          for word in output_words)
            evidence = "scan:train:" + sha256(command.encode()).hexdigest()[:24]
            self.templates.setdefault(key, {}).setdefault(value, []).append(
                {"command": command, "evidence_ref": evidence,
                 "source_blob": source_blob})
        if not self.templates:
            raise ValueError("No source-derived templates")

    def state(self):
        payload = {
            "schema": SCHEMA, "source_blob": self.source_blob,
            "atomic": dict(sorted(self.atomic.items())),
            "templates": [
                {"command_pattern": list(key),
                 "alternatives": [
                     {"action_pattern": list(value), "sources": sources}
                     for value, sources in sorted(alternatives.items())
                 ]}
                for key, alternatives in sorted(self.templates.items())
            ],
        }
        return {**payload, "state_sha256": _digest(payload)}

    @classmethod
    def restore(cls, state):
        if state.get("schema") != SCHEMA:
            raise ValueError("Unknown induced-slot state schema")
        payload = {key: value for key, value in state.items()
                   if key != "state_sha256"}
        if state.get("state_sha256") != _digest(payload):
            raise ValueError("Induced-slot source snapshot digest mismatch")
        obj = cls.__new__(cls)
        obj.source_blob = state["source_blob"]
        obj.atomic = dict(state["atomic"])
        obj.templates = {}
        for entry in state["templates"]:
            key = tuple(entry["command_pattern"])
            if key in obj.templates:
                raise ValueError("Duplicate template key")
            obj.templates[key] = {
                tuple(option["action_pattern"]): list(option["sources"])
                for option in entry["alternatives"]}
        if not obj.atomic or not obj.templates or obj.state() != state:
            raise ValueError("Invalid induced-slot state roundtrip")
        return obj

    def predict(self, command):
        words = command.split()
        roles = set(words) & self.atomic.keys()
        if len(roles) != 1:
            return {"prediction": None, "reason": "not_one_known_action",
                    "evidence_refs": []}
        role = next(iter(roles))
        key = tuple(SLOT if word == role else word for word in words)
        options = self.templates.get(key)
        if not options:
            return {"prediction": None, "reason": "unseen_source_skeleton",
                    "evidence_refs": []}
        if len(options) != 1:
            return {"prediction": None, "reason": "conflicting_source_skeleton",
                    "evidence_refs": sorted({
                        row["evidence_ref"] for rows in options.values()
                        for row in rows})}
        output_pattern, sources = next(iter(options.items()))
        output = " ".join(self.atomic[role] if word == SLOT else word
                          for word in output_pattern)
        return {"prediction": output, "reason": "source_induced_exact_skeleton",
                "evidence_refs": sorted(row["evidence_ref"] for row in sources),
                "source_commands": sorted(row["command"] for row in sources),
                "source_blob": self.source_blob}


def run_report(train, test, hashes, *, holdout_offset=0):
    """Offset whole disjoint cohorts without changing source selection or model."""
    if type(holdout_offset) is not int or not 0 <= holdout_offset <= 8:
        raise ValueError("Invalid preregistered holdout offset")
    selected = _training(train)
    window = TEST_BUDGET * 2
    chosen = _select(test, window * (holdout_offset + 1), "heldout")[
        window * holdout_offset:]
    if len(chosen) != TEST_BUDGET * 2 or set(chosen) & set(selected):
        raise AssertionError("Disjoint holdout budget violated")
    model = InducedSlots(selected, FILES["train"][1])
    snapshot = model.state()
    state_sha = _digest(snapshot)
    rows = []
    with tempfile.TemporaryDirectory() as tmp:
        # Research snapshot only. Not a competing BEAN store or a Jetson install.
        state_path = Path(tmp) / "induced-slots.json"
        state_path.write_text(json.dumps(snapshot, sort_keys=True), encoding="utf-8")
        restored = InducedSlots.restore(json.loads(state_path.read_text(encoding="utf-8")))
        if _digest(restored.state()) != state_sha:
            raise AssertionError("Induced abstraction changed after restart")
        core = NativeReasoningService(Path(tmp) / "native-scan.sqlite", model=None)
        by_id = {}
        for command, output in selected.items():
            ref = "scan:train:" + sha256(command.encode()).hexdigest()[:24]
            lesson = core.propose_instruction(
                domain="scan-training",
                instruction="SCAN training command " + command + " => " + output,
                evidence_refs=[ref, "scan:gitblob:" + FILES["train"][1]])
            by_id[lesson["lesson_id"]] = (command, output)
        first_rankings = []
        for i, command in enumerate(chosen):
            # Hidden output is never passed into the learner or retrieval.
            hits = core.recall_analogies(
                domain="scan-heldout", query=command, limit=RETRIEVAL_BUDGET)
            if any(hit["lesson_id"] not in by_id or
                   "scan:gitblob:" + FILES["train"][1] not in hit["evidence_refs"]
                   for hit in hits):
                raise AssertionError("Native retrieval provenance lost")
            if i < 12:
                first_rankings.append([hit["lesson_id"] for hit in hits])
            predictions, source = _predict(command, hits, by_id, selected, train)
            induced = restored.predict(command)
            predictions["induced_slots"] = induced["prediction"]
            # Scoring happens after every prediction has been frozen.
            truth = test[command]
            row = {
                "cohort": COHORTS[i // TEST_BUDGET],
                "command": command,
                "predictions": predictions,
                "correct": {name: predictions[name] == truth for name in POLICIES},
                "scorer_only_output": truth,
                "native_retrieval_ids": [hit["lesson_id"] for hit in hits],
                "native_transfer_unverified": all(
                    not hit["independently_verified_transfer"] and
                    not hit["safe_to_apply_without_target_test"] for hit in hits),
                "matched_source": source["matched_training_command"],
                "induced": induced,
                "induced_state_sha256": state_sha,
            }
            row["case_sha256"] = _digest(row)
            rows.append(row)
        before = len(core.bank.journal.events())
        core.close()
        reopened = NativeReasoningService(Path(tmp) / "native-scan.sqlite", model=None)
        try:
            for command, ids in zip(chosen[:12], first_rankings):
                replay = reopened.recall_analogies(
                    domain="scan-heldout", query=command, limit=RETRIEVAL_BUDGET)
                if [hit["lesson_id"] for hit in replay] != ids:
                    raise AssertionError("Native journal restart ranking drift")
            if len(reopened.bank.journal.events()) != before:
                raise AssertionError("Read-only retrieval wrote journal")
        finally:
            reopened.close()
    cohorts = {}
    for name in COHORTS:
        group = [row for row in rows if row["cohort"] == name]
        cohorts[name] = {
            "cases": len(group),
            "scores_exact_match": {policy: sum(row["correct"][policy] for row in group)
                                   for policy in POLICIES},
            "coverage": {policy: sum(row["predictions"][policy] is not None
                                    for row in group) for policy in POLICIES},
            "paired_induced_minus_matched": [
                int(row["correct"]["induced_slots"]) -
                int(row["correct"]["matched_template"]) for row in group],
            "induced_failure_commands": [
                row["command"] for row in group
                if not row["correct"]["induced_slots"]],
        }
    return {
        "schema": SCHEMA,
        "source_revision": os.environ.get("BEAN_SOURCE_SHA", "not_supplied"),
        "benchmark": SOURCE, "split": "add_prim_jump",
        "source_hashes": hashes, "selection_seed": "bean-scan-v1-20261102",
        "holdout_offset": holdout_offset,
        "training_budget": len(selected), "training_total": len(train),
        "atomic_anchors": dict(sorted(model.atomic.items())),
        "induced_templates": len(model.templates),
        "ambiguous_templates": sum(len(v) > 1 for v in model.templates.values()),
        "retrieval_budget": RETRIEVAL_BUDGET,
        "induced_state_sha256": state_sha,
        "induced_snapshot_restart_verified": True,
        "native_sqlite_restart_verified": True,
        "cohorts": cohorts, "case_receipts": rows,
        "case_receipts_sha256": _digest(rows),
        "limitations": [
            "Source-derived exact action-slot templates are not a learned grammar",
            "Single known-action role only; conflicting evidence forces abstention",
            "Four atomic anchors are syntax-selected from the 1,024 source examples",
            "Full-training template baseline uses 13,204 examples, not budget-matched",
            "Both heldout cohorts share one SCAN grammar and one original test split",
            "Native lexical ranking remains unchanged; this is test-only research",
            "No neural training, provider, Jetson execution, Axiom or Core event writes",
            "Persisted research JSON and temporary native SQLite are not device restart",
        ],
    }


class InducedSlotControls(unittest.TestCase):
    def test_induction_on_unseen_fictional_action(self):
        train = {"glide": "I_GLIDE", "hop": "I_HOP",
                 "glide twice": "I_GLIDE I_GLIDE",
                 "glide left": "I_TURN_LEFT I_GLIDE"}
        model = InducedSlots(train, "synthetic-blob")
        self.assertEqual(model.predict("hop twice")["prediction"], "I_HOP I_HOP")
        self.assertEqual(model.predict("hop left")["prediction"],
                         "I_TURN_LEFT I_HOP")
        self.assertEqual(model.predict("hop right")["reason"],
                         "unseen_source_skeleton")
        self.assertEqual(model.predict("hop and glide")["reason"],
                         "not_one_known_action")
        self.assertTrue(model.predict("hop twice")["evidence_refs"])

    def test_conflicting_source_abstraction_abstains(self):
        train = {"glide": "I_GLIDE", "hop": "I_HOP",
                 "glide left": "I_TURN_LEFT I_GLIDE",
                 "hop left": "I_HOP I_TURN_LEFT"}
        model = InducedSlots(train, "synthetic-blob")
        self.assertEqual(model.predict("glide left")["reason"],
                         "conflicting_source_skeleton")
        self.assertIsNone(model.predict("hop left")["prediction"])

    def test_restart_and_hidden_target_firewall(self):
        train = {"glide": "I_GLIDE", "hop": "I_HOP",
                 "glide twice": "I_GLIDE I_GLIDE"}
        model = InducedSlots(train, "synthetic-blob")
        state = json.loads(json.dumps(model.state()))
        restored = InducedSlots.restore(state)
        self.assertEqual(_digest(restored.state()), _digest(state))
        prediction = restored.predict("hop twice")
        # Scorer-only target intervention cannot change the frozen prediction.
        self.assertEqual(prediction, restored.predict("hop twice"))
        self.assertNotEqual(prediction["prediction"], "I_HOP")
        state["templates"][0]["command_pattern"].append("tamper")
        with self.assertRaises(ValueError):
            InducedSlots.restore(state)

    def test_training_budget_and_selection_are_order_invariant(self):
        source = {"glide": "I_GLIDE", "hop": "I_HOP"}
        source.update({"glide " + str(i): "I_GLIDE" for i in range(1200)})
        self.assertEqual(_training(source),
                         _training(dict(reversed(list(source.items())))))
        self.assertEqual(len(_training(source)), LESSON_BUDGET)

    @unittest.skipUnless(os.environ.get("BEAN_EXTERNAL_SCAN") == "1",
                         "pinned public SCAN download opt-in")
    def test_external_disjoint_heldouts(self):
        data, hashes = _fetch()
        report = run_report(data["train"], data["test"], hashes)
        self.assertEqual(len(report["case_receipts"]), TEST_BUDGET * 2)
        self.assertTrue(report["induced_snapshot_restart_verified"])
        self.assertTrue(report["native_sqlite_restart_verified"])
        self.assertEqual(report["case_receipts_sha256"],
                         _digest(report["case_receipts"]))
        self.assertEqual(set(report["cohorts"]), set(COHORTS))
        self.assertTrue(all(row["native_transfer_unverified"]
                            for row in report["case_receipts"]))


if __name__ == "__main__":
    if sys.argv[1:] == ["--report"]:
        data, hashes = _fetch()
        print(json.dumps(run_report(data["train"], data["test"], hashes),
                         sort_keys=True, indent=2))
    else:
        unittest.main()
