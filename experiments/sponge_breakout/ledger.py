"""Small, verifiable, append-only receipt ledger for experimental Breakout runs.

The JSONL ledger is source-controlled separately from bulky SQLite journals.
Hashes detect accidental alteration; Git history establishes repository revisions,
but SHA-256 does NOT authenticate experiment claims or prove independent learning.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path


FORMAT = "bean.sponge.breakout.ledger.v1"


def canonical(row):
    return json.dumps(row, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def digest(row):
    return hashlib.sha256(canonical(row)).hexdigest()


def verify(path):
    path = Path(path)
    previous = "0" * 64
    records = []
    seen = set()
    if not path.exists():
        return records
    for idx, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            raise ValueError(f"blank ledger line {idx}")
        row = json.loads(line)
        if not isinstance(row, dict) or row.get("schema") != FORMAT:
            raise ValueError(f"invalid ledger schema at line {idx}")
        stored = row.get("entry_sha256")
        content = {k: v for k, v in row.items() if k != "entry_sha256"}
        if row.get("previous_sha256") != previous or stored != digest(content):
            raise ValueError(f"ledger chain broken at line {idx}")
        key = row.get("run_key")
        if not isinstance(key, str) or not key or key in seen:
            raise ValueError(f"duplicate or missing run key at line {idx}")
        if not isinstance(row.get("journal_tip"), str) or len(row["journal_tip"]) != 64:
            raise ValueError(f"missing journal digest at line {idx}")
        seen.add(key)
        records.append(row)
        previous = stored
    return records


def append_result(path, result):
    """Append one deterministic run receipt; never edit an existing row."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    prior = verify(path)
    key = result["run_key"]
    if any(record["run_key"] == key for record in prior):
        raise ValueError(f"run already recorded: {key}")
    checkpoints = [
        {"episode": c["episode"],
         "bricks": c["validation"]["bricks"],
         "policy_sha256": c["receipt"]["memory_sha256"]}
        for c in result["checkpoints"]
    ]
    row = {
        "schema": FORMAT,
        "run_key": key,
        "previous_sha256": prior[-1]["entry_sha256"] if prior else "0" * 64,
        "protocol": result["protocol"],
        "selected_episode": result["selected_episode"],
        "validation_checkpoints": checkpoints,
        "holdout": result["holdout"],
        "holdout_delta": result["holdout_delta"],
        "journal_tip": result["journal_tip"],
        "source_digests": result["source_digests"],
        "evidence_class": "synthetic_game_training_separate_holdout",
        "interpretation": "policy learned in simplified game; no proof of cognitive transfer",
    }
    row["entry_sha256"] = digest(row)
    # Append and fsync; verification catches interrupted or corrupted writes.
    with path.open("a", encoding="utf-8", newline="\n") as stream:
        stream.write(canonical(row).decode("utf-8") + "\n")
        stream.flush()
        os.fsync(stream.fileno())
    verify(path)
    return row


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("path", type=Path)
    parser.add_argument("--expect-runs", type=int, default=None)
    args = parser.parse_args()
    rows = verify(args.path)
    if args.expect_runs is not None and len(rows) != args.expect_runs:
        raise SystemExit(f"expected {args.expect_runs} runs, found {len(rows)}")
    print(json.dumps({"verified_rows": len(rows),
                      "tip_sha256": rows[-1]["entry_sha256"] if rows else None,
                      "runs": [{"key": r["run_key"], "selected_bricks": r["holdout"]["selected"]["bricks"],
                                "cold_bricks": r["holdout"]["cold"]["bricks"],
                                "delta": r["holdout_delta"]} for r in rows]}, sort_keys=True))


if __name__ == "__main__":
    main()
