"""Merge CI receipts into a source-controlled immutable JSONL research scoreboard.

Existing entries are never edited. Known run keys must have byte-equivalent
science fields; new entries are chained to the latest versioned commit.
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path
from .ledger import canonical, digest, verify


def signature(row):
    return {k: v for k, v in row.items()
            if k not in {"previous_sha256", "entry_sha256", "artifact_entry_sha256"}}


def merge(source, destination):
    incoming = verify(source)
    if not incoming:
        raise ValueError("no benchmark receipts to preserve")
    dest = Path(destination)
    dest.parent.mkdir(parents=True, exist_ok=True)
    stored = verify(dest)
    indexed = {record["run_key"]: record for record in stored}
    merged = list(stored)
    appended = 0
    for row in incoming:
        old = indexed.get(row["run_key"])
        if old is not None:
            if signature(old) != signature(row):
                raise ValueError(f"conflicting historical run: {row['run_key']}")
            continue
        new_row = dict(row)
        previous = merged[-1]["entry_sha256"] if merged else "0" * 64
        if new_row["previous_sha256"] != previous:
            # Rechain this validated CI receipt without erasing its source hash.
            new_row["artifact_entry_sha256"] = new_row["entry_sha256"]
            new_row["previous_sha256"] = previous
            new_row["entry_sha256"] = digest(
                {k: v for k, v in new_row.items() if k != "entry_sha256"})
        merged.append(new_row)
        indexed[row["run_key"]] = new_row
        appended += 1
    if appended:
        payload = "".join(canonical(r).decode("utf-8") + "\n" for r in merged)
        temp = dest.with_suffix(dest.suffix + ".tmp")
        temp.write_text(payload, encoding="utf-8", newline="\n")
        os.replace(temp, dest)
    if verify(dest) != merged:
        raise ValueError("ledger verification after publication failed")
    return appended


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("ci_ledger", type=Path)
    parser.add_argument("repository_ledger", type=Path)
    args = parser.parse_args()
    added = merge(args.ci_ledger, args.repository_ledger)
    print(f"persistent scoreboard: appended={added} total={len(verify(args.repository_ledger))}")


if __name__ == "__main__":
    main()
