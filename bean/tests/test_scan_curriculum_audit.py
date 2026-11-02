"""Independent archived-receipt auditor for source-only SCAN curriculum.

Does not import or run the candidate, train on data, or infer missing outcomes.
Verifies the new 192-case archive against #229's prior 192-case archive.
"""
from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import sys
import unittest


def digest(value):
    return sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                             ensure_ascii=True).encode("utf-8")).hexdigest()


def audit(candidate, previous):
    rows = candidate["case_receipts"]
    older = previous["case_receipts"]
    if len(rows) != 192 or len(older) != 192:
        raise ValueError("Expected 192 new and 192 previous cases")
    commands = [row["command"] for row in rows]
    if len(set(commands)) != 192 or set(commands) & {
            row["command"] for row in older}:
        raise ValueError("Repeated or previously tested commands")
    if candidate["source_hashes"] != previous["source_hashes"]:
        raise ValueError("Source dataset changed")
    if candidate["candidate_label_budget"] != 1024 or (
            candidate["control_label_budget"] != 1024):
        raise ValueError("Label budgets are not equal")
    if candidate["holdout_offset"] != 2 or previous["holdout_offset"] != 1:
        raise ValueError("Incorrect fresh cohort offsets")
    if candidate["case_receipts_sha256"] != digest(rows):
        raise ValueError("Candidate archive digest mismatch")
    if previous["case_receipts_sha256"] != digest(older):
        raise ValueError("Previous archive digest mismatch")

    refs = {}
    for key, prefix in (
            ("candidate_training_commands", "candidate"),
            ("control_training_commands", "control")):
        source = candidate[key]
        if len(source) != 1024 or len(set(source)) != 1024:
            raise ValueError("Duplicate or missing labeled source")
        if digest(source) != candidate[prefix + "_training_commands_sha256"]:
            raise ValueError("Training selection digest mismatch")
        if set(source) & set(commands):
            raise ValueError("Training/holdout command overlap")
        refs[prefix] = {
            "scan:train:" + sha256(command.encode()).hexdigest()[:24]
            for command in source
        }

    cohorts = {}
    for cohort in ("fresh_disjoint_cohort_5", "fresh_disjoint_cohort_6"):
        group = [row for row in rows if row["cohort"] == cohort]
        if len(group) != 96:
            raise ValueError("Incomplete cohort")
        policies = tuple(group[0]["predictions"])
        if not {"curriculum_two_role", "random_two_role",
                "matched_template"}.issubset(policies):
            raise ValueError("Required matched policies absent")
        score = {policy: 0 for policy in policies}
        coverage = {policy: 0 for policy in policies}
        wins = losses = 0
        for row in group:
            if row["case_sha256"] != digest({
                    key: value for key, value in row.items()
                    if key != "case_sha256"}):
                raise ValueError("Case receipt digest mismatch")
            if row["curriculum_state_sha256"] != candidate[
                    "candidate_state_sha256"]:
                raise ValueError("Candidate mixed snapshot states")
            if row["random_state_sha256"] != candidate[
                    "control_state_sha256"]:
                raise ValueError("Control mixed snapshot states")
            for policy in policies:
                correct = (row["predictions"][policy] ==
                           row["scorer_only_output"])
                if row["correct"][policy] != correct:
                    raise ValueError("Incorrect scorer flag")
                score[policy] += int(correct)
                coverage[policy] += int(
                    row["predictions"][policy] is not None)
            if not set(row["curriculum_result"]["evidence_refs"]).issubset(
                    refs["candidate"]):
                raise ValueError("Candidate cited unselected evidence")
            if not set(row["random_result"]["evidence_refs"]).issubset(
                    refs["control"]):
                raise ValueError("Control cited unselected evidence")
            new = row["correct"]["curriculum_two_role"]
            old = row["correct"]["random_two_role"]
            wins += int(new and not old)
            losses += int(old and not new)
            if not row["native_transfer_unverified"]:
                raise ValueError("Native provenance status changed")
        aggregate = candidate["cohorts"][cohort]
        if score != aggregate["scores_exact_match"]:
            raise ValueError("Aggregate scores changed")
        if coverage != aggregate["coverage"]:
            raise ValueError("Aggregate coverage changed")
        if [int(row["correct"]["curriculum_two_role"]) -
            int(row["correct"]["random_two_role"]) for row in group] != (
                aggregate["paired_curriculum_minus_random"]):
            raise ValueError("Paired comparison changed")
        regressions = [row for row in group
                       if row["correct"]["random_two_role"]
                       and not row["correct"]["curriculum_two_role"]]
        if len(regressions) != len(aggregate["regressions"]):
            raise ValueError("Negative cases omitted")
        failures = [row for row in group
                    if not row["correct"]["curriculum_two_role"]]
        if len(failures) != len(aggregate["candidate_failures"]):
            raise ValueError("Candidate failures omitted")
        cohorts[cohort] = {
            "scores": score,
            "coverage": coverage,
            "paired_wins": wins,
            "paired_losses": losses,
            "negative_cases_retained": len(failures),
        }
    return {
        "source_revision": candidate["source_revision"],
        "source_hashes": candidate["source_hashes"],
        "case_receipts_sha256": candidate["case_receipts_sha256"],
        "cases_verified": 192,
        "fresh_disjoint_from_previous": True,
        "cohorts": cohorts,
    }


class CurriculumAuditControls(unittest.TestCase):
    def test_digest_detects_mutation(self):
        self.assertNotEqual(digest({"a": 1}), digest({"a": 2}))

    def test_rejects_missing_archive(self):
        with self.assertRaises(ValueError):
            audit({"case_receipts": []}, {"case_receipts": []})


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit("Usage: python -m bean.tests.test_scan_curriculum_audit NEW.json PRIOR.json")
    candidate = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    previous = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
    print(json.dumps(audit(candidate, previous), sort_keys=True))
