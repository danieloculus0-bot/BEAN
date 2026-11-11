"""Fixed-label-budget balanced role curriculum, stacked on existing BEAN SCAN research.

One falsifiable intervention: reserve up to 128 of 1,024 labeled examples for
distinct single-role source skeletons, then select distinct two-role skeletons.
The earlier two-role-first curriculum and unchanged hash sampler are controls.
No test commands or labels inform source selection. No new memory or runtime.
"""
from __future__ import annotations

from hashlib import sha256
import json
import os
import re
import sys
import unittest

from bean.tests.test_external_scan_composition import (
    FILES, LESSON_BUDGET, SEED, TEST_BUDGET, _digest, _fetch, _select,
)
from bean.tests.test_scan_induced_slots import _training, run_report
from bean.tests.test_scan_source_curriculum import (
    _curriculum_training, _restore_snapshot, _source_skeleton,
)
from bean.tests.test_scan_two_role_slots import TwoRoleSlots, _roles

SCHEMA = "bean.scan_balanced_curriculum.v1"
POLICY = "balanced_two_role"
PRIOR = "curriculum_two_role"
CONTROL = "random_two_role"
COHORTS = ("fresh_disjoint_cohort_7", "fresh_disjoint_cohort_8")
HOLDOUT_OFFSET = 3
SINGLE_ROLE_RESERVE = 128
STRATEGY = "source_only_distinct_single_role_reserve_128_then_two_role"


def _balanced_commands(train, budget=LESSON_BUDGET):
    """Inspect unlabeled source keys, then purchase exactly budget labels.

    The four atomic anchors are the only labels inspected before selection.
    Each selected source skeleton gets one label before any filler is chosen.
    """
    atomic = {
        command: output for command, output in train.items()
        if re.fullmatch(r"[a-z]+", command)
        and re.fullmatch(r"I_[A-Z]+", output)
    }
    if not 2 <= len(atomic) <= 32 or budget <= len(atomic):
        raise ValueError("Invalid atomic anchors or budget")
    anchors = sorted(atomic)
    groups = {1: {}, 2: {}}
    for command in train:
        if command in atomic:
            continue
        key = _source_skeleton(command, atomic)
        if key is None:
            continue
        role_count = 2 if "__ACTION_ROLE_1__" in key else 1
        groups[role_count].setdefault(key, []).append(command)

    def ranked_keys(role_count):
        return sorted(groups[role_count], key=lambda key: (
            sha256((SEED + ":balanced:" + str(role_count) + ":" +
                    " ".join(key)).encode()).hexdigest(), key))

    selected = list(anchors)
    single_reserve = min(SINGLE_ROLE_RESERVE, max(1, budget // 8),
                         budget - len(anchors))
    for key in ranked_keys(1)[:single_reserve]:
        selected.append(_select(groups[1][key], 1,
                                "balanced-single:" + _digest(list(key)))[0])
    for key in ranked_keys(2):
        if len(selected) >= budget:
            break
        selected.append(_select(groups[2][key], 1,
                                "balanced-double:" + _digest(list(key)))[0])
    if len(selected) < budget:
        # Only source keys, not heldout frequencies or unseen source labels.
        remaining = set(train) - set(selected)
        selected.extend(_select(remaining, budget - len(selected),
                                "balanced-fill"))
    if len(selected) != budget or len(set(selected)) != budget:
        raise AssertionError("Unbalanced or duplicate labeled source budget")
    return selected


def _balanced_training(train, budget=LESSON_BUDGET):
    return {command: train[command] for command in
            _balanced_commands(train, budget)}


def run_balanced_report(train, test, hashes):
    chosen = _balanced_training(train)
    prior = _curriculum_training(train)
    random = _training(train)
    if any(len(group) != LESSON_BUDGET for group in (chosen, prior, random)):
        raise AssertionError("Unequal label budgets")
    candidate, candidate_state = _restore_snapshot(
        TwoRoleSlots(chosen, FILES["train"][1]))
    previous, previous_state = _restore_snapshot(
        TwoRoleSlots(prior, FILES["train"][1]))
    control, control_state = _restore_snapshot(
        TwoRoleSlots(random, FILES["train"][1]))

    all_commands = _select(test, TEST_BUDGET * 8, "heldout")
    older = set(all_commands[:TEST_BUDGET * 6])
    commands = all_commands[TEST_BUDGET * 6:]
    if len(commands) != TEST_BUDGET * 2 or older.intersection(commands):
        raise AssertionError("New cohorts overlap earlier holdouts")
    # Freeze every prediction before any scorer-only target is retrieved.
    frozen = {
        POLICY: [candidate.predict(command) for command in commands],
        PRIOR: [previous.predict(command) for command in commands],
        CONTROL: [control.predict(command) for command in commands],
    }
    selections = {POLICY: chosen, PRIOR: prior, CONTROL: random}
    states = {POLICY: candidate_state, PRIOR: previous_state,
              CONTROL: control_state}
    for name, predictions in frozen.items():
        valid = {"scan:train:" + sha256(c.encode()).hexdigest()[:24]
                 for c in selections[name]}
        if any(not set(result["evidence_refs"]).issubset(valid)
               for result in predictions):
            raise AssertionError("Prediction cited unlabeled source")

    baseline = run_report(train, test, hashes, holdout_offset=HOLDOUT_OFFSET)
    rows = baseline["case_receipts"]
    if [row["command"] for row in rows] != commands:
        raise AssertionError("Scorer selected different holdout commands")
    for i, row in enumerate(rows):
        row["cohort"] = COHORTS[i // TEST_BUDGET]
        roles = _roles(row["command"].split(), candidate.atomic)
        row["role_count"] = len(roles)
        for name in frozen:
            result = frozen[name][i]
            row["predictions"][name] = result["prediction"]
            row["correct"][name] = (
                result["prediction"] == row["scorer_only_output"])
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
        policies = tuple(group[0]["predictions"])
        scores = {name: sum(row["correct"][name] for row in group)
                  for name in policies}
        coverage = {name: sum(row["predictions"][name] is not None
                              for row in group) for name in policies}
        by_role = {}
        for count in (1, 2):
            subset = [row for row in group if row["role_count"] == count]
            by_role[str(count)] = {
                "cases": len(subset),
                "scores": {name: sum(row["correct"][name] for row in subset)
                           for name in (POLICY, PRIOR, CONTROL)},
            }
        cohorts[cohort] = {
            "cases": len(group),
            "scores_exact_match": scores,
            "coverage": coverage,
            "by_role": by_role,
            "paired_balanced_minus_prior": [
                int(row["correct"][POLICY]) - int(row["correct"][PRIOR])
                for row in group
            ],
            "regressions": [
                {"command": row["command"],
                 "candidate_reason": row[POLICY + "_result"]["reason"],
                 "prior_evidence_refs": row[PRIOR + "_result"]["evidence_refs"]}
                for row in group
                if row["correct"][PRIOR] and not row["correct"][POLICY]
            ],
            "candidate_failures": [
                {"command": row["command"],
                 "reason": row[POLICY + "_result"]["reason"]}
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
        "single_role_reserve": SINGLE_ROLE_RESERVE,
        "source_input_pool_size": len(train),
        "label_budgets": {name: len(selections[name]) for name in selections},
        "training_commands": {name: list(selections[name])
                              for name in selections},
        "training_commands_sha256": {
            name: _digest(list(selections[name])) for name in selections},
        "state_sha256": {name: states[name]["state_sha256"]
                         for name in states},
        "holdout_offset": HOLDOUT_OFFSET,
        "previous_holdout_commands_sha256": _digest(sorted(older)),
        "snapshot_restart_verified": True,
        "native_sqlite_restart_verified":
            baseline["native_sqlite_restart_verified"],
        "baseline_receipts_sha256": baseline["case_receipts_sha256"],
        "cohorts": cohorts,
        "case_receipts": rows,
        "case_receipts_sha256": _digest(rows),
        "limitations": [
            "One fixed 128-source single-role reserve, not a tuned optimum",
            "All 13,204 source input keys visible; only 1,024 output labels",
            "Role categories and target commands not used in selection",
            "SCAN single grammar; no independent cross-domain transfer",
            "Full-training structural lookup has unequal label budget",
            "All failures and paired regressions retained",
        ],
    }


class BalancedCurriculumControls(unittest.TestCase):
    @staticmethod
    def sample():
        return {
            "glide": "I_GLIDE", "hop": "I_HOP", "skip": "I_SKIP",
            "glide twice": "I_GLIDE I_GLIDE",
            "hop thrice": "I_HOP I_HOP I_HOP",
            "glide and hop": "I_GLIDE I_HOP",
            "hop after glide": "I_GLIDE I_HOP",
            "glide after hop": "I_HOP I_GLIDE",
            "hop and glide": "I_HOP I_GLIDE",
        }

    def test_reserves_single_and_two_role_skeletons(self):
        train = self.sample()
        commands = _balanced_commands(train, budget=6)
        self.assertEqual(len(commands), 6)
        self.assertEqual(commands[:3], ["glide", "hop", "skip"])
        self.assertEqual(sum(" twice" in c or " thrice" in c
                             for c in commands), 1)
        self.assertEqual(sum(" and " in c or " after " in c
                             for c in commands), 2)
        model = TwoRoleSlots(_balanced_training(train, budget=6),
                             "fictional-source")
        self.assertTrue(model.single.templates)
        self.assertTrue(model.two)

    def test_unselected_labels_do_not_change_selection(self):
        train = self.sample()
        original = _balanced_commands(train, budget=6)
        mutated = dict(train)
        for command in train:
            if command not in original:
                mutated[command] = "UNOBSERVED_CHANGED"
        self.assertEqual(original, _balanced_commands(mutated, budget=6))
        self.assertEqual(original, _balanced_commands(
            dict(reversed(list(train.items()))), budget=6))

    def test_snapshot_restart_and_tamper_rejection(self):
        model = TwoRoleSlots(_balanced_training(self.sample(), budget=6),
                             "fictional-source")
        restored, snapshot = _restore_snapshot(model)
        self.assertEqual(model.predict("skip and glide"),
                         restored.predict("skip and glide"))
        snapshot["two_templates"][0]["command_pattern"].append("tamper")
        with self.assertRaises(ValueError):
            TwoRoleSlots.restore(snapshot)

    def test_holdout_disjointness(self):
        mapping = {"case-" + str(i): "hidden" for i in range(850)}
        ordered = _select(mapping, TEST_BUDGET * 8, "heldout")
        self.assertEqual(len(ordered), 768)
        self.assertFalse(set(ordered[:576]) & set(ordered[576:]))

    @unittest.skipUnless(os.environ.get("BEAN_EXTERNAL_SCAN") == "1",
                         "pinned public SCAN download opt-in")
    def test_fresh_balanced_evaluation(self):
        data, hashes = _fetch()
        report = run_balanced_report(data["train"], data["test"], hashes)
        self.assertEqual(len(report["case_receipts"]), 192)
        self.assertEqual(report["case_receipts_sha256"],
                         _digest(report["case_receipts"]))
        self.assertTrue(report["snapshot_restart_verified"])
        self.assertTrue(report["native_sqlite_restart_verified"])


if __name__ == "__main__":
    if sys.argv[1:] == ["--report"]:
        data, hashes = _fetch()
        print(json.dumps(run_balanced_report(data["train"], data["test"],
                                             hashes), sort_keys=True, indent=2))
    else:
        unittest.main()
