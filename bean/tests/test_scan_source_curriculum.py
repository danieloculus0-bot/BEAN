"""Source-only curriculum selection for BEAN's existing SCAN two-role learner.

One experimental change: allocate a fixed 1,024 labeled-example budget to
distinct two-role input skeletons first, then one-role skeletons. Candidate
selection sees all *source commands*, but only atomic-anchor and selected
source outputs. It never sees test commands or target outputs. Compare against
the unchanged hash-sampled two-role learner and matched structural controls.

BEAN_EXTERNAL_SCAN=1 python -m unittest -v bean.tests.test_scan_source_curriculum
python -m bean.tests.test_scan_source_curriculum --report
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
    FILES, LESSON_BUDGET, SEED, TEST_BUDGET, _digest, _fetch, _select,
)
from bean.tests.test_scan_induced_slots import _training, run_report
from bean.tests.test_scan_two_role_slots import TwoRoleSlots, _roles

SCHEMA = "bean.scan_source_curriculum.v1"
POLICY = "curriculum_two_role"
CONTROL = "random_two_role"
COHORTS = ("fresh_disjoint_cohort_5", "fresh_disjoint_cohort_6")
HOLDOUT_OFFSET = 2
STRATEGY = "source_only_two_role_distinct_skeletons_first"


def _source_skeleton(command, atomic):
    words = command.split()
    roles = _roles(words, atomic)
    if len(roles) not in (1, 2):
        return None
    slots = dict(zip(roles, ("__ACTION_ROLE_0__", "__ACTION_ROLE_1__")))
    return tuple(slots.get(word, word) for word in words)


def _curriculum_commands(train, budget=LESSON_BUDGET):
    """Choose source keys using commands alone after identifying atomic anchors.

    A source command's unselected output is never read. Every comparator
    receives the same number of labels; both can inspect source input keys.
    """
    atomic = {
        command: output for command, output in train.items()
        if re.fullmatch(r"[a-z]+", command)
        and re.fullmatch(r"I_[A-Z]+", output)
    }
    if not 2 <= len(atomic) <= 32 or budget < len(atomic):
        raise ValueError("Invalid source anchors or label budget")
    anchors = sorted(atomic)
    groups = {}
    for command in train:
        if command in atomic:
            continue
        key = _source_skeleton(command, atomic)
        if key is not None:
            groups.setdefault(key, []).append(command)
    # Prioritize the failure class identified in #229. Within each class,
    # deterministic source-only ranking avoids using heldout frequencies.
    ranked = sorted(
        groups,
        key=lambda key: (
            0 if "__ACTION_ROLE_1__" in key else 1,
            sha256((SEED + ":curriculum-key:" + " ".join(key)).encode()).hexdigest(),
            key,
        ),
    )
    picked = []
    for key in ranked:
        tag = "curriculum-representative:" + _digest(list(key))
        picked.append(_select(groups[key], 1, tag)[0])
        if len(picked) + len(anchors) == budget:
            break
    if len(picked) + len(anchors) < budget:
        remaining = set(train) - set(anchors) - set(picked)
        picked.extend(_select(remaining, budget - len(picked) - len(anchors),
                              "curriculum-fill"))
    result = anchors + picked
    if len(result) != budget or len(set(result)) != budget:
        raise AssertionError("Curriculum label budget or uniqueness changed")
    return result


def _curriculum_training(train, budget=LESSON_BUDGET):
    commands = _curriculum_commands(train, budget)
    return {command: train[command] for command in commands}


def _restore_snapshot(model):
    snapshot = model.state()
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "source-curriculum.json"
        path.write_text(json.dumps(snapshot, sort_keys=True), encoding="utf-8")
        restored = TwoRoleSlots.restore(
            json.loads(path.read_text(encoding="utf-8")))
    if restored.state() != snapshot:
        raise AssertionError("Curriculum state changed across restart")
    return restored, snapshot


def run_curriculum_report(train, test, hashes):
    selected = _curriculum_training(train)
    random_selected = _training(train)
    if len(selected) != LESSON_BUDGET or len(random_selected) != LESSON_BUDGET:
        raise AssertionError("Mismatched labeled source budgets")
    candidate, candidate_state = _restore_snapshot(
        TwoRoleSlots(selected, FILES["train"][1]))
    random_model, random_state = _restore_snapshot(
        TwoRoleSlots(random_selected, FILES["train"][1]))

    # This is the NEXT 192 hash-selected commands after the four prior cohorts.
    # Freeze both sets of predictions before passing any scorer-only outputs
    # into the existing independent comparison/reporting code.
    all_commands = _select(test, TEST_BUDGET * 6, "heldout")
    old_commands = set(all_commands[:TEST_BUDGET * 4])
    commands = all_commands[TEST_BUDGET * 4:]
    if len(commands) != TEST_BUDGET * 2 or old_commands.intersection(commands):
        raise AssertionError("Fresh heldout disjointness failed")
    frozen_candidate = [candidate.predict(command) for command in commands]
    frozen_random = [random_model.predict(command) for command in commands]

    candidate_refs = {
        "scan:train:" + sha256(command.encode()).hexdigest()[:24]
        for command in selected
    }
    random_refs = {
        "scan:train:" + sha256(command.encode()).hexdigest()[:24]
        for command in random_selected
    }
    for prediction in frozen_candidate:
        if not set(prediction["evidence_refs"]).issubset(candidate_refs):
            raise AssertionError("Candidate cited unselected source evidence")
    for prediction in frozen_random:
        if not set(prediction["evidence_refs"]).issubset(random_refs):
            raise AssertionError("Control cited unselected source evidence")

    baseline = run_report(train, test, hashes, holdout_offset=HOLDOUT_OFFSET)
    rows = baseline["case_receipts"]
    if [row["command"] for row in rows] != commands:
        raise AssertionError("Native comparator holdout selection disagreed")
    for i, (row, candidate_result, random_result) in enumerate(
            zip(rows, frozen_candidate, frozen_random)):
        row["cohort"] = COHORTS[i // TEST_BUDGET]
        row["predictions"][POLICY] = candidate_result["prediction"]
        row["predictions"][CONTROL] = random_result["prediction"]
        row["correct"][POLICY] = (
            candidate_result["prediction"] == row["scorer_only_output"])
        row["correct"][CONTROL] = (
            random_result["prediction"] == row["scorer_only_output"])
        row["curriculum_result"] = candidate_result
        row["random_result"] = random_result
        row["curriculum_state_sha256"] = candidate_state["state_sha256"]
        row["random_state_sha256"] = random_state["state_sha256"]
        row["case_sha256"] = _digest({
            key: value for key, value in row.items() if key != "case_sha256"
        })

    cohorts = {}
    for cohort in COHORTS:
        group = [row for row in rows if row["cohort"] == cohort]
        if len(group) != TEST_BUDGET:
            raise AssertionError("Incomplete heldout cohort")
        scores = {
            name: sum(row["correct"][name] for row in group)
            for name in group[0]["predictions"]
        }
        coverage = {
            name: sum(row["predictions"][name] is not None for row in group)
            for name in group[0]["predictions"]
        }
        cohorts[cohort] = {
            "cases": len(group),
            "scores_exact_match": scores,
            "coverage": coverage,
            "paired_curriculum_minus_random": [
                int(row["correct"][POLICY]) - int(row["correct"][CONTROL])
                for row in group
            ],
            "regressions": [
                {"command": row["command"],
                 "candidate_reason": row["curriculum_result"]["reason"],
                 "control_evidence_refs": row["random_result"]["evidence_refs"]}
                for row in group
                if row["correct"][CONTROL] and not row["correct"][POLICY]
            ],
            "candidate_failures": [
                {"command": row["command"],
                 "reason": row["curriculum_result"]["reason"]}
                for row in group if not row["correct"][POLICY]
            ],
        }
    return {
        "schema": SCHEMA,
        "source_revision": os.environ.get("BEAN_SOURCE_SHA", "not_supplied"),
        "benchmark": baseline["benchmark"],
        "split": baseline["split"],
        "source_hashes": hashes,
        "selection_seed": SEED,
        "selection_strategy": STRATEGY,
        "source_input_pool_size": len(train),
        "candidate_label_budget": len(selected),
        "control_label_budget": len(random_selected),
        "candidate_training_commands": list(selected),
        "control_training_commands": list(random_selected),
        "candidate_training_commands_sha256": _digest(list(selected)),
        "control_training_commands_sha256": _digest(list(random_selected)),
        "holdout_offset": HOLDOUT_OFFSET,
        "previous_holdout_commands_sha256": _digest(sorted(old_commands)),
        "candidate_state_sha256": candidate_state["state_sha256"],
        "control_state_sha256": random_state["state_sha256"],
        "snapshot_restart_verified": True,
        "native_sqlite_restart_verified": baseline[
            "native_sqlite_restart_verified"],
        "baseline_receipts_sha256": baseline["case_receipts_sha256"],
        "cohorts": cohorts,
        "case_receipts": rows,
        "case_receipts_sha256": _digest(rows),
        "limitations": [
            "Curriculum inspects all source input commands, but only 1,024 labels",
            "Two-role-first selection is a declared bias from prior failure analysis",
            "Candidate can lose one-role cases even when total accuracy improves",
            "Same SCAN grammar and add-primitive split; no new grammar induction",
            "A 13,204-label structural oracle is unequal budget",
            "Temporary research snapshot is not canonical event memory",
            "All case outcomes and negative examples retained for review",
        ],
    }


class CurriculumControls(unittest.TestCase):
    def test_source_only_selection_does_not_read_unselected_labels(self):
        train = {
            "glide": "I_GLIDE", "hop": "I_HOP", "skip": "I_SKIP",
            "glide and hop": "I_GLIDE I_HOP",
            "hop after glide": "I_GLIDE I_HOP",
            "glide twice": "I_GLIDE I_GLIDE",
            "hop twice": "I_HOP I_HOP",
            "skip thrice": "I_SKIP I_SKIP I_SKIP",
        }
        original = _curriculum_commands(train, budget=5)
        self.assertEqual(len(original), 5)
        self.assertEqual(original[:3], ["glide", "hop", "skip"])
        self.assertEqual(sum(" and " in c or " after " in c for c in original), 2)
        mutated = dict(train)
        for command in train:
            if command not in original:
                mutated[command] = "UNOBSERVED_OUTCOME_CHANGED"
        self.assertEqual(original, _curriculum_commands(mutated, budget=5))
        self.assertEqual(original, _curriculum_commands(
            dict(reversed(list(train.items()))), budget=5))

    def test_curriculum_state_survives_restart_and_detects_tampering(self):
        train = {
            "glide": "I_GLIDE", "hop": "I_HOP", "skip": "I_SKIP",
            "glide and hop": "I_GLIDE I_HOP",
            "hop after glide": "I_GLIDE I_HOP",
            "glide twice": "I_GLIDE I_GLIDE",
        }
        model = TwoRoleSlots(_curriculum_training(train, budget=5),
                             "fictional-source")
        restored, state = _restore_snapshot(model)
        self.assertEqual(model.predict("skip and hop"),
                         restored.predict("skip and hop"))
        state["two_templates"][0]["command_pattern"].append("tamper")
        with self.assertRaises(ValueError):
            TwoRoleSlots.restore(state)

    def test_source_only_curriculum_can_sacrifice_one_role(self):
        train = {
            "glide": "I_GLIDE", "hop": "I_HOP", "skip": "I_SKIP",
            "glide and hop": "I_GLIDE I_HOP",
            "hop after glide": "I_GLIDE I_HOP",
            "glide twice": "I_GLIDE I_GLIDE",
        }
        model = TwoRoleSlots(_curriculum_training(train, budget=5),
                             "fictional-source")
        self.assertIsNone(model.predict("skip twice")["prediction"])
        self.assertIsNotNone(model.predict("skip and glide")["prediction"])

    @unittest.skipUnless(os.environ.get("BEAN_EXTERNAL_SCAN") == "1",
                         "pinned public SCAN download opt-in")
    def test_fresh_external_curriculum_vs_random(self):
        data, hashes = _fetch()
        report = run_curriculum_report(data["train"], data["test"], hashes)
        self.assertEqual(len(report["case_receipts"]), 192)
        self.assertTrue(report["snapshot_restart_verified"])
        self.assertTrue(report["native_sqlite_restart_verified"])
        self.assertEqual(report["case_receipts_sha256"],
                         _digest(report["case_receipts"]))


if __name__ == "__main__":
    if sys.argv[1:] == ["--report"]:
        data, hashes = _fetch()
        print(json.dumps(run_curriculum_report(data["train"], data["test"],
                                               hashes), sort_keys=True, indent=2))
    else:
        unittest.main()
