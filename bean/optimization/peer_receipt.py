"""Emit a reproducible, pinned cross-branch test receipt from GitHub Actions.

This document says CI reported a result. Consumers verify the actual GitHub
run and commit permissions separately. It never approves code promotion.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from .peer_dialogue import PeerDialogue


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--selector-file", type=Path, required=True)
    parser.add_argument("--selector-sha", required=True)
    parser.add_argument("--validator-sha", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    candidate_digest = hashlib.sha256(args.selector_file.read_bytes()).hexdigest()
    run_url = "https://github.com/danieloculus0-bot/BEAN/actions/runs/" + args.run_id
    dialogue = PeerDialogue().next(
        role="selector", kind="proposal",
        branch="feat/agentic-improvement-selection-20261010",
        commit_sha=args.selector_sha,
        subject="Evaluate selected source without accepting its own test claims",
        evidence_refs=("bean/optimization/selection.py:1",),
        candidate_sha256=candidate_digest,
    )
    dialogue = dialogue.next(
        role="validator", kind="challenge",
        branch="experiment/bean-peer-development-lab017-20261010",
        commit_sha=args.validator_sha,
        subject="Independent adversarial and no-execution tests for selection",
        evidence_refs=("bean/tests/test_peer_selector_challenge_lab017.py:1",),
        candidate_sha256=candidate_digest,
    )
    dialogue = dialogue.next(
        role="validator", kind="result",
        branch="experiment/bean-peer-development-lab017-20261010",
        commit_sha=args.validator_sha,
        subject="Peer CI independently reported the selector contract passing",
        evidence_refs=("github:actions:" + args.run_id,),
        candidate_sha256=candidate_digest,
        test_state="reported_pass", test_run_url=run_url,
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    dialogue.save(args.out)
    print(json.dumps({"schema": "bean.peer-development.receipt.v1",
                      "peer_commit": args.selector_sha,
                      "peer_file_sha256": candidate_digest,
                      "peer_test_run": run_url,
                      "ledger_sha256": dialogue.export()["sha256"],
                      "status": "reported_pass_not_automatically_approved"},
                     indent=2))


if __name__ == "__main__":
    main()
