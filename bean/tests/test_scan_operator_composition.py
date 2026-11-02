"""Source-evidenced binary composition over BEAN's existing SCAN phrase-role learner.

Induce an operator's output order only when a selected labeled source command
can be exactly explained by TWO independently labeled source subcommands.
No operator words, semantics, target labels, or SCAN grammar are hard-coded.
A bounded recursive fallback composes independently predicted subcommands only
when the unchanged phrase learner abstains. Conflicting source orders abstain.
All provenance stays on the existing public-source SHA receipt convention.

BEAN_EXTERNAL_SCAN=1 python -m unittest -v bean.tests.test_scan_operator_composition
python -m bean.tests.test_scan_operator_composition --report
"""
from __future__ import annotations

from hashlib import sha256
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest

from bean.tests.test_external_scan_composition import (
    FILES, LESSON_BUDGET, TEST_BUDGET, _digest, _fetch, _select,
)
from bean.tests.test_scan_induced_slots import run_report
from bean.tests.test_scan_phrase_roles import (
    PhraseRoleSlots, _restore_phrase, _source_training,
)

SCHEMA = "bean.scan_operator_composition.v1"
POLICY = "learned_operator_order"
MATCHED = "unchanged_phrase_roles"
ABLATION = "blind_left_first"
COHORTS = ("fresh_disjoint_cohort_11", "fresh_disjoint_cohort_12")
HOLDOUT_OFFSET = 5
MAX_DEPTH = 4
MAX_VISITS = 128


def _ref(command):
    return "scan:train:" + sha256(command.encode()).hexdigest()[:24]


def _induce_rules(training):
    """Discover source-supported binary split words and their output order."""
    votes = {}
    for command, output in sorted(training.items()):
        words = command.split()
        for i in range(1, len(words) - 1):
            left, right = " ".join(words[:i]), " ".join(words[i + 1:])
            if left not in training or right not in training:
                continue
            lhs, rhs = training[left], training[right]
            if lhs == rhs:
                continue  # Cannot distinguish the order from this example.
            if output == lhs + " " + rhs:
                order = "lr"
            elif output == rhs + " " + lhs:
                order = "rl"
            else:
                continue  # No evidence that this split is compositional.
            record = {
                "source_command": command, "left": left, "right": right,
                "evidence_refs": sorted({_ref(command), _ref(left), _ref(right)}),
            }
            votes.setdefault(words[i], {"lr": [], "rl": []})[order].append(record)
    return {
        word: {
            "order": next((order for order in ("lr", "rl")
                           if support[order] and not support[
                               "rl" if order == "lr" else "lr"]), None),
            "support": support,
        }
        for word, support in sorted(votes.items())
    }


class OperatorComposer:
    """Learned-order or blind-order composition with bounded abstention."""

    def __init__(self, training, source_blob, *, blind_left_first=False):
        self.training = dict(sorted(training.items()))
        self.source_blob = source_blob
        self.blind_left_first = blind_left_first
        self.base = PhraseRoleSlots(self.training, source_blob)
        self.rules = _induce_rules(self.training)

    def state(self):
        payload = {
            "schema": SCHEMA, "source_blob": self.source_blob,
            "blind_left_first": self.blind_left_first,
            "training_rows": [[c, o] for c, o in self.training.items()],
            "operator_rules": self.rules,
            "base_state": self.base.state(),
        }
        return {**payload, "state_sha256": _digest(payload)}

    @classmethod
    def restore(cls, state):
        if not isinstance(state, dict) or state.get("schema") != SCHEMA:
            raise ValueError("Unknown operator snapshot schema")
        payload = {k: v for k, v in state.items() if k != "state_sha256"}
        if state.get("state_sha256") != _digest(payload):
            raise ValueError("Operator snapshot hash mismatch")
        PhraseRoleSlots.restore(state["base_state"])
        rows = state["training_rows"]
        if len(rows) != len({row[0] for row in rows}):
            raise ValueError("Duplicate training row")
        model = cls(dict(rows), state["source_blob"],
                    blind_left_first=state["blind_left_first"])
        if model.state() != state:
            raise ValueError("Operator snapshot cannot be reproduced")
        return model

    def _compose(self, command, depth, visits):
        visits[0] += 1
        base = dict(self.base.predict(command))
        base["composed"] = False
        base["operator_path"] = []
        if base["prediction"] is not None or depth >= MAX_DEPTH or (
                visits[0] > MAX_VISITS):
            return base

        words = command.split()
        candidates = []
        conflict_refs = set()
        for i in range(1, len(words) - 1):
            operator = words[i]
            rule = self.rules.get(operator)
            if rule is None:
                continue
            if rule["order"] is None:
                for records in rule["support"].values():
                    for record in records:
                        conflict_refs.update(record["evidence_refs"])
                continue
            left = self._compose(" ".join(words[:i]), depth + 1, visits)
            right = self._compose(" ".join(words[i + 1:]), depth + 1, visits)
            if left["prediction"] is None or right["prediction"] is None:
                continue
            order = "lr" if self.blind_left_first else rule["order"]
            first, second = ((left, right) if order == "lr"
                             else (right, left))
            output = first["prediction"] + " " + second["prediction"]
            evidence = set(left["evidence_refs"]) | set(right["evidence_refs"])
            for record in rule["support"][rule["order"]]:
                evidence.update(record["evidence_refs"])
            candidates.append({
                "prediction": output, "evidence_refs": sorted(evidence),
                "operator_path": ([operator] + left["operator_path"] +
                                  right["operator_path"]),
            })

        if not candidates:
            if conflict_refs:
                base["reason"] = "conflicting_source_operator"
                base["evidence_refs"] = sorted(
                    set(base["evidence_refs"]) | conflict_refs)
            return base
        outputs = {row["prediction"] for row in candidates}
        all_refs = sorted({ref for row in candidates
                           for ref in row["evidence_refs"]})
        if len(outputs) != 1:
            return {
                "prediction": None, "reason": "ambiguous_operator_parse",
                "evidence_refs": all_refs, "composed": False,
                "operator_path": [],
            }
        return {
            "prediction": candidates[0]["prediction"],
            "reason": ("blind_left_first_composition" if self.blind_left_first
                       else "source_induced_binary_composition"),
            "evidence_refs": all_refs, "composed": True,
            "operator_path": candidates[0]["operator_path"],
        }

    def predict(self, command):
        return self._compose(command, 0, [0])


def _restore(model):
    snapshot = model.state()
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "operator-snapshot.json"
        path.write_text(json.dumps(snapshot, sort_keys=True), encoding="utf-8")
        restored = OperatorComposer.restore(
            json.loads(path.read_text(encoding="utf-8")))
    if restored.state() != snapshot:
        raise AssertionError("Operator snapshot changed after restart")
    return restored, snapshot


def run_operator_report(train, test, hashes):
    selected = _source_training(train)
    if len(selected) != LESSON_BUDGET:
        raise AssertionError("Source label budget changed")
    candidate, candidate_state = _restore(
        OperatorComposer(selected, FILES["train"][1]))
    blind, blind_state = _restore(
        OperatorComposer(selected, FILES["train"][1],
                         blind_left_first=True))
    base, base_state = _restore_phrase(
        PhraseRoleSlots(selected, FILES["train"][1]))
    models = {POLICY: candidate, MATCHED: base, ABLATION: blind}
    states = {POLICY: candidate_state, MATCHED: base_state,
              ABLATION: blind_state}

    ordered = _select(test, TEST_BUDGET * 12, "heldout")
    previous = ordered[:TEST_BUDGET * 10]
    commands = ordered[TEST_BUDGET * 10:]
    if len(commands) != TEST_BUDGET * 2 or set(previous) & set(commands):
        raise AssertionError("Heldout overlap")
    # All three model predictions are frozen before scorer-only outputs.
    frozen = {name: [model.predict(command) for command in commands]
              for name, model in models.items()}
    valid_refs = {_ref(command) for command in selected}
    for predictions in frozen.values():
        if any(not set(result["evidence_refs"]).issubset(valid_refs)
               for result in predictions):
            raise AssertionError("Unselected source cited")

    baseline = run_report(train, test, hashes, holdout_offset=HOLDOUT_OFFSET)
    rows = baseline["case_receipts"]
    if [row["command"] for row in rows] != commands:
        raise AssertionError("Native scorer holdout selection differs")
    for i, row in enumerate(rows):
        row["cohort"] = COHORTS[i // TEST_BUDGET]
        row["operator_composed"] = frozen[POLICY][i]["composed"]
        for name in models:
            result = frozen[name][i]
            row["predictions"][name] = result["prediction"]
            row["correct"][name] = result["prediction"] == row["scorer_only_output"]
            row[name + "_result"] = result
            row[name + "_state_sha256"] = states[name]["state_sha256"]
        row["case_sha256"] = _digest({
            key: value for key, value in row.items() if key != "case_sha256"
        })

    cohorts = {}
    for cohort in COHORTS:
        group = [row for row in rows if row["cohort"] == cohort]
        if len(group) != TEST_BUDGET:
            raise AssertionError("Incomplete cohort")
        keys = tuple(group[0]["predictions"])
        by_composition = {}
        for composed in (False, True):
            subset = [row for row in group
                      if row["operator_composed"] == composed]
            by_composition[str(composed).lower()] = {
                "cases": len(subset),
                "scores": {name: sum(row["correct"][name] for row in subset)
                           for name in models},
            }
        cohorts[cohort] = {
            "cases": len(group),
            "scores_exact_match": {
                name: sum(row["correct"][name] for row in group)
                for name in keys},
            "coverage": {
                name: sum(row["predictions"][name] is not None for row in group)
                for name in keys},
            "by_composition": by_composition,
            "paired_learned_minus_phrase": [
                int(row["correct"][POLICY]) - int(row["correct"][MATCHED])
                for row in group],
            "paired_learned_minus_blind": [
                int(row["correct"][POLICY]) - int(row["correct"][ABLATION])
                for row in group],
            "regressions": [
                {"command": row["command"],
                 "candidate_reason": row[POLICY + "_result"]["reason"],
                 "control_refs": row[MATCHED + "_result"]["evidence_refs"]}
                for row in group
                if row["correct"][MATCHED] and not row["correct"][POLICY]],
            "candidate_failures": [
                {"command": row["command"],
                 "reason": row[POLICY + "_result"]["reason"],
                 "evidence_refs": row[POLICY + "_result"]["evidence_refs"]}
                for row in group if not row["correct"][POLICY]],
        }
    return {
        "schema": SCHEMA,
        "source_revision": os.environ.get("BEAN_SOURCE_SHA", "not_supplied"),
        "benchmark": baseline["benchmark"],
        "split": baseline["split"],
        "source_hashes": hashes,
        "selection_seed": baseline["selection_seed"],
        "source_input_pool_size": len(train),
        "training_budget": len(selected),
        "training_rows": [[c, o] for c, o in selected.items()],
        "training_commands_sha256": _digest(list(selected)),
        "state_sha256": {name: state["state_sha256"]
                         for name, state in states.items()},
        "operator_rules": candidate.rules,
        "operator_rule_count": len(candidate.rules),
        "max_depth": MAX_DEPTH, "max_visits": MAX_VISITS,
        "holdout_offset": HOLDOUT_OFFSET,
        "previous_holdout_commands": previous,
        "previous_holdout_commands_sha256": _digest(previous),
        "snapshot_restart_verified": True,
        "native_sqlite_restart_verified":
            baseline["native_sqlite_restart_verified"],
        "baseline_receipts_sha256": baseline["case_receipts_sha256"],
        "cohorts": cohorts,
        "case_receipts": rows,
        "case_receipts_sha256": _digest(rows),
        "limitations": [
            "Rules require selected exact source labels for both subcommands",
            "One SCAN grammar; no operator transfer tested across domains",
            "A one-example rule may be brittle; conflicting orders abstain",
            "Fallback is bounded to four levels and 128 recursive visits",
            "All 1,024 labels are shared by candidate and both controls",
            "All failed cases and paired regressions retained",
        ],
    }


class OperatorCompositionControls(unittest.TestCase):
    @staticmethod
    def sample():
        return {
            "glide": "I_GLIDE", "hop": "I_HOP", "skip": "I_SKIP",
            "pivot port": "I_TURN_PORT",
            "pivot starboard": "I_TURN_STARBOARD",
            "glide and hop": "I_GLIDE I_HOP",
            "hop after glide": "I_GLIDE I_HOP",
            "glide twice": "I_GLIDE I_GLIDE",
            "hop thrice": "I_HOP I_HOP I_HOP",
            "pivot port twice": "I_TURN_PORT I_TURN_PORT",
        }

    def test_unseen_composed_subcommands_and_order_ablation(self):
        data = self.sample()
        model = OperatorComposer(data, "fictional-source")
        self.assertEqual(model.rules["and"]["order"], "lr")
        self.assertEqual(model.rules["after"]["order"], "rl")
        self.assertEqual(
            model.predict("skip twice and hop thrice")["prediction"],
            "I_SKIP I_SKIP I_HOP I_HOP I_HOP")
        self.assertEqual(
            model.predict("skip twice after hop thrice")["prediction"],
            "I_HOP I_HOP I_HOP I_SKIP I_SKIP")
        blind = OperatorComposer(data, "fictional-source",
                                 blind_left_first=True)
        self.assertEqual(
            blind.predict("skip twice after hop thrice")["prediction"],
            "I_SKIP I_SKIP I_HOP I_HOP I_HOP")
        self.assertTrue(
            model.predict("skip twice after hop thrice")["composed"])
        self.assertTrue(set(model.predict(
            "skip twice after hop thrice")["evidence_refs"]).issubset(
                {_ref(c) for c in data}))

    def test_conflicting_order_abstains_and_preserves_negative_evidence(self):
        data = self.sample()
        data["glide after hop"] = "I_GLIDE I_HOP"
        model = OperatorComposer(data, "fictional-source")
        self.assertIsNone(model.rules["after"]["order"])
        result = model.predict("skip twice after hop thrice")
        self.assertIsNone(result["prediction"])
        self.assertEqual(result["reason"], "conflicting_source_operator")
        self.assertTrue(result["evidence_refs"])

    def test_unknown_operator_abstains(self):
        model = OperatorComposer(self.sample(), "fictional-source")
        self.assertIsNone(
            model.predict("skip twice unless hop thrice")["prediction"])

    def test_restart_and_tamper_rejection(self):
        model = OperatorComposer(self.sample(), "fictional-source")
        restored, snapshot = _restore(model)
        self.assertEqual(model.predict("skip twice after hop thrice"),
                         restored.predict("skip twice after hop thrice"))
        snapshot["operator_rules"]["after"]["order"] = "lr"
        with self.assertRaises(ValueError):
            OperatorComposer.restore(snapshot)

    def test_source_order_does_not_affect_rules(self):
        data = self.sample()
        reversed_data = dict(reversed(list(data.items())))
        self.assertEqual(_induce_rules(data), _induce_rules(reversed_data))

    @unittest.skipUnless(os.environ.get("BEAN_EXTERNAL_SCAN") == "1",
                         "pinned public SCAN download opt-in")
    def test_fresh_operator_composition_evaluation(self):
        data, hashes = _fetch()
        report = run_operator_report(data["train"], data["test"], hashes)
        self.assertEqual(len(report["case_receipts"]), 192)
        self.assertEqual(report["case_receipts_sha256"],
                         _digest(report["case_receipts"]))
        self.assertTrue(report["snapshot_restart_verified"])
        self.assertTrue(report["native_sqlite_restart_verified"])


if __name__ == "__main__":
    if sys.argv[1:] == ["--report"]:
        data, hashes = _fetch()
        print(json.dumps(run_operator_report(
            data["train"], data["test"], hashes), sort_keys=True, indent=2))
    else:
        unittest.main()
