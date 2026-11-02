"""Independent receipt-only verifier for two-token SCAN role induction.

Never imports the candidate learner. Recomputes all 192 correctness flags,
case digests, evidence membership, training budgets, strata, wins, losses,
failures and cohort separation from completed JSON. Does not trust summaries.
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


def audit(candidate, previous):
    rows = candidate["case_receipts"]
    older = previous["case_receipts"]
    if len(rows) != 192 or len(older) != 192:
        raise ValueError("Expected two complete 192-case archives")
    commands = [row["command"] for row in rows]
    if len(set(commands)) != 192:
        raise ValueError("Duplicate target command")
    if candidate["source_hashes"] != previous["source_hashes"]:
        raise ValueError("Public source hashes changed")
    if candidate["holdout_offset"] != 4 or previous["holdout_offset"] != 3:
        raise ValueError("Unexpected holdout offsets")
    old_commands = candidate["previous_holdout_commands"]
    if len(old_commands) != 768 or len(set(old_commands)) != 768:
        raise ValueError("Incomplete earlier holdout inventory")
    if candidate["previous_holdout_commands_sha256"] != digest(old_commands):
        raise ValueError("Earlier holdout inventory digest mismatch")
    if set(commands) & set(old_commands):
        raise ValueError("Overlapping earlier and new heldouts")
    if not {row["command"] for row in older}.issubset(set(old_commands)):
        raise ValueError("Previous archive not represented in holdout inventory")
    if candidate["case_receipts_sha256"] != digest(rows):
        raise ValueError("Candidate archive digest mismatch")
    if previous["case_receipts_sha256"] != digest(older):
        raise ValueError("Previous archive digest mismatch")
    if candidate["phrase_anchor_cap"] != 64:
        raise ValueError("Unregistered phrase candidate budget")
    if not candidate["snapshot_restart_verified"] or not (
            candidate["native_sqlite_restart_verified"]):
        raise ValueError("Restart evidence missing")

    policies = ("phrase_roles", "same_labels_no_phrase",
                "curriculum_two_role", "random_two_role")
    if candidate["training_commands"][policies[0]] != (
            candidate["training_commands"][policies[1]]):
        raise ValueError("Primary control did not use identical selected labels")
    selected_refs = {}
    for name in policies:
        training = candidate["training_commands"][name]
        if len(training) != 1024 or len(set(training)) != 1024:
            raise ValueError("Wrong labeled source budget")
        if candidate["label_budgets"][name] != 1024:
            raise ValueError("Wrong declared source budget")
        if candidate["training_commands_sha256"][name] != digest(training):
            raise ValueError("Training selection digest mismatch")
        if set(training) & set(commands):
            raise ValueError("Training/test overlap")
        selected_refs[name] = {
            "scan:train:" + sha256(command.encode()).hexdigest()[:24]
            for command in training
        }
        if not re.fullmatch(r"[a-f0-9]{64}", candidate["state_sha256"][name]):
            raise ValueError("Invalid snapshot hash")

    phrase_anchors = candidate["phrase_anchors"]
    if len(phrase_anchors) > 64:
        raise ValueError("More phrase anchors than selected candidates")
    for phrase, output in phrase_anchors.items():
        if phrase not in candidate["training_commands"][policies[0]]:
            raise ValueError("Phrase anchor was not labeled")
        if len(phrase.split()) != 2 or not re.fullmatch(r"I_[A-Z_]+", output):
            raise ValueError("Phrase anchor is not minimal atomic output")

    audited = {}
    for cohort in ("fresh_disjoint_cohort_9", "fresh_disjoint_cohort_10"):
        group = [row for row in rows if row["cohort"] == cohort]
        if len(group) != 96:
            raise ValueError("Incomplete cohort")
        keys = tuple(group[0]["predictions"])
        if not set(policies).issubset(keys):
            raise ValueError("Missing candidate or matched controls")
        scores = {name: 0 for name in keys}
        coverage = {name: 0 for name in keys}
        strata = {str(hit).lower(): {
            "cases": 0, "scores": {name: 0 for name in policies}}
            for hit in (False, True)}
        wins = losses = 0
        for row in group:
            if row["case_sha256"] != digest({
                    key: value for key, value in row.items()
                    if key != "case_sha256"}):
                raise ValueError("Case receipt digest mismatch")
            hit = bool(row["phrase_anchor_hit"])
            matches = row[policies[0] + "_result"]["phrase_matches"]
            if hit != bool(matches):
                raise ValueError("Incorrect phrase hit flag")
            if any(phrase not in phrase_anchors or
                   phrase not in row["command"] for phrase in matches):
                raise ValueError("Unobserved phrase used in heldout")
            bucket = strata[str(hit).lower()]
            bucket["cases"] += 1
            for name in keys:
                correct = row["predictions"][name] == row["scorer_only_output"]
                if row["correct"][name] != correct:
                    raise ValueError("Incorrect correctness flag")
                scores[name] += int(correct)
                coverage[name] += int(row["predictions"][name] is not None)
            for name in policies:
                result = row[name + "_result"]
                if result["prediction"] != row["predictions"][name]:
                    raise ValueError("Result/prediction mismatch")
                if not set(result["evidence_refs"]).issubset(
                        selected_refs[name]):
                    raise ValueError("Unselected source evidence")
                if row[name + "_state_sha256"] != (
                        candidate["state_sha256"][name]):
                    raise ValueError("Mixed snapshot states")
                bucket["scores"][name] += int(row["correct"][name])
            wins += int(row["correct"][policies[0]] and not
                        row["correct"][policies[1]])
            losses += int(row["correct"][policies[1]] and not
                          row["correct"][policies[0]])
            if not row["native_transfer_unverified"]:
                raise ValueError("Native comparator scope changed")
        aggregate = candidate["cohorts"][cohort]
        if scores != aggregate["scores_exact_match"]:
            raise ValueError("Wrong aggregate scores")
        if coverage != aggregate["coverage"]:
            raise ValueError("Wrong coverage counts")
        if strata != aggregate["by_phrase_hit"]:
            raise ValueError("Wrong phrase-hit stratification")
        paired = [int(row["correct"][policies[0]]) -
                  int(row["correct"][policies[1]]) for row in group]
        if paired != aggregate["paired_phrase_minus_same_labels"]:
            raise ValueError("Wrong paired outcome vector")
        if losses != len(aggregate["regressions"]):
            raise ValueError("Omitted paired regressions")
        failures = sum(not row["correct"][policies[0]] for row in group)
        if failures != len(aggregate["candidate_failures"]):
            raise ValueError("Omitted negative cases")
        audited[cohort] = {
            "scores": {name: scores[name] for name in policies},
            "by_phrase_hit": strata,
            "paired_wins": wins,
            "paired_losses": losses,
            "failures_retained": failures,
        }
    return {
        "source_revision": candidate["source_revision"],
        "case_receipts_sha256": candidate["case_receipts_sha256"],
        "cases_verified": 192,
        "disjoint_from_all_previous_eight_cohorts": True,
        "cohorts": audited,
    }


class PhraseAuditControls(unittest.TestCase):
    def test_digest_mutation_detected(self):
        self.assertNotEqual(digest({"x": 1}), digest({"x": 2}))

    def test_incomplete_archive_rejected(self):
        with self.assertRaises(ValueError):
            audit({"case_receipts": []}, {"case_receipts": []})


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit("Usage: python -m bean.tests.test_scan_phrase_audit NEW.json PRIOR.json")
    new = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    prior = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
    print(json.dumps(audit(new, prior), sort_keys=True))
