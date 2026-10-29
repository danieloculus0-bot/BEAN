"""BEAN-native discounted hotter/colder rewards for learned corner-edge goals.

Experimental matched comparison against the UNCHANGED terminal-only joint
SpongeTD learner. Both policies use identical legal self-play transitions,
update counts, full-state fallback, inference budgets and held-out cubes.
No reference solver, inverse scramble or generic cube search is used.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import random
from tempfile import TemporaryDirectory

from bean.optimization.sponge_td import SpongeTD
from .rubiks3 import MOVES, SOLVED, apply, scramble
from .rubiks3_joint_rescue import policy_solve_joint_rescue
from .rubiks3_legality import validate_legal_cube
from .rubiks3_pair_goals import pair_features, joint_reward, train_pairs
from .rubiks3_pieces import piece_features, observed_edges
from .rubiks3_sponge import _digest, collect_states
from .rubiks3_symmetry import canonical, learn_symmetric
from .rubiks3_value_rollout import policy_solve_value_rollout

SCHEMA = "bean.rubiks3.joint-temperature.v1"


def pair_distances(state):
    """Identity, configuration, cubie distances, and solved flags for 96 pairs."""
    pieces = piece_features(state)
    corners = [p for p in pieces if p[0][0] == "corner"]
    edges = [p for p in pieces if p[0][0] == "edge"]
    return tuple(((ci, ei), (cc, ec), (cd, ed), (cd == 0, ed == 0))
                 for ci, cc, cd in corners for ei, ec, ed in edges)


def joint_temperature_reward(before_dist, after_dist, before_solved,
                             after_solved, gamma, strength=0.5):
    """Discounted change in closeness, plus the original newly-solved reward.

    A solved pair is a local terminal goal. The potential of the terminal
    successor is zero; no repeated +1 is paid for merely preserving it.
    This is a testable local reward heuristic, NOT a claim of global
    policy invariance or an exact whole-cube distance oracle.
    """
    if not 0 <= gamma <= 1 or not 0 <= strength <= 1:
        raise ValueError("invalid discount or shaping strength")
    if (len(before_dist) != 2 or len(after_dist) != 2
            or any(type(d) is not int or d < 0
                   for d in (*before_dist, *after_dist))):
        raise ValueError("invalid cubie distances")
    # Preserving an already solved pair is neutral, not a fresh success or
    # a penalty. Otherwise the controller is taught to break good subgoals.
    if before_solved == after_solved == (True, True):
        return 0.0
    before = 1.0 / (1 + sum(before_dist))
    after = (0.0 if after_solved == (True, True)
             else 1.0 / (1 + sum(after_dist)))
    return (joint_reward(before_solved, after_solved)
            + strength * (gamma * after - before))


def train_joint_temperature(learner, edges, *, epochs=2, seed=19, strength=0.5):
    """Update the EXISTING SpongeTD on observed legal transitions only."""
    if type(epochs) is not int or epochs < 1 or not edges:
        raise ValueError("positive epochs and observed edges required")
    if not 0 <= strength <= 1:
        raise ValueError("invalid shaping strength")
    order = list(edges)
    rng = random.Random(seed)
    for _ in range(epochs):
        rng.shuffle(order)
        for state, action, nxt in order:
            before = pair_distances(state)
            after = pair_distances(nxt)
            for (pid, config, bd, bs), (nid, nc, nd, ns) in zip(before, after):
                if pid != nid:
                    raise AssertionError("pair identity changed under legal turn")
                reward = joint_temperature_reward(
                    bd, nd, bs, ns, learner.gamma, strength)
                learner.learn((pid, config), action, reward, (pid, nc),
                              ns == (True, True))
    return {"observed_edges": len(edges), "epochs": epochs,
            "pairs_per_transition": 96, "td_updates": learner.steps,
            "strength": strength,
            "reward": "newly solved pair + discounted local joint closeness change",
            "reference_solver_used": False}


def experiment(*, train_seeds=range(16), test_seeds=range(33000, 33005),
               train_lengths=(2, 3, 4, 5, 6),
               test_lengths=(3, 4, 5, 6, 20), epochs=2,
               strength=0.5, work_budget=64, output=None):
    train_seeds, test_seeds = tuple(train_seeds), tuple(test_seeds)
    if (not train_seeds or not test_seeds
            or len(set(train_seeds)) != len(train_seeds)
            or len(set(test_seeds)) != len(test_seeds)
            or set(train_seeds) & set(test_seeds)):
        raise ValueError("unique disjoint train/test seeds required")
    if (not train_lengths or not test_lengths or type(epochs) is not int
            or epochs < 1 or type(work_budget) is not int or work_budget < 1):
        raise ValueError("invalid experiment configuration")
    states, episodes = collect_states(train_seeds, train_lengths)
    known = {canonical(s)[0] for s in states}
    edges = observed_edges(states)
    with TemporaryDirectory(prefix="bean-cube-joint-temp-") as tmp:
        full = SpongeTD(Path(tmp) / "full.db", actions=MOVES,
                        alpha=1, gamma=.9, epsilon=0, seed=19)
        baseline = SpongeTD(Path(tmp) / "baseline.db", actions=MOVES,
                            alpha=1, gamma=.9, epsilon=0, seed=19)
        candidate = SpongeTD(Path(tmp) / "candidate.db", actions=MOVES,
                             alpha=1, gamma=.9, epsilon=0, seed=19)
        try:
            full_training = learn_symmetric(full, states, epochs=epochs)
            base_training = train_pairs(baseline, edges, epochs=epochs)
            new_training = train_joint_temperature(
                candidate, edges, epochs=epochs, strength=strength)
            if baseline.steps != candidate.steps:
                raise AssertionError("joint TD update budgets differ")
            frozen = (_digest(full.q), _digest(baseline.q), _digest(candidate.q))
            cases, excluded, seen = [], [], set()
            for seed in test_seeds:
                for length in test_lengths:
                    recipe = scramble(seed, length)
                    state = apply(SOLVED, recipe)
                    key = canonical(state)[0]
                    reason = ("training_rotation_overlap" if key in known else
                              "duplicate_holdout_rotation_class" if key in seen else None)
                    if reason:
                        excluded.append({"seed": seed, "scramble_length": length,
                                         "scramble_evaluator_only": recipe,
                                         "state": state, "canonical_state": key,
                                         "reason": reason})
                        continue
                    seen.add(key)
                    fm, fi = policy_solve_value_rollout(full, state)
                    bm, bi = policy_solve_joint_rescue(
                        full, baseline, state, rescue_backup=True,
                        work_budget=work_budget)
                    cm, ci = policy_solve_joint_rescue(
                        full, candidate, state, rescue_backup=True,
                        work_budget=work_budget)
                    fok, bok, cok = (apply(state, route) == SOLVED
                                     for route in (fm, bm, cm))
                    if (fok != fi["solved"] or bok != bi["solved"]
                            or cok != ci["solved"]):
                        raise AssertionError("independent replay disagrees with controller")
                    cases.append({
                        "seed": seed, "scramble_length": length,
                        "scramble_evaluator_only": recipe, "state": state,
                        "canonical_state": key,
                        "full_moves": fm, "full_solved": fok,
                        "full_failure": fi["failure"],
                        "baseline_moves": bm, "baseline_move_count": len(bm),
                        "baseline_solved": bok, "baseline_failure": bi["failure"],
                        "baseline_paused": bi["paused"],
                        "baseline_checkpoint": bi["checkpoint"],
                        "candidate_moves": cm, "candidate_move_count": len(cm),
                        "candidate_solved": cok, "candidate_failure": ci["failure"],
                        "candidate_paused": ci["paused"],
                        "candidate_checkpoint": ci["checkpoint"],
                        "candidate_better": cok and not bok,
                        "candidate_worse": bok and not cok,
                        "candidate_shorter": cok and bok and len(cm) < len(bm),
                        "optimality_proven": False})
            if frozen != (_digest(full.q), _digest(baseline.q), _digest(candidate.q)):
                raise AssertionError("holdout mutated frozen Q weights")
            result = {
                "schema": SCHEMA,
                "source_revision": os.environ.get("GITHUB_SHA", "local_unverified"),
                "module_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                "mechanism": "BEAN SpongeTD 96-pair local temperature shaping",
                "reference_solver_used": False, "inverse_scramble_used": False,
                "not_general_solver": True, "optimality_unproven": True,
                "train_seeds": list(train_seeds), "test_seeds": list(test_seeds),
                "train_lengths": list(train_lengths), "test_lengths": list(test_lengths),
                "training_episodes": episodes,
                "full_training": full_training, "baseline_training": base_training,
                "candidate_training": new_training,
                "matched_joint_td_updates": candidate.steps,
                "work_budget_per_invocation": work_budget,
                "full_q_sha256": frozen[0], "baseline_q_sha256": frozen[1],
                "candidate_q_sha256": frozen[2],
                "eligible_cases": len(cases), "excluded_count": len(excluded),
                "full_solved": sum(c["full_solved"] for c in cases),
                "baseline_solved": sum(c["baseline_solved"] for c in cases),
                "candidate_solved": sum(c["candidate_solved"] for c in cases),
                "candidate_better": sum(c["candidate_better"] for c in cases),
                "candidate_worse": sum(c["candidate_worse"] for c in cases),
                "candidate_shorter": sum(c["candidate_shorter"] for c in cases),
                "baseline_paused": sum(c["baseline_paused"] for c in cases),
                "candidate_paused": sum(c["candidate_paused"] for c in cases),
                "twenty_turn_cases": sum(c["scramble_length"] == 20 for c in cases),
                "twenty_turn_solved": sum(c["candidate_solved"] for c in cases
                                          if c["scramble_length"] == 20),
                "excluded": excluded, "cases": cases,
                "caveat": "Local pair rewards may not coordinate global cube goals; "
                          "no full-cube mastery or shortest-route proof."}
            result["sha256"] = _digest(result)
            if output is not None:
                path = Path(output)
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
            return result
        finally:
            full.close()
            baseline.close()
            candidate.close()


def verify_receipt(path):
    """Independent legal-state replay, original scramble check, and count audit."""
    record = json.loads(Path(path).read_text(encoding="utf-8"))
    saved = record.get("sha256")
    if record.get("schema") != SCHEMA or saved != _digest(
            {k: v for k, v in record.items() if k != "sha256"}):
        raise ValueError("receipt checksum or schema mismatch")
    if record["eligible_cases"] != len(record["cases"]):
        raise ValueError("case count mismatch")
    if record["excluded_count"] != len(record["excluded"]):
        raise ValueError("excluded count mismatch")
    if set(record["train_seeds"]) & set(record["test_seeds"]):
        raise ValueError("training/holdout overlap")
    for row in record["cases"] + record["excluded"]:
        if (row["scramble_evaluator_only"] !=
                scramble(row["seed"], row["scramble_length"])):
            raise ValueError("original scramble mismatch")
        if apply(SOLVED, row["scramble_evaluator_only"]) != row["state"]:
            raise ValueError("original cube state mismatch")
        validate_legal_cube(row["state"])
        if canonical(row["state"])[0] != row["canonical_state"]:
            raise ValueError("rotation-class mismatch")
    for row in record["cases"]:
        for prefix in ("full", "baseline", "candidate"):
            moves = row[prefix + "_moves"]
            if any(move not in MOVES for move in moves):
                raise ValueError("illegal policy move")
            if (apply(row["state"], moves) == SOLVED) != row[prefix + "_solved"]:
                raise ValueError("forged solved-state claim")
            if prefix != "full":
                if len(moves) != row[prefix + "_move_count"]:
                    raise ValueError("forged move count")
                checkpoint = row[prefix + "_checkpoint"]
                if row[prefix + "_paused"] != (checkpoint is not None):
                    raise ValueError("pause/checkpoint mismatch")
                if checkpoint is not None and (
                        checkpoint.get("route") != moves or
                        checkpoint.get("start") != row["state"]):
                    raise ValueError("checkpoint route mismatch")
        if (row["candidate_better"] != (
                row["candidate_solved"] and not row["baseline_solved"])
                or row["candidate_worse"] != (
                    row["baseline_solved"] and not row["candidate_solved"])):
            raise ValueError("candidate comparison mismatch")
    for field in ("full_solved", "baseline_solved", "candidate_solved",
                  "candidate_better", "candidate_worse", "candidate_shorter",
                  "baseline_paused", "candidate_paused"):
        if record[field] != sum(bool(row[field]) for row in record["cases"]):
            raise ValueError("aggregate mismatch: " + field)
    if record["twenty_turn_solved"] != sum(
            row["candidate_solved"] for row in record["cases"]
            if row["scramble_length"] == 20):
        raise ValueError("20-turn count mismatch")
    return {"verified": True, "eligible_cases": len(record["cases"]),
            "candidate_solved": record["candidate_solved"],
            "baseline_solved": record["baseline_solved"],
            "twenty_turn_solved": record["twenty_turn_solved"],
            "sha256": saved}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--test-seed-start", type=int, default=33000)
    parser.add_argument("--test-count", type=int, default=5)
    parser.add_argument("--work-budget", type=int, default=64)
    parser.add_argument("--output", default="cognitive-gauntlet-results/joint-temperature-33000.json")
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    if args.verify:
        result = verify_receipt(args.output)
    else:
        result = experiment(
            test_seeds=range(args.test_seed_start,
                             args.test_seed_start + args.test_count),
            work_budget=args.work_budget, output=args.output)
    print(json.dumps({k: v for k, v in result.items() if k in
                      ("verified", "eligible_cases", "excluded_count",
                       "baseline_solved", "candidate_solved", "candidate_better",
                       "candidate_worse", "twenty_turn_solved", "sha256")}, indent=2))
