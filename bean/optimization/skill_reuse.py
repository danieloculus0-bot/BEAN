"""Process-independent, integrity-checked retrieval of incubated BEAN skills.

Retrieval does not execute model-generated source. A caller must independently
evaluate it in an isolated execution environment before promotion or use.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from .skill_incubator import retrieve_verified_skill


def recover(*, database: Path, name: str, objective: str) -> dict:
    source = retrieve_verified_skill(database, name=name, objective=objective)
    return {
        "schema": "bean.verified_skill_recovery.v1",
        "name": name,
        "objective": objective,
        "source": source,
        "source_sha256": hashlib.sha256(source.encode("utf-8")).hexdigest(),
        "executed": False,
        "independent_transfer_verified": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Recover BEAN skill source from SQLite in a new process")
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--name", required=True)
    parser.add_argument("--objective", required=True)
    args = parser.parse_args()
    print(json.dumps(recover(database=args.database, name=args.name, objective=args.objective),
                     sort_keys=True))


if __name__ == "__main__":
    main()
