"""Source-labeled multi-token action induction for existing BEAN SCAN research.

A two-word command is only a *candidate* anchor until its selected training
label is observed to contain exactly one action token. Source-only selection
reserves candidate labels inside the SAME 1,024-example budget. The matched
control receives the identical selected labels but no phrase normalization.
This is an isolated research wrapper around existing TwoRoleSlots, not a
replacement memory, parser, runtime policy, or SCAN-specific grammar.

BEAN_EXTERNAL_SCAN=1 python -m unittest -v bean.tests.test_scan_phrase_roles
python -m bean.tests.test_scan_phrase_roles --report
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
from bean.tests.test_scan_induced_slots import _training, run_report
from bean.tests.test_scan_source_curriculum import _curriculum_commands, _curriculum_training
from bean.tests.test_scan_two_role_slots import TwoRoleSlots

SCHEMA = "bean.scan_phrase_roles.v1"
POLICY = "phrase_roles"
MATCHED = "same_labels_no_phrase"
PRIOR = "curriculum_two_role"
RANDOM = "random_two_role"
COHORTS = ("fresh_disjoint_cohort_9", "fresh_disjoint_cohort_10")
HOLDOUT_OFFSET = 4
PHRASE_CANDIDATE_CAP = 64


def _source_commands(train, budget=LESSON_BUDGET):
    """Reserve shortest multiword source keys without looking at their labels.

    The earlier curriculum is the starting selection. Replacing a few of its
    examples with two-token source keys changes selection, so a same-label
    no-phrase model is the primary controlled comparison.
    """
    if budget < 8:
        raise ValueError("Insufficient source budget")
    candidates = [
        command for command in train
        if len(command.split()) == 2 and
        all(re.fullmatch(r"[a-z]+", word) for word in command.split())
    ]
    candidates = _select(candidates, min(PHRASE_CANDIDATE_CAP, len(candidates)),
                         "phrase-anchor-candidates")
    if len(candidates) >= budget:
        raise ValueError("Anchor candidates exhaust label budget")
    previous = _curriculum_commands(train, budget)
    selected = candidates + [
        command for command in previous if command not in set(candidates)
    ][:budget - len(candidates)]
    if len(selected) != budget or len(set(selected)) != budget:
        raise AssertionError("Source label selection budget changed")
    return selected


def _source_training(train, budget=LESSON_BUDGET):
    return {command: train[command] for command in _source_commands(train, budget)}


def _phrase_token(phrase):
    # Only lowercase letters, so existing atomic induction sees a single role.
    digest = sha256(phrase.encode("utf-8")).digest()
    return "macro" + "".join(chr(97 + byte % 26) for byte in digest[:14])


class PhraseRoleSlots:
    """Induce minimal multi-token primitives, reuse TwoRoleSlots unchanged.

    Never infer a phrase's output from its spelling. A source command with a
    single output token is a candidate atomic phrase; otherwise it is not.
    All model evidence is mapped back to the ORIGINAL source command SHA.
    """

    def __init__(self, training, source_blob):
        self.source_blob = source_blob
        self.training = dict(sorted(training.items()))
        self.phrases = {
            command: output
            for command, output in self.training.items()
            if len(command.split()) == 2 and
            all(re.fullmatch(r"[a-z]+", word) for word in command.split()) and
            re.fullmatch(r"I_[A-Z]+", output)
        }
        self.tokens = {phrase: _phrase_token(phrase) for phrase in self.phrases}
        if len(set(self.tokens.values())) != len(self.tokens):
            raise ValueError("Phrase token collision")
        if set(self.tokens.values()) & set(self.training):
            raise ValueError("Phrase token conflicts with source command")
        normalized = {}
        self.original_by_normalized = {}
        self.ref_map = {}
        for command, output in self.training.items():
            key, _ = self._normalize(command)
            if key in normalized:
                raise ValueError("Non-injective source normalization")
            normalized[key] = output
            self.original_by_normalized[key] = command
            self.ref_map["scan:train:" + sha256(key.encode()).hexdigest()[:24]] = (
                "scan:train:" + sha256(command.encode()).hexdigest()[:24])
        self.inner = TwoRoleSlots(normalized, source_blob)

    def _normalize(self, command):
        words = command.split()
        output, hits = [], []
        index = 0
        while index < len(words):
            phrase = " ".join(words[index:index + 2])
            if phrase in self.tokens:
                output.append(self.tokens[phrase])
                hits.append(phrase)
                index += 2
            else:
                output.append(words[index])
                index += 1
        return " ".join(output), hits

    def state(self):
        payload = {
            "schema": SCHEMA,
            "source_blob": self.source_blob,
            "training_rows": [[command, output]
                              for command, output in self.training.items()],
            "phrase_anchors": dict(sorted(self.phrases.items())),
            "inner_state": self.inner.state(),
        }
        return {**payload, "state_sha256": _digest(payload)}

    @classmethod
    def restore(cls, state):
        if not isinstance(state, dict) or state.get("schema") != SCHEMA:
            raise ValueError("Unknown phrase-role snapshot schema")
        payload = {key: value for key, value in state.items()
                   if key != "state_sha256"}
        if state.get("state_sha256") != _digest(payload):
            raise ValueError("Phrase-role snapshot digest mismatch")
        TwoRoleSlots.restore(state["inner_state"])
        rows = state["training_rows"]
        if len(rows) != len({row[0] for row in rows}):
            raise ValueError("Duplicate source row")
        obj = cls(dict(rows), state["source_blob"])
        if obj.state() != state:
            raise ValueError("Phrase-role snapshot cannot be reproduced")
        return obj

    def predict(self, command):
        normalized, phrases = self._normalize(command)
        inner = self.inner.predict(normalized)
        refs = {self.ref_map[ref] for ref in inner["evidence_refs"]}
        refs.update("scan:train:" + sha256(phrase.encode()).hexdigest()[:24]
                    for phrase in phrases)
        result = dict(inner)
        result["evidence_refs"] = sorted(refs)
        if "source_commands" in inner:
            result["source_commands"] = sorted(
                self.original_by_normalized[source]
                for source in inner["source_commands"])
        result["phrase_matches"] = phrases
        result["reason"] = ("source_induced_phrase_" + inner["reason"]
                            if phrases else inner["reason"])
        result["source_blob"] = self.source_blob
        return result


def _restore_phrase(model):
    snapshot = model.state()
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "phrase-roles.json"
        path.write_text(json.dumps(snapshot, sort_keys=True), encoding="utf-8")
        restored = PhraseRoleSlots.restore(
            json.loads(path.read_text(encoding="utf-8")))
    if restored.state() != snapshot:
        raise AssertionError("Phrase-role snapshot changed on restart")
    return restored, snapshot


def run_phrase_report(train, test, hashes):
    selected = _source_training(train)
    prior = _curriculum_training(train)
    random = _training(train)
    selections = {POLICY: selected, MATCHED: selected,
                  PRIOR: prior, RANDOM: random}
    if any(len(value) != LESSON_BUDGET for value in selections.values()):
        raise AssertionError("Unequal labeled source budget")
    candidate, candidate_state = _restore_phrase(
        PhraseRoleSlots(selected, FILES["train"][1]))
    models = {POLICY: candidate}
    states = {POLICY: candidate_state}
    for name in (MATCHED, PRIOR, RANDOM):
        model = TwoRoleSlots(selections[name], FILES["train"][1])
        snapshot = model.state()
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / (name + ".json")
            path.write_text(json.dumps(snapshot, sort_keys=True),
                            encoding="utf-8")
            models[name] = TwoRoleSlots.restore(
                json.loads(path.read_text(encoding="utf-8")))
        if models[name].state() != snapshot:
            raise AssertionError("Matched snapshot restart failed")
        states[name] = snapshot

    # Freeze ALL predictions on cohorts 9/10 before reading scorer-only labels.
    all_commands = _select(test, TEST_BUDGET * 10, "heldout")
    previous = all_commands[:TEST_BUDGET * 8]
    commands = all_commands[TEST_BUDGET * 8:]
    if len(commands) != TEST_BUDGET * 2 or set(previous) & set(commands):
        raise AssertionError("Reused earlier holdout")
    frozen = {name: [model.predict(command) for command in commands]
              for name, model in models.items()}
    for name, predictions in frozen.items():
        valid_refs = {
            "scan:train:" + sha256(command.encode()).hexdigest()[:24]
            for command in selections[name]
        }
        if any(not set(result["evidence_refs"]).issubset(valid_refs)
               for result in predictions):
            raise AssertionError("Unselected source cited by " + name)

    baseline = run_report(train, test, hashes, holdout_offset=HOLDOUT_OFFSET)
    rows = baseline["case_receipts"]
    if [row["command"] for row in rows] != commands:
        raise AssertionError("Scorer selected different commands")
    for index, row in enumerate(rows):
        row["cohort"] = COHORTS[index // TEST_BUDGET]
        row["phrase_anchor_hit"] = bool(frozen[POLICY][index]["phrase_matches"])
        for name in models:
            result = frozen[name][index]
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
        by_phrase_hit = {}
        for hit in (False, True):
            subset = [row for row in group if row["phrase_anchor_hit"] == hit]
            by_phrase_hit[str(hit).lower()] = {
                "cases": len(subset),
                "scores": {name: sum(row["correct"][name] for row in subset)
                           for name in (POLICY, MATCHED, PRIOR, RANDOM)},
            }
        cohorts[cohort] = {
            "cases": len(group),
            "scores_exact_match": {
                name: sum(row["correct"][name] for row in group) for name in keys
            },
            "coverage": {
                name: sum(row["predictions"][name] is not None for row in group)
                for name in keys
            },
            "by_phrase_hit": by_phrase_hit,
            "paired_phrase_minus_same_labels": [
                int(row["correct"][POLICY]) - int(row["correct"][MATCHED])
                for row in group
            ],
            "regressions": [
                {"command": row["command"],
                 "candidate_reason": row[POLICY + "_result"]["reason"],
                 "control_refs": row[MATCHED + "_result"]["evidence_refs"]}
                for row in group
                if row["correct"][MATCHED] and not row["correct"][POLICY]
            ],
            "candidate_failures": [
                {"command": row["command"],
                 "reason": row[POLICY + "_result"]["reason"],
                 "evidence_refs": row[POLICY + "_result"]["evidence_refs"]}
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
        "source_input_pool_size": len(train),
        "label_budgets": {name: len(value) for name, value in selections.items()},
        "training_commands": {name: list(value) for name, value in selections.items()},
        "training_commands_sha256": {
            name: _digest(list(value)) for name, value in selections.items()
        },
        "state_sha256": {name: state["state_sha256"]
                         for name, state in states.items()},
        "phrase_anchor_cap": PHRASE_CANDIDATE_CAP,
        "phrase_anchors": dict(sorted(candidate.phrases.items())),
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
            "Two-token anchors require an observed one-token output",
            "Only selected 1,024 source labels are inspected for phrase induction",
            "Phrase candidate reservation changes training selection; same-label control isolates representation",
            "Exact source-derived skeletons do not infer an unseen operator grammar",
            "Fresh cohorts 9/10 remain from one pinned SCAN split",
            "All failures and regressions retained for falsification",
        ],
    }


class PhraseRoleControls(unittest.TestCase):
    @staticmethod
    def _toy():
        return {
            "glide": "I_GLIDE", "hop": "I_HOP", "skip": "I_SKIP",
            "pivot port": "I_TURN_PORT",
            "pivot starboard": "I_TURN_STARBOARD",
            "pivot port and glide": "I_TURN_PORT I_GLIDE",
            "pivot starboard and hop": "I_TURN_STARBOARD I_HOP",
            "pivot port twice": "I_TURN_PORT I_TURN_PORT",
            "glide and hop": "I_GLIDE I_HOP",
        }

    def test_multiword_roles_generalize_to_unseen_combinations(self):
        model = PhraseRoleSlots(self._toy(), "fictional-source")
        result = model.predict("pivot starboard and glide")
        self.assertEqual(result["prediction"], "I_TURN_STARBOARD I_GLIDE")
        self.assertEqual(result["phrase_matches"], ["pivot starboard"])
        self.assertIn("pivot starboard and hop", result["source_commands"])
        self.assertEqual(model.predict("pivot starboard twice")["prediction"],
                         "I_TURN_STARBOARD I_TURN_STARBOARD")
        self.assertEqual(model.predict("pivot starboard")["prediction"],
                         "I_TURN_STARBOARD")
        self.assertIsNone(model.predict("pivot aft")["prediction"])

    def test_conflicting_evidence_abstains(self):
        train = self._toy()
        train["pivot starboard and hop"] = "I_HOP I_TURN_STARBOARD"
        model = PhraseRoleSlots(train, "fictional-source")
        result = model.predict("pivot starboard and glide")
        self.assertIsNone(result["prediction"])
        self.assertIn("conflicting_two_role_skeleton", result["reason"])
        self.assertTrue(result["evidence_refs"])

    def test_snapshot_restart_and_tamper(self):
        model = PhraseRoleSlots(self._toy(), "fictional-source")
        restored, snapshot = _restore_phrase(model)
        self.assertEqual(model.predict("pivot starboard and glide"),
                         restored.predict("pivot starboard and glide"))
        snapshot["phrase_anchors"]["pivot port"] = "I_FAKE"
        with self.assertRaises(ValueError):
            PhraseRoleSlots.restore(snapshot)

    def test_candidate_selection_uses_same_fixed_budget(self):
        train = self._toy()
        train.update({"glide " + str(i): "I_GLIDE" for i in range(30)})
        # Source-only selection delegates to the existing curriculum, which
        # requires at least two source roles and can fill from other keys.
        chosen = _source_commands(train, budget=8)
        self.assertEqual(len(chosen), 8)
        self.assertIn("pivot port", chosen)
        self.assertIn("pivot starboard", chosen)

    @unittest.skipUnless(os.environ.get("BEAN_EXTERNAL_SCAN") == "1",
                         "pinned public SCAN download opt-in")
    def test_fresh_phrase_role_evaluation(self):
        data, hashes = _fetch()
        report = run_phrase_report(data["train"], data["test"], hashes)
        self.assertEqual(len(report["case_receipts"]), 192)
        self.assertEqual(report["case_receipts_sha256"],
                         _digest(report["case_receipts"]))
        self.assertTrue(report["snapshot_restart_verified"])
        self.assertTrue(report["native_sqlite_restart_verified"])


if __name__ == "__main__":
    if sys.argv[1:] == ["--report"]:
        data, hashes = _fetch()
        print(json.dumps(run_phrase_report(data["train"], data["test"], hashes),
                         sort_keys=True, indent=2))
    else:
        unittest.main()
