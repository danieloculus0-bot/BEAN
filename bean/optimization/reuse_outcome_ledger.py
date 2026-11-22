"""Append-only SHA-linked receipts for BEAN's retained-skill reuse outcomes.

This records observed evaluations, including failures. A receipt is not proof
of learning or cross-domain transfer; controls must be evaluated separately.
"""
from __future__ import annotations

from contextlib import closing
import hashlib
import json
from pathlib import Path
import sqlite3


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def append_reuse_outcome(database, *, skill, source_sha256, tests_sha256, passed,
                         novel_test_set, provider_invoked=False, experiment_id=None, condition="candidate"):
    """Persist a reproducible result, preserving failures and chained history."""
    if not isinstance(skill, str) or not skill:
        raise ValueError("invalid skill")
    for value in (source_sha256, tests_sha256):
        if not isinstance(value, str) or len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
            raise ValueError("invalid SHA-256")
    if any(type(v) is not bool for v in (passed, novel_test_set, provider_invoked)):
        raise ValueError("boolean outcomes required")
    if experiment_id is not None and (not isinstance(experiment_id, str) or not experiment_id.strip()):
        raise ValueError("invalid experiment identity")
    if condition not in ("candidate", "frozen", "no_memory", "grammar_matched", "strong_control"):
        raise ValueError("invalid evaluation condition")
    path = Path(database)
    if path.is_symlink():
        raise ValueError("linked outcome ledger")
    path.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(path, timeout=15)) as db, db:
        db.execute("""CREATE TABLE IF NOT EXISTS reuse_outcomes (
            sequence INTEGER PRIMARY KEY AUTOINCREMENT,
            payload TEXT NOT NULL, prior_sha256 TEXT NOT NULL,
            receipt_sha256 TEXT NOT NULL)""")
        db.execute("BEGIN IMMEDIATE") if not db.in_transaction else None
        last = db.execute("SELECT receipt_sha256 FROM reuse_outcomes ORDER BY sequence DESC LIMIT 1").fetchone()
        prior = last[0] if last else "0" * 64
        payload = {"skill": skill, "source_sha256": source_sha256,
                   "tests_sha256": tests_sha256, "passed": passed,
                   "novel_test_set": novel_test_set, "provider_invoked": provider_invoked,
                   "experiment_id": experiment_id, "condition": condition}
        encoded = _canonical(payload).decode("utf-8")
        digest = hashlib.sha256(prior.encode("ascii") + encoded.encode("utf-8")).hexdigest()
        db.execute("INSERT INTO reuse_outcomes(payload, prior_sha256, receipt_sha256) VALUES(?,?,?)",
                   (encoded, prior, digest))
        sequence = db.execute("SELECT last_insert_rowid()").fetchone()[0]
    return {"sequence": sequence, "receipt_sha256": digest, "prior_sha256": prior}


def verify_reuse_outcomes(database):
    """Verify the full chain; return ordered outcomes without hiding failures."""
    path = Path(database)
    if path.is_symlink():
        raise ValueError("linked outcome ledger")
    with closing(sqlite3.connect(path)) as db:
        rows = db.execute("SELECT sequence,payload,prior_sha256,receipt_sha256 FROM reuse_outcomes ORDER BY sequence").fetchall()
    prior = "0" * 64
    outcomes = []
    for index, (sequence, encoded, stored_prior, digest) in enumerate(rows, 1):
        if sequence != index or stored_prior != prior:
            raise ValueError("reuse outcome chain discontinuity")
        payload = json.loads(encoded)
        if _canonical(payload).decode("utf-8") != encoded:
            raise ValueError("noncanonical reuse outcome")
        if hashlib.sha256(prior.encode("ascii") + encoded.encode("utf-8")).hexdigest() != digest:
            raise ValueError("reuse outcome digest mismatch")
        outcomes.append(payload)
        prior = digest
    return outcomes



EVALUATION_ARMS = ("candidate", "frozen", "no_memory", "grammar_matched", "strong_control")


def summarize_matched_experiment(outcomes, experiment_id):
    """Score only complete, one-to-one, same-holdout control groups.

    This is descriptive paired correctness, not independent proof of learning.
    No budget, model identity or seed is stored in the current receipt schema.
    """
    if not isinstance(experiment_id, str) or not experiment_id.strip():
        raise ValueError("experiment_id required")
    selected = [r for r in outcomes if r.get("experiment_id") == experiment_id]
    groups = {}
    for receipt in selected:
        key = (receipt.get("skill"), receipt.get("tests_sha256"))
        groups.setdefault(key, []).append(receipt)
    valid = []
    excluded = []
    for (skill, test_sha), records in sorted(groups.items()):
        by_arm = {}
        reasons = []
        for record in records:
            arm = record.get("condition")
            if arm not in EVALUATION_ARMS or arm in by_arm:
                reasons.append("duplicate_or_unknown_arm")
            else:
                by_arm[arm] = record
            if record.get("novel_test_set") is not True:
                reasons.append("not_marked_novel")
            if type(record.get("passed")) is not bool:
                reasons.append("invalid_outcome")
        if set(by_arm) != set(EVALUATION_ARMS):
            reasons.append("incomplete_arms")
        if reasons:
            excluded.append({"skill": skill, "tests_sha256": test_sha,
                             "reasons": sorted(set(reasons))})
            continue
        valid.append({"skill": skill, "tests_sha256": test_sha,
                      "results": {arm: by_arm[arm]["passed"] for arm in EVALUATION_ARMS}})
    counts = {arm: sum(int(item["results"][arm]) for item in valid)
              for arm in EVALUATION_ARMS}
    n = len(valid)
    return {"experiment_id": experiment_id, "matched_tasks": n,
            "correct": counts,
            "candidate_minus_controls": {arm: counts["candidate"] - counts[arm]
                                          for arm in EVALUATION_ARMS if arm != "candidate"},
            "excluded": excluded, "equal_budget_verified": False, "source_equivalence_verified": False,
            "independent_learning_verified": False,
            "interpretation": "descriptive_only_no_budget_or_seed_receipts"}

def main(argv=None):
    """Read-only verification in a fresh interpreter; exit nonzero on tampering."""
    import argparse
    parser = argparse.ArgumentParser(description="Verify BEAN retained-skill reuse evidence")
    parser.add_argument("database", help="Existing SQLite outcome ledger")
    parser.add_argument("--expected-count", type=int, default=None,
                        help="Pinned receipt count from an independently retained checkpoint")
    parser.add_argument("--expected-head-sha256", default=None,
                        help="Pinned final receipt digest from an independently retained checkpoint")
    parser.add_argument("--emit-checkpoint", action="store_true",
                        help="Include count and head digest to pin outside the ledger")
    parser.add_argument("--summarize-experiment", default=None,
                        help="Descriptive complete-arm comparison; not proof of learning")
    args = parser.parse_args(argv)
    path = Path(args.database)
    if not path.is_file() or path.is_symlink():
        parser.error("an existing regular ledger file is required")
    try:
        outcomes = verify_reuse_outcomes(path)
    except (sqlite3.Error, ValueError, json.JSONDecodeError) as exc:
        parser.exit(1, f"integrity verification failed: {type(exc).__name__}: {exc}\n")
    # A self-contained hash chain cannot detect deletion of its final rows.
    # An independently retained checkpoint pins both the count and final digest.
    if args.expected_count is not None and (args.expected_count < 0 or len(outcomes) != args.expected_count):
        parser.exit(1, "integrity verification failed: checkpoint count mismatch\n")
    if args.expected_head_sha256 is not None:
        expected = args.expected_head_sha256
        if len(expected) != 64 or any(c not in "0123456789abcdef" for c in expected):
            parser.error("expected head must be a lowercase SHA-256 digest")
        with closing(sqlite3.connect(path)) as db:
            row = db.execute("SELECT receipt_sha256 FROM reuse_outcomes ORDER BY sequence DESC LIMIT 1").fetchone()
        actual_head = row[0] if row else "0" * 64
        if actual_head != expected:
            parser.exit(1, "integrity verification failed: checkpoint head mismatch\n")
    result = {"verified": True, "count": len(outcomes),
              "failures": sum(not item["passed"] for item in outcomes)}
    if args.emit_checkpoint:
        # Export is informational: the caller must pin it independently.
        with closing(sqlite3.connect(path)) as db:
            row = db.execute("SELECT receipt_sha256 FROM reuse_outcomes ORDER BY sequence DESC LIMIT 1").fetchone()
        result["head_sha256"] = row[0] if row else "0" * 64
    if args.summarize_experiment is not None:
        result["matched_summary"] = summarize_matched_experiment(outcomes, args.summarize_experiment)
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
