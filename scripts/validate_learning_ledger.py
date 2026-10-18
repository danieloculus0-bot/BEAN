#!/usr/bin/env python3
"""Validate BEAN's source-linked learning ledger without claiming agent learning.

Usage:
    python scripts/validate_learning_ledger.py
    python scripts/validate_learning_ledger.py research/learning_ledger.jsonl
"""
from __future__ import annotations

import argparse
import datetime
import json
from pathlib import Path

REQUIRED_TEXT = (
    "lesson_id", "recorded_date", "title", "status", "domain",
    "observation", "evidence_type", "how_learned", "what_changed",
    "actual_learning_mechanism", "validated_outcome", "transfer_test",
    "limitations", "promotion_state",
)
CAUSAL_PROOF_FIELDS = (
    "baseline_run_ref", "treatment_run_ref", "heldout_eval_ref",
    "mechanism_artifact_ref",
)
VALID_STATUSES = frozenset({
    "supported_code_design", "observed_synthetic", "inconclusive",
    "hypothesis_only", "proposal_from_peer_review", "refuted",
    "independently_replicated",
})


def validate_entries(lines: list[str]) -> list[dict]:
    """Check structure, provenance, IDs, and evidence gates; not source truth."""
    records: list[dict] = []
    ids: set[str] = set()
    for number, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"line {number}: invalid JSON: {exc.msg}") from exc
        if not isinstance(row, dict):
            raise ValueError(f"line {number}: expected JSON object")
        for field in REQUIRED_TEXT:
            if not isinstance(row.get(field), str) or not row[field].strip():
                raise ValueError(f"line {number}: missing/non-text {field}")
        if row["status"] not in VALID_STATUSES:
            raise ValueError(f"line {number}: unsupported status {row['status']!r}")
        if row["lesson_id"] in ids:
            raise ValueError(f"line {number}: duplicated lesson_id {row['lesson_id']}")
        ids.add(row["lesson_id"])
        try:
            datetime.date.fromisoformat(row["recorded_date"])
        except ValueError as exc:
            raise ValueError(f"line {number}: invalid date") from exc
        urls = row.get("evidence_urls")
        if not isinstance(urls, list) or not urls or any(
            not isinstance(url, str) or not url.startswith("https://")
            for url in urls
        ):
            raise ValueError(f"line {number}: evidence_urls must be https URL list")
        causal = row.get("causal_learning_demonstrated")
        if not isinstance(causal, bool):
            raise ValueError(f"line {number}: causal_learning_demonstrated must be boolean")
        if causal:
            missing = [
                key for key in CAUSAL_PROOF_FIELDS
                if not isinstance(row.get(key), str) or
                not row[key].startswith("https://")
            ]
            if missing:
                raise ValueError(
                    f"line {number}: learning claim lacks causal proof refs: {missing}"
                )
            if row["status"] != "independently_replicated":
                raise ValueError(
                    f"line {number}: causal learning requires independently_replicated status"
                )
        records.append(row)
    if not records:
        raise ValueError("empty learning ledger")
    return records


def validate_file(path: Path) -> list[dict]:
    return validate_entries(path.read_text(encoding="utf-8").splitlines())


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    default = Path(__file__).resolve().parents[1] / "research" / "learning_ledger.jsonl"
    parser.add_argument("ledger", nargs="?", type=Path, default=default)
    args = parser.parse_args()
    try:
        rows = validate_file(args.ledger)
    except (ValueError, OSError) as exc:
        parser.exit(1, f"INVALID learning ledger: {exc}\n")
    claimed = sum(row["causal_learning_demonstrated"] for row in rows)
    print(f"VALID lessons={len(rows)} causal_learning_claims={claimed}")
    print("This verifies structure and linked-receipt presence, NOT evidence authenticity.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
