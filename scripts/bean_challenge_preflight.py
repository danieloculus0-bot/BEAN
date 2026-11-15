#!/usr/bin/env python3
"""BEAN-native preflight. Exit 2 means an evidence-linked objection blocks action.

Example request JSON:
{"proposal":{"action":"merge","target":"owner/repo#123","revision":"<exact head SHA>",
"summary":"Short intent"},"objections":[{"kind":"conflict","reason":"Known regression",
"evidence_refs":["epistemic_audit:<existing BEAN audit ID>"]}]}
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from bean.cognition.challenge_gate import ChallengeGate, Proposal
from bean.memory.store import init_store


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Evidence-linked BEAN challenge preflight")
    parser.add_argument("--db", type=Path, required=True, help="Existing BEAN Core SQLite path")
    commands = parser.add_subparsers(dest="command", required=True)
    review = commands.add_parser("review", help="Record/recheck a proposed action")
    review.add_argument("--request", type=Path, required=True,
                        help="JSON with proposal and objections")
    override = commands.add_parser("override", help="Record explicit override of blocked review")
    override.add_argument("--challenge-id", required=True)
    override.add_argument("--actor", required=True)
    override.add_argument("--justification", required=True)
    status = commands.add_parser("status", help="Read a recorded review")
    status.add_argument("--challenge-id", required=True)
    args = parser.parse_args(argv)

    try:
        if not args.db.is_file():
            raise ValueError("Existing Core SQLite file required; refusing an accidental new brain")
        init_store(str(args.db))
        gate = ChallengeGate()
        if args.command == "review":
            payload = json.loads(args.request.read_text(encoding="utf-8"))
            if not isinstance(payload, dict) or set(payload) != {"proposal", "objections"}:
                raise ValueError("Review JSON requires proposal and objections")
            if not isinstance(payload["proposal"], dict) or set(payload["proposal"]) != {
                "action", "target", "revision", "summary"
            }:
                raise ValueError("Proposal requires action, target, revision and summary")
            result = gate.review(Proposal(**payload["proposal"]), payload["objections"])
        elif args.command == "override":
            result = gate.override(args.challenge_id, actor=args.actor,
                                   justification=args.justification)
        else:
            result = gate.status(args.challenge_id)
        print(json.dumps(result, indent=2, sort_keys=True))
        return 2 if result["decision"] == "BLOCK" else 0
    except (ValueError, OSError, json.JSONDecodeError, TypeError) as exc:
        print(f"BEAN preflight invalid: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
