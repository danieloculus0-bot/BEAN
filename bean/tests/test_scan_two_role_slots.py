"""Research-only two-role action binding over existing BEAN SCAN experiment.

Extends PR #228's source-derived one-slot templates, without new runtime memory,
a second journal, a SCAN parser, a fixed target verb, or target-label access.
Evaluation uses the NEXT two disjoint 96-case SCAN cohorts and 1,024 examples
for every budget-matched comparator. This is a synthetic compositional probe.

BEAN_EXTERNAL_SCAN=1 python -m unittest -v bean.tests.test_scan_two_role_slots
python -m bean.tests.test_scan_two_role_slots --report
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

from bean.tests.test_external_scan_composition import (
    FILES, LESSON_BUDGET, TEST_BUDGET, _digest, _fetch, _select,
)
from bean.tests.test_scan_induced_slots import InducedSlots, _training, run_report

SCHEMA = "bean.scan_two_role_slots.v1"
SLOTS = ("__ACTION_ROLE_0__", "__ACTION_ROLE_1__")
POLICY = "two_role_slots"
HOLDOUT_OFFSET = 1  # 192 commands after the previous experiment's 192
COHORTS = ("fresh_disjoint_cohort_3", "fresh_disjoint_cohort_4")


def _roles(words, atomic):
    """Bind source-observed atomic actions by first occurrence, not by verb name."""
    return tuple(dict.fromkeys(word for word in words if word in atomic))


class TwoRoleSlots:
    """Two-role anti-unification with exact evidence and ambiguity abstention.

    The previously tested one-role learner is reused unchanged for one-role
    queries. Two-role patterns are derived from paired *source* commands and
    outputs; no SCAN-specific conjunction, grammar or target primitive is coded.
    """

    def __init__(self, training, source_blob):
        self.single = InducedSlots(training, source_blob)
        self.atomic = dict(self.single.atomic)
        self.source_blob = source_blob
        self.two = {}
        for command, output in sorted(training.items()):
            words = command.split()
            roles = _roles(words, self.atomic)
            if len(roles) != 2:
                continue
            actions = tuple(self.atomic[role] for role in roles)
            if len(set(actions)) != 2:
                continue
            output_words = output.split()
            if any(action not in output_words for action in actions):
                continue
            role_slots = dict(zip(roles, SLOTS))
            action_slots = dict(zip(actions, SLOTS))
            key = tuple(role_slots.get(word, word) for word in words)
            value = tuple(action_slots.get(word, word) for word in output_words)
            source = {
                "command": command,
                "evidence_ref": "scan:train:" + sha256(command.encode()).hexdigest()[:24],
                "source_blob": source_blob,
            }
            self.two.setdefault(key, {}).setdefault(value, []).append(source)

    def state(self):
        payload = {
            "schema": SCHEMA,
            "source_blob": self.source_blob,
            "single": self.single.state(),
            "two_templates": [
                {"command_pattern": list(key),
                 "alternatives": [
                     {"action_pattern": list(value), "sources": sources}
                     for value, sources in sorted(options.items())]}
                for key, options in sorted(self.two.items())
            ],
        }
        return {**payload, "state_sha256": _digest(payload)}

    @classmethod
    def restore(cls, state):
        if not isinstance(state, dict) or state.get("schema") != SCHEMA:
            raise ValueError("Unknown two-role schema")
        payload = {key: value for key, value in state.items()
                   if key != "state_sha256"}
        if state.get("state_sha256") != _digest(payload):
            raise ValueError("Two-role snapshot digest mismatch")
        obj = cls.__new__(cls)
        obj.single = InducedSlots.restore(state["single"])
        obj.atomic = dict(obj.single.atomic)
        obj.source_blob = state["source_blob"]
        if obj.single.source_blob != obj.source_blob:
            raise ValueError("Two-role source mismatch")
        obj.two = {}
        for entry in state["two_templates"]:
            key = tuple(entry["command_pattern"])
            if key in obj.two or key.count(SLOTS[0]) == 0 or key.count(SLOTS[1]) == 0:
                raise ValueError("Duplicate or malformed two-role skeleton")
            alternatives = {}
            for option in entry["alternatives"]:
                value = tuple(option["action_pattern"])
                if value in alternatives:
                    raise ValueError("Duplicate action skeleton")
                sources = option["sources"]
                if not sources or any(
                    source.get("source_blob") != obj.source_blob or
                    source.get("evidence_ref") !=
                    "scan:train:" + sha256(source.get("command", "").encode()).hexdigest()[:24]
                    for source in sources
                ):
                    raise ValueError("Missing or invalid training provenance")
                alternatives[value] = list(sources)
            obj.two[key] = alternatives
        if obj.state() != state:
            raise ValueError("Two-role state does not roundtrip")
        return obj

    def predict(self, command):
        words = command.split()
        roles = _roles(words, self.atomic)
        if len(roles) == 1:
            return self.single.predict(command)
        if len(roles) != 2:
            return {"prediction": None, "reason": "not_two_known_actions",
                    "evidence_refs": []}
        key = tuple(dict(zip(roles, SLOTS)).get(word, word) for word in words)
        options = self.two.get(key)
        if not options:
            return {"prediction": None, "reason": "unseen_two_role_skeleton",
                    "evidence_refs": []}
        if len(options) != 1:
            return {
                "prediction": None, "reason": "conflicting_two_role_skeleton",
                "evidence_refs": sorted({
                    row["evidence_ref"] for sources in options.values()
                    for row in sources}),
            }
        pattern, sources = next(iter(options.items()))
        bindings = dict(zip(SLOTS, (self.atomic[role] for role in roles)))
        return {
            "prediction": " ".join(bindings.get(word, word) for word in pattern),
            "reason": "source_induced_two_role_skeleton",
            "evidence_refs": sorted(row["evidence_ref"] for row in sources),
            "source_commands": sorted(row["command"] for row in sources),
            "source_blob": self.source_blob,
        }


def run_two_role_report(train, test, hashes):
    selected = _training(train)
    if len(selected) != LESSON_BUDGET:
        raise AssertionError("Source budget mismatch")
    model = TwoRoleSlots(selected, FILES["train"][1])
    snapshot = model.state()
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "two-role-snapshot.json"
        path.write_text(json.dumps(snapshot, sort_keys=True), encoding="utf-8")
        restored = TwoRoleSlots.restore(json.loads(path.read_text(encoding="utf-8")))
        if _digest(restored.state()) != _digest(snapshot):
            raise AssertionError("Snapshot changed across restart")

    # Freeze all new predictions BEFORE reading any scorer-only target outputs.
    all_holdouts = _select(test, TEST_BUDGET * 4, "heldout")
    old_commands = set(all_holdouts[:TEST_BUDGET * 2])
    commands = all_holdouts[TEST_BUDGET * 2:]
    if len(commands) != TEST_BUDGET * 2 or old_commands.intersection(commands):
        raise AssertionError("Fresh heldout disjointness failed")
    frozen = [restored.predict(command) for command in commands]
    valid_refs = {"scan:train:" + sha256(command.encode()).hexdigest()[:24]
                  for command in selected}
    if any(not set(result["evidence_refs"]).issubset(valid_refs)
           for result in frozen):
        raise AssertionError("Prediction cited non-training evidence")

    # Reuse all prior matched baselines and the actual NativeReasoningService
    # temporary SQLite restart check; do not create a second retrieval stack.
    baseline = run_report(train, test, hashes, holdout_offset=HOLDOUT_OFFSET)
    rows = baseline["case_receipts"]
    if [row["command"] for row in rows] != commands:
        raise AssertionError("Baseline/test selection disagreement")
    prior_receipts_sha = baseline["case_receipts_sha256"]
    for i, (row, result) in enumerate(zip(rows, frozen)):
        row["cohort"] = COHORTS[i // TEST_BUDGET]
        row["predictions"][POLICY] = result["prediction"]
        row["correct"][POLICY] = result["prediction"] == row["scorer_only_output"]
        row["two_role"] = result
        row["two_role_state_sha256"] = snapshot["state_sha256"]
        row["case_sha256"] = _digest({key: value for key, value in row.items()
                                     if key != "case_sha256"})

    cohorts = {}
    for cohort in COHORTS:
        group = [row for row in rows if row["cohort"] == cohort]
        cohorts[cohort] = {
            "cases": len(group),
            "scores_exact_match": {
                name: sum(row["correct"][name] for row in group)
                for name in group[0]["predictions"]
            },
            "coverage": {
                name: sum(row["predictions"][name] is not None for row in group)
                for name in group[0]["predictions"]
            },
            "paired_two_role_minus_single": [
                int(row["correct"][POLICY]) - int(row["correct"]["induced_slots"])
                for row in group
            ],
            "paired_two_role_minus_matched": [
                int(row["correct"][POLICY]) - int(row["correct"]["matched_template"])
                for row in group
            ],
            "two_role_errors": [
                {"command": row["command"], "reason": row["two_role"]["reason"],
                 "evidence_refs": row["two_role"]["evidence_refs"]}
                for row in group if not row["correct"][POLICY]
            ],
        }
    return {
        "schema": SCHEMA,
        "source_revision": os.environ.get("BEAN_SOURCE_SHA", "not_supplied"),
        "benchmark": baseline["benchmark"],
        "split": baseline["split"],
        "source_hashes": hashes,
        "selection_seed": baseline["selection_seed"],
        "holdout_offset": HOLDOUT_OFFSET,
        "training_budget": len(selected),
        "retrieval_budget": baseline["retrieval_budget"],
        "two_role_templates": len(model.two),
        "conflicting_two_role_templates": sum(len(v) > 1 for v in model.two.values()),
        "model_state_sha256": snapshot["state_sha256"],
        "snapshot_restart_verified": True,
        "native_sqlite_restart_verified": baseline["native_sqlite_restart_verified"],
        "prior_baseline_receipts_sha256": prior_receipts_sha,
        "cohorts": cohorts,
        "case_receipts": rows,
        "case_receipts_sha256": _digest(rows),
        "limitations": [
            "Source-derived two-role exact skeletons are not a learned grammar",
            "Two distinct known action roles only; ambiguity forces abstention",
            "Same 1,024 source examples and same SCAN grammar as prior experiment",
            "New disjoint heldouts are still from the original SCAN test split",
            "Full-training comparator uses 13,204 examples, unequal source budget",
            "Research JSON is a temporary snapshot, not canonical Core memory",
            "Native SQLite restart is temporary, not an operating Jetson",
            "No neural training, Axiom event-bus execution, real-world transfer or AGI",
        ],
    }


class TwoRoleControls(unittest.TestCase):
    def test_unseen_two_role_binding_and_one_role_fallback(self):
        train = {
            "glide": "I_GLIDE", "hop": "I_HOP", "skip": "I_SKIP",
            "glide and hop": "I_GLIDE I_HOP",
            "hop after glide": "I_GLIDE I_HOP",
            "glide twice": "I_GLIDE I_GLIDE",
        }
        model = TwoRoleSlots(train, "fictional-source")
        self.assertEqual(model.predict("skip and glide")["prediction"],
                         "I_SKIP I_GLIDE")
        self.assertEqual(model.predict("skip after hop")["prediction"],
                         "I_HOP I_SKIP")
        self.assertEqual(model.predict("skip twice")["prediction"],
                         "I_SKIP I_SKIP")
        self.assertEqual(model.predict("skip and hop after glide")["reason"],
                         "not_two_known_actions")
        self.assertEqual(model.predict("skip or hop")["reason"],
                         "unseen_two_role_skeleton")
        self.assertTrue(model.predict("skip and glide")["evidence_refs"])

    def test_conflicting_source_patterns_abstain(self):
        train = {
            "glide": "I_GLIDE", "hop": "I_HOP", "skip": "I_SKIP",
            "glide and hop": "I_GLIDE I_HOP",
            "hop and glide": "I_GLIDE I_HOP",
            "glide twice": "I_GLIDE I_GLIDE",
        }
        model = TwoRoleSlots(train, "fictional-source")
        result = model.predict("skip and glide")
        self.assertIsNone(result["prediction"])
        self.assertEqual(result["reason"], "conflicting_two_role_skeleton")
        self.assertEqual(len(result["evidence_refs"]), 2)

    def test_snapshot_restart_and_tamper_rejection(self):
        train = {
            "glide": "I_GLIDE", "hop": "I_HOP", "skip": "I_SKIP",
            "glide and hop": "I_GLIDE I_HOP",
            "glide twice": "I_GLIDE I_GLIDE",
        }
        model = TwoRoleSlots(train, "fictional-source")
        state = json.loads(json.dumps(model.state()))
        restored = TwoRoleSlots.restore(state)
        self.assertEqual(model.predict("skip and glide"),
                         restored.predict("skip and glide"))
        state["two_templates"][0]["command_pattern"].append("tamper")
        with self.assertRaises(ValueError):
            TwoRoleSlots.restore(state)

    def test_holdout_offset_never_reuses_prior_cohort(self):
        mapping = {"case-" + str(i): "hidden" for i in range(700)}
        selected = _select(mapping, TEST_BUDGET * 4, "heldout")
        self.assertEqual(len(selected), 384)
        self.assertFalse(set(selected[:192]) & set(selected[192:]))

    @unittest.skipUnless(os.environ.get("BEAN_EXTERNAL_SCAN") == "1",
                         "pinned public SCAN download opt-in")
    def test_fresh_external_two_role_evaluation(self):
        data, hashes = _fetch()
        report = run_two_role_report(data["train"], data["test"], hashes)
        self.assertEqual(len(report["case_receipts"]), 192)
        self.assertEqual(report["case_receipts_sha256"],
                         _digest(report["case_receipts"]))
        self.assertTrue(report["snapshot_restart_verified"])
        self.assertTrue(report["native_sqlite_restart_verified"])
        self.assertEqual(set(report["cohorts"]), set(COHORTS))
        self.assertTrue(all(row["native_transfer_unverified"]
                            for row in report["case_receipts"]))


if __name__ == "__main__":
    if sys.argv[1:] == ["--report"]:
        data, hashes = _fetch()
        print(json.dumps(run_two_role_report(data["train"], data["test"], hashes),
                         sort_keys=True, indent=2))
    else:
        unittest.main()
