"""Drive independent workflow validation through the running native Core.

This is a supervisor-side client, not a second planner. The expected outcomes
must come from an independent evaluator. No model is allowed to grade itself.
Candidate replay requires the cognition_workflow_validate inbox handler.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import sqlite3
import time

from bean.runtime.inbox import CommandInbox
from bean.runtime.native_orchestration import read_plan_result
from bean.cognition.goal_state import plan_proposal_id


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False)


def replay_id(case):
    # The oracle is deliberately excluded: changing expected results cannot
    # turn the same execution into an independent new validation trial.
    identity = [case["family"], case["graph_sha"], case["inputs"]]
    return "validate:" + hashlib.sha256(canonical(identity).encode()).hexdigest()


def validate_case(case):
    if not isinstance(case, dict) or set(case) != {
        "family", "graph_sha", "inputs", "checks", "evidence_ref"
    }:
        raise ValueError("expected family, graph_sha, inputs, checks, evidence_ref")
    if not isinstance(case["family"], str) or not 1 <= len(case["family"]) <= 100:
        raise ValueError("invalid family")
    sha = case["graph_sha"]
    if not isinstance(sha, str) or len(sha) != 64 or any(c not in "0123456789abcdef" for c in sha):
        raise ValueError("exact lowercase workflow SHA-256 required")
    if not isinstance(case["inputs"], dict):
        raise ValueError("inputs must be an object")
    if not isinstance(case["evidence_ref"], str) or not 1 <= len(case["evidence_ref"]) <= 500:
        raise ValueError("independent evidence reference required")
    checks = case["checks"]
    if not isinstance(checks, list) or not 1 <= len(checks) <= 32:
        raise ValueError("independent checks required")
    for check in checks:
        if (not isinstance(check, dict) or set(check) != {"step", "path", "expected"}
                or type(check["step"]) is not int or not 0 <= check["step"] < 8
                or not isinstance(check["path"], list) or len(check["path"]) > 16
                or any(type(k) not in (str, int) for k in check["path"])):
            raise ValueError("invalid outcome check")
    canonical(case)
    return case


def connect(database):
    conn = sqlite3.connect(Path(database).resolve().as_uri() + "?mode=ro", uri=True, timeout=2)
    conn.row_factory = sqlite3.Row
    return conn


def read_trial(database, plan_id):
    with connect(database) as conn:
        try:
            row = conn.execute(
                "SELECT family,graph_sha,input_sha,evidence_json,passed "
                "FROM bean_verified_workflow_trials WHERE plan_id=?", (plan_id,)
            ).fetchone()
        except sqlite3.OperationalError as exc:
            if "no such table" not in str(exc):
                raise
            return None
        if row is None:
            return None
        result = dict(row)
        result["evidence"] = json.loads(result.pop("evidence_json"))
        return result


def verify_identity(database, plan_id, case):
    with connect(database) as conn:
        row = conn.execute(
            "SELECT action_detail FROM cognition_goal_proposals WHERE proposal_id=?",
            (plan_proposal_id(plan_id, 0),)
        ).fetchone()
    if not row:
        raise ValueError("no durable proposal")
    detail = json.loads(row["action_detail"])
    if (detail.get("workflow_sha") != case["graph_sha"]
            or detail.get("inputs") != case["inputs"]
            or detail.get("planner_provider") != "candidate_validation"):
        raise ValueError("plan is not the requested candidate replay")


def assert_same_evidence(trial, case):
    checks = [{k: item[k] for k in ("step", "path", "expected")}
              for item in trial["evidence"]["checks"]]
    if (trial["family"] != case["family"] or trial["graph_sha"] != case["graph_sha"]
            or trial["evidence"]["source"] != case["evidence_ref"]
            or canonical(checks) != canonical(case["checks"])):
        raise ValueError("existing immutable trial has different evaluator evidence")


def await_observation(read, request, deadline, interval, *, terminal=lambda value: value is not None):
    """Check the real database before interpreting inbox movement."""
    while True:
        value = read()
        if terminal(value):
            return value
        if request is not None:
            if (request.parent / "failed" / request.name).is_file():
                raise RuntimeError("Core rejected inbox command")
            if (request.parent / "processed" / request.name).is_file() and value is None:
                # Processing completed but no durable result: abstention, not success.
                value = read()
                if value is None:
                    raise RuntimeError("Core processed command without a durable result")
                if terminal(value):
                    return value
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError("execution pending; reconnect using the same case")
        time.sleep(min(interval, remaining))


def run_case(database, inbox_path, case, *, timeout=180, interval=0.25):
    case = validate_case(case)
    if not math.isfinite(timeout) or timeout <= 0 or not math.isfinite(interval) or interval <= 0:
        raise ValueError("positive finite timeout and interval required")
    pid = replay_id(case)
    deadline = time.monotonic() + timeout
    existing = read_trial(database, pid)
    if existing is not None:
        verify_identity(database, pid, case)
        assert_same_evidence(existing, case)
        return {"plan_id": pid, "trial": existing, "reconnected": True}
    inbox = CommandInbox(inbox_path)

    def snapshot():
        result = read_plan_result(database, pid)
        return result if result["steps"] else None

    def drop_or_reconnect(command, args):
        # Reuse any still-pending identical request after a client restart.
        for path in sorted(inbox.inbox_dir.glob("*.json")):
            try:
                raw = json.loads(path.read_text(encoding="utf-8"))
            except (FileNotFoundError, ValueError):
                continue
            if raw.get("command") == command and raw.get("args") == args:
                return path
        return inbox.drop(command, args, sender="independent_workflow_evaluator")

    plan = snapshot()
    request = None
    if plan is None:
        request = drop_or_reconnect("cognition_workflow_validate", {
            "family": case["family"], "graph_sha": case["graph_sha"],
            "inputs": case["inputs"], "plan_id": pid})
    plan = await_observation(snapshot, request, deadline, interval,
                             terminal=lambda x: x is not None and x["status"] in
                             {"completed", "failed", "needs_review", "needs_evidence"})
    verify_identity(database, pid, case)
    # Do not let a recovered fresh plan earn retained-workflow credit.
    if plan["status"] not in {"completed", "failed"}:
        return {"plan_id": pid, "status": plan["status"], "trial": None}
    if {c["step"] for c in case["checks"]} != set(range(len(plan["steps"]))):
        raise ValueError("independent checks must cover each actual step")
    request = drop_or_reconnect("cognition_workflow_feedback", {
        "family": case["family"], "plan_id": pid,
        "checks": case["checks"], "evidence_ref": case["evidence_ref"]})
    trial = await_observation(lambda: read_trial(database, pid), request, deadline, interval)
    assert_same_evidence(trial, case)
    return {"plan_id": pid, "trial": trial, "steps": plan["steps"], "reconnected": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, required=True)
    parser.add_argument("--inbox", type=Path, required=True)
    parser.add_argument("--case", type=Path, required=True)
    parser.add_argument("--timeout", type=float, default=180)
    args = parser.parse_args()
    result = run_case(args.db, args.inbox, json.loads(args.case.read_text(encoding="utf-8")),
                      timeout=args.timeout)
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if (result.get("trial") or {}).get("passed") == 1 else 1)


if __name__ == "__main__":
    main()
