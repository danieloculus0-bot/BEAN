"""Receipt-only independent audit of BEAN's source-induced operator experiment.

Does not import the candidate or its operator learner. Reconstructs operator
votes directly from archived labeled source rows, checks every source reference,
all 192 case digests, exact matches, paired regressions, restart assertions and
holdout separation. This audit is deliberately separate from model execution.
"""
from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import re
import sys
import unittest


def digest(value):
    return sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                             ensure_ascii=True).encode("utf-8")).hexdigest()


def ref(command):
    return "scan:train:" + sha256(command.encode()).hexdigest()[:24]


def independent_rules(training):
    votes = {}
    for command, output in sorted(training.items()):
        words = command.split()
        for i in range(1, len(words) - 1):
            left, right = " ".join(words[:i]), " ".join(words[i + 1:])
            if left not in training or right not in training:
                continue
            lhs, rhs = training[left], training[right]
            if lhs == rhs:
                continue
            if output == lhs + " " + rhs:
                order = "lr"
            elif output == rhs + " " + lhs:
                order = "rl"
            else:
                continue
            record = {
                "source_command": command, "left": left, "right": right,
                "evidence_refs": sorted({ref(command), ref(left), ref(right)}),
            }
            votes.setdefault(words[i], {"lr": [], "rl": []})[order].append(record)
    return {
        word: {
            "order": next((order for order in ("lr", "rl")
                           if support[order] and not support[
                               "rl" if order == "lr" else "rl"]), None),
            "support": support,
        }
        for word, support in sorted(votes.items())
    }


def audit(candidate, previous):
    rows = candidate["case_receipts"]
    older = previous["case_receipts"]
    if len(rows) != 192 or len(older) != 192:
        raise ValueError("Incomplete 192-case archive")
    commands = [row["command"] for row in rows]
    if len(set(commands)) != 192:
        raise ValueError("Duplicate target command")
    if candidate["source_hashes"] != previous["source_hashes"]:
        raise ValueError("Pinned public source changed")
    if candidate["holdout_offset"] != 5 or previous["holdout_offset"] != 4:
        raise ValueError("Unexpected holdout window")
    old = candidate["previous_holdout_commands"]
    if len(old) != 960 or len(set(old)) != 960 or set(old) & set(commands):
        raise ValueError("Earlier holdouts reused or incomplete")
    if candidate["previous_holdout_commands_sha256"] != digest(old):
        raise ValueError("Prior holdout digest mismatch")
    if not {row["command"] for row in older}.issubset(set(old)):
        raise ValueError("Previous cohort missing from holdout inventory")
    if candidate["case_receipts_sha256"] != digest(rows):
        raise ValueError("Case archive digest mismatch")
    if previous["case_receipts_sha256"] != digest(older):
        raise ValueError("Previous archive digest mismatch")
    if candidate["max_depth"] != 4 or candidate["max_visits"] != 128:
        raise ValueError("Unexpected search budget")
    if not candidate["snapshot_restart_verified"] or not (
            candidate["native_sqlite_restart_verified"]):
        raise ValueError("Restart checks not completed")

    training_rows = candidate["training_rows"]
    if len(training_rows) != 1024 or candidate["training_budget"] != 1024:
        raise ValueError("Unequal labeled source budget")
    if any(not isinstance(row, list) or len(row) != 2
           for row in training_rows):
        raise ValueError("Malformed labeled source row")
    training = dict(training_rows)
    if len(training) != 1024:
        raise ValueError("Duplicate labeled source command")
    if candidate["training_commands_sha256"] != digest(
            [row[0] for row in training_rows]):
        raise ValueError("Labeled source selection hash mismatch")
    if set(training) & set(commands):
        raise ValueError("Source/test overlap")
    expected = independent_rules(training)
    if candidate["operator_rules"] != expected:
        raise ValueError("Operator votes disagree with labeled source evidence")
    if candidate["operator_rule_count"] != len(expected):
        raise ValueError("Operator count mismatch")
    valid_refs = {ref(command) for command in training}
    for name, value in candidate["state_sha256"].items():
        if name not in ("learned_operator_order", "unchanged_phrase_roles",
                        "blind_left_first") or not re.fullmatch(
                            r"[0-9a-f]{64}", value):
            raise ValueError("Malformed or unknown model state digest")

    audited = {}
    policies = ("learned_operator_order", "unchanged_phrase_roles",
                "blind_left_first")
    for cohort in ("fresh_disjoint_cohort_11", "fresh_disjoint_cohort_12"):
        group = [row for row in rows if row["cohort"] == cohort]
        if len(group) != 96:
            raise ValueError("Incomplete cohort")
        keys = tuple(group[0]["predictions"])
        if not set(policies).issubset(keys):
            raise ValueError("Missing same-label controls")
        scores = {name: 0 for name in keys}
        coverage = {name: 0 for name in keys}
        strata = {str(composed).lower(): {
            "cases": 0, "scores": {name: 0 for name in policies}}
            for composed in (False, True)}
        for row in group:
            if row["case_sha256"] != digest({
                    key: value for key, value in row.items()
                    if key != "case_sha256"}):
                raise ValueError("Case digest mismatch")
            result = row[policies[0] + "_result"]
            composed = row["operator_composed"]
            if type(composed) is not bool or composed != result["composed"]:
                raise ValueError("Incorrect composition flag")
            if composed:
                if row["predictions"][policies[1]] is not None:
                    raise ValueError("Candidate overrode non-abstaining control")
                if not result["operator_path"] or any(
                        word not in expected or expected[word]["order"] is None
                        for word in result["operator_path"]):
                    raise ValueError("Unlearned operator used in composition")
            bucket = strata[str(composed).lower()]
            bucket["cases"] += 1
            for name in keys:
                correct = row["predictions"][name] == row["scorer_only_output"]
                if row["correct"][name] != correct:
                    raise ValueError("Incorrect exact-match flag")
                scores[name] += int(correct)
                coverage[name] += int(row["predictions"][name] is not None)
            for name in policies:
                prediction = row[name + "_result"]
                if prediction["prediction"] != row["predictions"][name]:
                    raise ValueError("Prediction/result mismatch")
                if not set(prediction["evidence_refs"]).issubset(valid_refs):
                    raise ValueError("Unselected source evidence")
                if row[name + "_state_sha256"] != (
                        candidate["state_sha256"][name]):
                    raise ValueError("Mixed model revisions")
                bucket["scores"][name] += int(row["correct"][name])
            if not row["native_transfer_unverified"]:
                raise ValueError("Native control provenance changed")

        aggregate = candidate["cohorts"][cohort]
        if scores != aggregate["scores_exact_match"]:
            raise ValueError("Score totals disagree with case evidence")
        if coverage != aggregate["coverage"]:
            raise ValueError("Coverage totals disagree with case evidence")
        if strata != aggregate["by_composition"]:
            raise ValueError("Composition strata mismatch")
        paired_base = [int(row["correct"][policies[0]]) -
                       int(row["correct"][policies[1]]) for row in group]
        paired_blind = [int(row["correct"][policies[0]]) -
                        int(row["correct"][policies[2]]) for row in group]
        if paired_base != aggregate["paired_learned_minus_phrase"] or (
                paired_blind != aggregate["paired_learned_minus_blind"]):
            raise ValueError("Paired comparison vector mismatch")
        losses = sum(value == -1 for value in paired_base)
        failures = sum(not row["correct"][policies[0]] for row in group)
        if losses != len(aggregate["regressions"]) or failures != len(
                aggregate["candidate_failures"]):
            raise ValueError("Regressions or failures omitted")
        audited[cohort] = {
            "scores": {name: scores[name] for name in policies},
            "composed_cases": strata["true"]["cases"],
            "paired_wins": sum(value == 1 for value in paired_base),
            "paired_losses": losses,
            "failures_retained": failures,
        }
    return {
        "source_revision": candidate["source_revision"],
        "cases_verified": 192,
        "case_receipts_sha256": candidate["case_receipts_sha256"],
        "operator_rules_independently_reconstructed": True,
        "disjoint_from_all_previous_ten_cohorts": True,
        "cohorts": audited,
    }


class OperatorAuditControls(unittest.TestCase):
    def test_digest_mutation(self):
        self.assertNotEqual(digest({"v": 1}), digest({"v": 2}))

    def test_missing_archive_rejected(self):
        with self.assertRaises(ValueError):
            audit({"case_receipts": []}, {"case_receipts": []})


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit(
            "Usage: python -m bean.tests.test_scan_operator_audit NEW.json PRIOR.json")
    new = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    prior = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
    print(json.dumps(audit(new, prior), sort_keys=True))
