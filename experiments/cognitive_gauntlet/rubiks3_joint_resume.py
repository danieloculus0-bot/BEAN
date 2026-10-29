"""Resume BEAN's frozen joint-cube policy from verified original checkpoints.

This evaluator never calls a reference solver or changes learned weights.
Compute slices are resumable; there is no total solution-move ceiling.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory

from bean.optimization.sponge_td import SpongeTD
from .rubiks3 import MOVES, SOLVED, apply
from .rubiks3_joint_rescue import policy_solve_joint_rescue
from .rubiks3_joint_rescue_verify import verify_receipt
from .rubiks3_pair_goals import train_pairs
from .rubiks3_pieces import observed_edges
from .rubiks3_sponge import _digest, collect_states
from .rubiks3_symmetry import learn_symmetric

SCHEMA = "bean.rubiks3.joint-resume.v1"


def replay(state, moves):
    if not isinstance(moves, list) or any(m not in MOVES for m in moves):
        raise ValueError("illegal route")
    return apply(state, moves) == SOLVED


def resume_receipt(source, *, slices=2, work_budget=32, output=None):
    if type(slices) is not int or slices < 1 or type(work_budget) is not int or work_budget < 1:
        raise ValueError("positive integer slices and work_budget required")
    source = Path(source)
    verify_receipt(source)
    old = json.loads(source.read_text(encoding="utf-8"))
    states, _ = collect_states(old["train_seeds"], old["train_lengths"])
    with TemporaryDirectory(prefix="bean-resume-") as tmp:
        full = SpongeTD(Path(tmp) / "full.db", actions=MOVES,
                        alpha=1, gamma=.9, epsilon=0, seed=19)
        joint = SpongeTD(Path(tmp) / "joint.db", actions=MOVES,
                         alpha=1, gamma=.9, epsilon=0, seed=19)
        try:
            learn_symmetric(full, states, epochs=old["full_training"]["epochs"])
            train_pairs(joint, observed_edges(states),
                        epochs=old["joint_training"]["epochs"])
            frozen = (_digest(full.q), _digest(joint.q))
            if frozen != (old["initial_q_sha256"], old["joint_q_sha256"]):
                raise ValueError("frozen Q digest mismatch")
            if (full.steps != old["initial_td_updates"] or
                    full.steps + joint.steps != old["candidate_total_td_updates"]):
                raise ValueError("TD update mismatch")
            cases = []
            for row in old["cases"]:
                route = list(row["candidate_moves"])
                solved, paused = row["candidate_solved"], row["candidate_paused"]
                failure, checkpoint = row["candidate_failure"], row["candidate_checkpoint"]
                if replay(row["state"], route) != solved:
                    raise ValueError("original replay mismatch")
                attempts = []
                for i in range(slices if paused else 0):
                    previous = list(route)
                    route, info = policy_solve_joint_rescue(
                        full, joint, row["state"], checkpoint=checkpoint,
                        work_budget=work_budget, rescue_backup=old["rescue_backup"])
                    solved = replay(row["state"], route)
                    if solved != info["solved"] or route[:len(previous)] != previous:
                        raise ValueError("continuation replay/prefix mismatch")
                    paused, failure, checkpoint = (
                        info["paused"], info["failure"], info["checkpoint"])
                    attempts.append({
                        "slice": i + 1, "moves": list(route),
                        "move_count": len(route), "solved": solved,
                        "paused": paused, "failure": failure,
                        "checkpoint": checkpoint, "full_steps": info["full_steps"],
                        "joint_steps": info["joint_steps"]})
                    if not paused:
                        break
                cases.append({
                    "seed": row["seed"], "scramble_length": row["scramble_length"],
                    "scramble_evaluator_only": row["scramble_evaluator_only"],
                    "state": row["state"], "canonical_state": row["canonical_state"],
                    "original_moves": row["candidate_moves"],
                    "original_solved": row["candidate_solved"],
                    "original_paused": row["candidate_paused"],
                    "original_failure": row["candidate_failure"],
                    "initial_solved": row["initial_solved"],
                    "rescue_control_solved": row["rescue_control_solved"],
                    "attempts": attempts, "resumed_moves": route,
                    "resumed_move_count": len(route), "resumed_solved": solved,
                    "resumed_paused": paused, "resumed_failure": failure,
                    "resumed_checkpoint": checkpoint,
                    "new_solution": solved and not row["candidate_solved"],
                    "optimality_proven": False})
            if frozen != (_digest(full.q), _digest(joint.q)):
                raise AssertionError("evaluation mutated frozen Q")
        finally:
            full.close()
            joint.close()
    result = {
        "schema": SCHEMA, "source_receipt_sha256": old["sha256"],
        "source_revision": old["source_revision"],
        "continuation_revision": os.environ.get("GITHUB_SHA", "local_unverified"),
        "module_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "initial_q_sha256": frozen[0], "joint_q_sha256": frozen[1],
        "rescue_backup": old["rescue_backup"],
        "train_seeds": old["train_seeds"], "test_seeds": old["test_seeds"],
        "test_lengths": old["test_lengths"],
        "additional_slices": slices, "work_budget_per_slice": work_budget,
        "eligible_cases": len(cases), "excluded_count": len(old["excluded"]),
        "excluded": old["excluded"], "cases": cases,
        "solved_before": sum(x["original_solved"] for x in cases),
        "solved_after": sum(x["resumed_solved"] for x in cases),
        "paused_before": sum(x["original_paused"] for x in cases),
        "paused_after": sum(x["resumed_paused"] for x in cases),
        "new_solutions": sum(x["new_solution"] for x in cases),
        "twenty_turn_cases": sum(x["scramble_length"] == 20 for x in cases),
        "twenty_turn_solved_before": sum(x["original_solved"] for x in cases
                                         if x["scramble_length"] == 20),
        "twenty_turn_solved_after": sum(x["resumed_solved"] for x in cases
                                        if x["scramble_length"] == 20),
        "reference_solver_used": False, "learned_weights_changed": False,
        "caveat": "Frozen policy continuation, not new learning or shortest-solution proof."}
    result["sha256"] = _digest(result)
    if output is not None:
        path = Path(output)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        verify_resume(source, path)
    return result


def verify_resume(source, continuation):
    """Independent route replay, source binding, every pause and aggregate."""
    verify_receipt(source)
    old = json.loads(Path(source).read_text(encoding="utf-8"))
    result = json.loads(Path(continuation).read_text(encoding="utf-8"))
    if result.get("schema") != SCHEMA or result.get("sha256") != _digest(
            {k: v for k, v in result.items() if k != "sha256"}):
        raise ValueError("invalid continuation schema/digest")
    bindings = {
        "source_receipt_sha256": "sha256", "source_revision": "source_revision",
        "initial_q_sha256": "initial_q_sha256",
        "joint_q_sha256": "joint_q_sha256", "rescue_backup": "rescue_backup",
        "excluded": "excluded"}
    if any(result[k] != old[v] for k, v in bindings.items()):
        raise ValueError("source receipt binding mismatch")
    if (len(result["cases"]) != len(old["cases"]) or
            result["eligible_cases"] != len(old["cases"]) or
            result["excluded_count"] != len(old["excluded"])):
        raise ValueError("case coverage mismatch")
    fields = {
        "seed": "seed", "scramble_length": "scramble_length",
        "scramble_evaluator_only": "scramble_evaluator_only",
        "state": "state", "canonical_state": "canonical_state",
        "original_moves": "candidate_moves",
        "original_solved": "candidate_solved",
        "original_paused": "candidate_paused",
        "original_failure": "candidate_failure",
        "initial_solved": "initial_solved",
        "rescue_control_solved": "rescue_control_solved"}
    for previous_row, row in zip(old["cases"], result["cases"]):
        if any(row[k] != previous_row[v] for k, v in fields.items()):
            raise ValueError("original case provenance mismatch")
        route = previous_row["candidate_moves"]
        attempts = row["attempts"]
        if bool(attempts) != previous_row["candidate_paused"] or len(attempts) > result["additional_slices"]:
            raise ValueError("invalid continuation selection")
        for i, attempt in enumerate(attempts):
            moves = attempt["moves"]
            if (attempt["slice"] != i + 1 or moves[:len(route)] != route
                    or len(moves) > len(route) + result["work_budget_per_slice"]
                    or len(moves) != attempt["move_count"]
                    or attempt["full_steps"] + attempt["joint_steps"] != len(moves)
                    or replay(row["state"], moves) != attempt["solved"]):
                raise ValueError("invalid attempt route/accounting")
            cp = attempt["checkpoint"]
            if attempt["paused"]:
                if (attempt["solved"] or attempt["failure"] != "paused_compute_budget"
                        or not isinstance(cp, dict) or cp.get("route") != moves
                        or cp.get("start") != row["state"]
                        or cp.get("full_q_sha256") != result["initial_q_sha256"]
                        or cp.get("joint_q_sha256") != result["joint_q_sha256"]
                        or cp.get("rescue_backup") != result["rescue_backup"]
                        or cp.get("full_steps") != attempt["full_steps"]
                        or cp.get("joint_steps") != attempt["joint_steps"]):
                    raise ValueError("invalid checkpoint")
            elif cp is not None or i + 1 != len(attempts):
                raise ValueError("continued terminal attempt")
            route = moves
        last = attempts[-1] if attempts else None
        if (row["resumed_moves"] != route or row["resumed_move_count"] != len(route)
                or row["resumed_solved"] != (last["solved"] if last else previous_row["candidate_solved"])
                or row["resumed_paused"] != (last["paused"] if last else previous_row["candidate_paused"])
                or row["resumed_failure"] != (last["failure"] if last else previous_row["candidate_failure"])
                or row["resumed_checkpoint"] != (last["checkpoint"] if last else previous_row["candidate_checkpoint"])
                or row["new_solution"] != (row["resumed_solved"] and not previous_row["candidate_solved"])
                or replay(row["state"], route) != row["resumed_solved"]):
            raise ValueError("invalid final continuation claim")
    counts = {
        "solved_before": sum(x["original_solved"] for x in result["cases"]),
        "solved_after": sum(x["resumed_solved"] for x in result["cases"]),
        "paused_before": sum(x["original_paused"] for x in result["cases"]),
        "paused_after": sum(x["resumed_paused"] for x in result["cases"]),
        "new_solutions": sum(x["new_solution"] for x in result["cases"]),
        "twenty_turn_cases": sum(x["scramble_length"] == 20 for x in result["cases"]),
        "twenty_turn_solved_before": sum(x["original_solved"] for x in result["cases"]
                                         if x["scramble_length"] == 20),
        "twenty_turn_solved_after": sum(x["resumed_solved"] for x in result["cases"]
                                        if x["scramble_length"] == 20)}
    if any(result[k] != v for k, v in counts.items()):
        raise ValueError("continuation aggregate mismatch")
    return {"verified": True, "source_receipt_sha256": old["sha256"],
            "continuation_sha256": result["sha256"], **counts}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--source", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--slices", type=int, default=2)
    p.add_argument("--work-budget", type=int, default=32)
    p.add_argument("--verify", action="store_true")
    args = p.parse_args()
    data = (verify_resume(args.source, args.output) if args.verify else
            resume_receipt(args.source, slices=args.slices,
                           work_budget=args.work_budget, output=args.output))
    print(json.dumps({k: v for k, v in data.items() if k in
                      ("verified", "solved_before", "solved_after", "paused_before",
                       "paused_after", "new_solutions", "twenty_turn_cases",
                       "twenty_turn_solved_after")}, sort_keys=True))


if __name__ == "__main__":
    main()
