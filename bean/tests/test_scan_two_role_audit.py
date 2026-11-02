"""Independent receipt-only verifier for the two-role SCAN research experiment.

Reads archived JSON only. Never imports the candidate, trains a model, downloads
a dataset, accesses the Jetson, or infers missing predictions.
"""
from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import sys
import unittest


def digest(value):
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"),
                     ensure_ascii=True).encode("utf-8")
    return sha256(raw).hexdigest()


def audit(candidate, previous):
    rows = candidate["case_receipts"]
    older = previous["case_receipts"]
    if len(rows) != 192 or len(older) != 192:
        raise ValueError("Expected both independent 192-case archives")
    if len({row["command"] for row in rows}) != 192:
        raise ValueError("Duplicate candidate case")
    if {row["command"] for row in rows} & {row["command"] for row in older}:
        raise ValueError("Candidate reused prior heldout commands")
    if candidate["source_hashes"] != previous["source_hashes"]:
        raise ValueError("Source dataset changed")
    if candidate["training_budget"] != 1024 or previous["training_budget"] != 1024:
        raise ValueError("Source budget mismatch")
    if candidate["holdout_offset"] != 1 or previous["holdout_offset"] != 0:
        raise ValueError("Unexpected cohort offset")
    if candidate["case_receipts_sha256"] != digest(rows):
        raise ValueError("Candidate archive digest mismatch")
    if previous["case_receipts_sha256"] != digest(older):
        raise ValueError("Previous archive digest mismatch")
    policies = tuple(rows[0]["predictions"])
    if "two_role_slots" not in policies or "induced_slots" not in policies:
        raise ValueError("Missing matched candidate or baseline")
    counts = {}
    for cohort in ("fresh_disjoint_cohort_3", "fresh_disjoint_cohort_4"):
        group = [row for row in rows if row["cohort"] == cohort]
        if len(group) != 96:
            raise ValueError("Cohort not exactly 96 cases")
        score = {policy: 0 for policy in policies}
        coverage = {policy: 0 for policy in policies}
        wins = losses = 0
        for row in group:
            if row["case_sha256"] != digest({
                key: value for key, value in row.items()
                if key != "case_sha256"
            }):
                raise ValueError("Case digest mismatch")
            if row["two_role_state_sha256"] != candidate["model_state_sha256"]:
                raise ValueError("Mixed model states")
            for policy in policies:
                prediction = row["predictions"][policy]
                correct = prediction == row["scorer_only_output"]
                if row["correct"][policy] != correct:
                    raise ValueError("Scorer flag mismatch")
                score[policy] += int(correct)
                coverage[policy] += int(prediction is not None)
            new = row["correct"]["two_role_slots"]
            old = row["correct"]["induced_slots"]
            wins += int(new and not old)
            losses += int(old and not new)
            if not row["native_transfer_unverified"]:
                raise ValueError("Native transfer claim changed")
            if not all(ref.startswith("scan:train:") for ref in
                       row["two_role"]["evidence_refs"]):
                raise ValueError("Invalid source evidence reference")
        if score != candidate["cohorts"][cohort]["scores_exact_match"]:
            raise ValueError("Aggregate score mismatch")
        if coverage != candidate["cohorts"][cohort]["coverage"]:
            raise ValueError("Aggregate coverage mismatch")
        counts[cohort] = {
            "scores": score,
            "paired_two_role_vs_one_slot": {"wins": wins, "losses": losses},
            "coverage": coverage,
        }
    return {
        "source_revision": candidate["source_revision"],
        "source_hashes": candidate["source_hashes"],
        "case_receipts_sha256": candidate["case_receipts_sha256"],
        "model_state_sha256": candidate["model_state_sha256"],
        "fresh_disjoint_verified": True,
        "cases_verified": len(rows),
        "cohorts": counts,
    }


class AuditControls(unittest.TestCase):
    def test_independent_digest_changes_on_mutation(self):
        row = {"command": "glide and hop", "prediction": "I_GLIDE I_HOP"}
        self.assertNotEqual(digest(row), digest({**row, "prediction": "I_HOP"}))

    def test_independent_auditor_rejects_short_archive(self):
        with self.assertRaises(ValueError):
            audit({"case_receipts": []}, {"case_receipts": []})


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit("Usage: python -m bean.tests.test_scan_two_role_audit NEW.json PRIOR.json")
    new = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    old = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
    print(json.dumps(audit(new, old), sort_keys=True))
