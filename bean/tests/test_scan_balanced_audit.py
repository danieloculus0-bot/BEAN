"""Receipt-only audit of balanced SCAN role coverage; no model imports.

Compare fresh cohorts 7/8 with archived source-only curriculum cohorts 5/6.
The audit reads completed JSON only and independently recomputes correctness,
case digests, evidence membership, role counts, paired wins and regressions.
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
        raise ValueError("Expected two full 192-case archives")
    commands = [row["command"] for row in rows]
    if len(set(commands)) != 192 or set(commands) & {
            row["command"] for row in older}:
        raise ValueError("Reused or duplicated heldout command")
    if candidate["source_hashes"] != previous["source_hashes"]:
        raise ValueError("Pinned public source hashes changed")
    if candidate["holdout_offset"] != 3 or previous["holdout_offset"] != 2:
        raise ValueError("Incorrect cohort offsets")
    if candidate["single_role_reserve"] != 128:
        raise ValueError("Unregistered role reserve")
    if candidate["case_receipts_sha256"] != digest(rows):
        raise ValueError("Candidate case archive digest mismatch")
    if previous["case_receipts_sha256"] != digest(older):
        raise ValueError("Previous case archive digest mismatch")

    policies = ("balanced_two_role", "curriculum_two_role", "random_two_role")
    source_refs = {}
    state_hashes = candidate["state_sha256"]
    for name in policies:
        training = candidate["training_commands"][name]
        if len(training) != 1024 or len(set(training)) != 1024:
            raise ValueError("Unequal or duplicate labeled source budget")
        if candidate["label_budgets"][name] != 1024:
            raise ValueError("Incorrect declared label budget")
        if candidate["training_commands_sha256"][name] != digest(training):
            raise ValueError("Training selection hash mismatch")
        if set(training) & set(commands):
            raise ValueError("Training/test overlap")
        source_refs[name] = {
            "scan:train:" + sha256(c.encode()).hexdigest()[:24]
            for c in training
        }
        if not re.fullmatch(r"[a-f0-9]{64}", state_hashes[name]):
            raise ValueError("Malformed state hash")

    anchors = {
        command for command in candidate["training_commands"][policies[0]]
        if re.fullmatch(r"[a-z]+", command)
    }
    if not 2 <= len(anchors) <= 32:
        raise ValueError("Unexpected source atomic anchors")
    if not candidate["snapshot_restart_verified"] or not (
            candidate["native_sqlite_restart_verified"]):
        raise ValueError("Restart evidence missing")

    audited = {}
    for cohort in ("fresh_disjoint_cohort_7", "fresh_disjoint_cohort_8"):
        group = [row for row in rows if row["cohort"] == cohort]
        if len(group) != 96:
            raise ValueError("Incomplete cohort")
        keys = tuple(group[0]["predictions"])
        if not set(policies).issubset(keys):
            raise ValueError("Missing candidate or control")
        scores = {name: 0 for name in keys}
        coverage = {name: 0 for name in keys}
        wins = losses = 0
        by_role = {str(k): {"cases": 0,
                           "scores": {name: 0 for name in policies}}
                   for k in (1, 2)}
        for row in group:
            if row["case_sha256"] != digest({
                    k: v for k, v in row.items() if k != "case_sha256"}):
                raise ValueError("Case digest mismatch")
            roles = {w for w in row["command"].split() if w in anchors}
            if row["role_count"] != len(roles):
                raise ValueError("Incorrect case role count")
            if str(row["role_count"]) not in by_role:
                raise ValueError("Unexpected action-role count")
            by_role[str(row["role_count"])]["cases"] += 1
            for name in keys:
                correct = (row["predictions"][name] ==
                           row["scorer_only_output"])
                if row["correct"][name] != correct:
                    raise ValueError("Incorrect scorer correctness")
                scores[name] += int(correct)
                coverage[name] += int(row["predictions"][name] is not None)
            for name in policies:
                result = row[name + "_result"]
                if result["prediction"] != row["predictions"][name]:
                    raise ValueError("Candidate result/prediction mismatch")
                if not set(result["evidence_refs"]).issubset(
                        source_refs[name]):
                    raise ValueError("Unselected source evidence cited")
                if row[name + "_state_sha256"] != state_hashes[name]:
                    raise ValueError("Mixed model snapshot states")
                by_role[str(row["role_count"])]["scores"][name] += int(
                    row["correct"][name])
            wins += int(row["correct"][policies[0]] and not
                        row["correct"][policies[1]])
            losses += int(row["correct"][policies[1]] and not
                          row["correct"][policies[0]])
            if not row["native_transfer_unverified"]:
                raise ValueError("Native evidence scope changed")

        aggregate = candidate["cohorts"][cohort]
        if scores != aggregate["scores_exact_match"]:
            raise ValueError("Aggregate exact-match scores incorrect")
        if coverage != aggregate["coverage"]:
            raise ValueError("Aggregate coverage incorrect")
        if by_role != aggregate["by_role"]:
            raise ValueError("Role-stratified scores incorrect")
        paired = [int(row["correct"][policies[0]]) -
                  int(row["correct"][policies[1]]) for row in group]
        if paired != aggregate["paired_balanced_minus_prior"]:
            raise ValueError("Paired outcomes changed")
        if losses != len(aggregate["regressions"]):
            raise ValueError("Negative regressions omitted")
        failures = sum(not row["correct"][policies[0]] for row in group)
        if failures != len(aggregate["candidate_failures"]):
            raise ValueError("Candidate failures omitted")
        audited[cohort] = {
            "scores": {name: scores[name] for name in policies},
            "by_role": by_role,
            "paired_wins": wins,
            "paired_losses": losses,
            "failures_retained": failures,
        }
    return {
        "source_revision": candidate["source_revision"],
        "case_receipts_sha256": candidate["case_receipts_sha256"],
        "cases_verified": 192,
        "disjoint_from_prior_cohorts": True,
        "cohorts": audited,
    }


class BalancedAuditControls(unittest.TestCase):
    def test_digest_mutation_changes_hash(self):
        self.assertNotEqual(digest({"a": 1}), digest({"a": 2}))

    def test_missing_cases_rejected(self):
        with self.assertRaises(ValueError):
            audit({"case_receipts": []}, {"case_receipts": []})


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit("Usage: python -m bean.tests.test_scan_balanced_audit NEW.json PRIOR.json")
    new = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    prior = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
    print(json.dumps(audit(new, prior), sort_keys=True))
