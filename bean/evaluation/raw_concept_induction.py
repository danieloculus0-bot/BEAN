"""BEAN synthesizes task-useful concepts from unlabeled nonlinear sensor observations.

No five abstract decision-role channels are given to the learner. It sees four
opaque scalar measurements per action, one categorical group, and a common
numeric context. A grammar generates arithmetic, complement, interaction,
target-gap and group-aggregate expressions over those raw measurements.

A source-learned policy supplies ONLY a decision rule (weights for three
slots). BEAN learns which NEW sensor expressions belong in those slots by
running interventions against separate nonlinear development simulations.
The selected expression program is recorded in its original SHA journal,
reopened from disk, then scored on held-out seeds against fixed baselines.

This experiment tests empirical feature/program induction within a bounded
grammar, including generalizing after sensor permutation. It never knows or
uses the domain vocabulary for the raw feature search.
"""
from __future__ import annotations

from hashlib import sha256
from pathlib import Path
import argparse
import json
import random
import statistics

from bean.learning.experimental import ExperienceBank
from bean.optimization.autodev import canonical
from bean.evaluation.abstract_nonlinear_transfer import (
    TRAIN_SEEDS, HORIZON, compare, learn_principle, recover_principle,
    make_ideas, ideas_step, ideas_utility, ideas_features, choose, rollout,
)

SCHEMA = "bean.raw_concept_induction.v1"
DEVELOPMENT = tuple(range(93000, 93024))
BLIND = tuple(range(104000, 104080))
WIRING_A = (0, 1, 2, 3)
WIRING_B = (2, 0, 3, 1)
DEFAULT = (("raw", 0, -1), ("raw", 1, -1), ("raw", 2, -1))


def generate_program_primitives():
    """Propose a generic expression vocabulary; no semantic assignments."""
    expressions = []
    for i in range(4):
        expressions.extend((
            ("raw", i, -1),
            ("invert", i, -1),
            ("goal_gap", i, -1),
            ("group_gap", i, -1),
        ))
    for i in range(4):
        for j in range(4):
            if i != j:
                expressions.append(("product", i, j))
            expressions.append(("deficit_product", i, j))
            expressions.append(("deficit_group", i, j))
    return tuple(expressions)


EXPRS = generate_program_primitives()


def raw_observations(world, wiring):
    """Observation-only environment adapter: opaque raw scalar channels."""
    if sorted(wiring) != list(range(4)):
        raise ValueError("Raw channels must be a four-channel permutation")
    rows = []
    for index, item in enumerate(world["experiments"]):
        # Only the environment understands this schema. The learner receives
        # x0..x3 as anonymous floating-point values and group/given target.
        raw = (item["readiness"], item["potential"], item["funding"],
               item["failure_rate"])
        rows.append((index, tuple(raw[j] for j in wiring),
                     item["discipline"], world["milestone"]))
    return rows


def evaluate_expression(expr, measurements, group_max):
    operator, i, j = expr
    x, group, target = measurements
    first = x[i]
    if operator == "raw":
        return first
    if operator == "invert":
        return 1-first
    if operator == "goal_gap":
        return max(0., target-first)
    if operator == "group_gap":
        return max(0., target-group_max[(group, i)])
    if operator == "product":
        return min(1., first*x[j])
    if operator == "deficit_product":
        return min(1., (1-first)*x[j])
    if operator == "deficit_group":
        return min(1., (1-first)*max(0., target-group_max[(group,j)]))
    raise ValueError("Unknown learned feature program")


def choice_from_raw(world, learned_program, wiring):
    rows = raw_observations(world, wiring)
    by_group = {}
    for _, values, group, _ in rows:
        for i in range(4):
            key = (group, i)
            by_group[key] = max(by_group.get(key, 0.), values[i])
    scores = []
    for index, values, group, target in rows:
        state = (values, group, target)
        components = [evaluate_expression(expr, state, by_group)
                      for expr in learned_program]
        # Transfer the weights empirically selected in the previous source
        # domain. The target expression semantics are NOT supplied.
        merit = .58*components[0] + .77*components[1] - .16*components[2]
        scores.append((merit, -index, index))
    return max(scores)[-1]


def simulate(seed, learned_program, wiring):
    world = make_ideas(seed)
    reward = 0.
    for step in range(HORIZON):
        selection = choice_from_raw(world, learned_program, wiring)
        fee = ideas_step(world, selection, step)
        reward += ideas_utility(world)/HORIZON - fee
    return round(reward, 8)


def mean_score(seeds, program, wiring):
    return statistics.mean(simulate(seed, program, wiring) for seed in seeds)


def fit_program(seeds, wiring):
    """Finite program synthesis via coordinate ascent with multiple starts.

    All prior evaluation queries involve ONLY target development seeds.
    Every generated candidate is executable source code, not a keyword tag.
    """
    if len(seeds) < 16 or len(set(seeds)) != len(seeds):
        raise ValueError("Need distinct development contexts")
    if len(set(EXPRS)) != len(EXPRS):
        raise ValueError("Duplicate feature grammar program")
    seeds = tuple(seeds)
    starts = (
        DEFAULT,
        (("invert",0,-1), ("goal_gap",1,-1), ("raw",2,-1)),
        (("deficit_product",0,1), ("group_gap",0,-1), ("raw",2,-1)),
    )
    best = None
    evaluations = 0
    visited = {}
    def get_score(program):
        nonlocal evaluations
        key = tuple(program)
        if key not in visited:
            evaluations += len(seeds)
            visited[key] = mean_score(seeds, key, wiring)
        return visited[key]

    for start in starts:
        program = list(start)
        for _ in range(3):
            changed = False
            for slot in range(3):
                possibilities = []
                for expr in EXPRS:
                    candidate = list(program)
                    candidate[slot] = expr
                    possibilities.append((get_score(candidate), tuple(candidate)))
                winner = min(possibilities, key=lambda v: (-v[0], v[1]))
                if winner[1] != tuple(program):
                    changed = True
                program = list(winner[1])
            if not changed:
                break
        result = (get_score(program), tuple(program))
        if best is None or (-result[0], result[1]) < (-best[0], best[1]):
            best = result
    return {
        "program": [list(x) for x in best[1]],
        "development_mean": round(best[0], 8),
        "candidate_expressions_generated": len(EXPRS),
        "independent_programs_evaluated": len(visited),
        "development_rollouts": evaluations,
        "optimization": "three_start_bounded_coordinate_ascent",
    }


def run_experiment(database, *, source_seeds=TRAIN_SEEDS,
                   development=DEVELOPMENT, blind=BLIND, wiring=WIRING_A):
    if (sorted(wiring) != list(range(4))
            or any(len(set(values)) != len(values)
                   for values in (source_seeds, development, blind))
            or set(source_seeds) & set(development)
            or set(source_seeds) & set(blind)
            or set(development) & set(blind)
            or len(source_seeds) < 16 or len(development) < 16
            or len(blind) < 32):
        raise ValueError("Distinct disjoint source/development/blind data required")
    bank = ExperienceBank(database)
    try:
        learn_principle(bank, compare("shop", source_seeds))
        source_policy = recover_principle(bank)
        if source_policy != "balanced":
            raise ValueError("Source selected unsupported policy; do not override it")
        learned = fit_program(development, wiring)
        record = {
            "schema": "bean.adaptive_lab026.v1",
            "experiment": SCHEMA,
            "phase": "raw_program_selection",
            "source_policy": source_policy,
            "development_cases": len(development),
            "development_seed_sha256": sha256(canonical(list(development))).hexdigest(),
            "program": learned["program"],
            "development_mean": learned["development_mean"],
            "search": learned["optimization"],
            "candidate_expressions_generated": learned[
                "candidate_expressions_generated"],
            "independent_programs_evaluated": learned[
                "independent_programs_evaluated"],
            "development_rollouts": learned["development_rollouts"],
            "evidence_origin": "intervention_reward_from_development_simulations",
            "blind_utility_visible_during_learning": False,
            "raw_channel_semantics_given_to_learner": False,
            "actions_authorized": False,
        }
        record["receipt_hash"] = sha256(canonical(record)).hexdigest()
        bank.record_trial(record)
        before_tip = bank.journal.export()["tip"]
    finally:
        bank.close()

    bank = ExperienceBank(database)
    try:
        restored = [e["data"] for e in bank.journal.events()
                    if e["kind"] == "trial"
                    and e["data"].get("experiment") == SCHEMA
                    and e["data"].get("phase") == "raw_program_selection"]
        if len(restored) != 1:
            raise ValueError("Expected only one retained learned raw program")
        kept = dict(restored[0])
        h = kept.pop("receipt_hash")
        if h != sha256(canonical(kept)).hexdigest():
            raise ValueError("Modified raw program source evidence")
        if recover_principle(bank) != source_policy:
            raise ValueError("Source policy changed during restart")
        program = tuple(tuple(row) for row in kept["program"])
    finally:
        bank.close()

    observed = {"learned_raw": [], "naive_raw": [], "raw_urgency": [],
                "random": [], "engineered_concepts": []}
    for seed in blind:
        observed["learned_raw"].append(simulate(seed, program, wiring))
        observed["naive_raw"].append(simulate(seed, DEFAULT, wiring))
        # Strong existing simulator baselines are scored, not used for fitting.
        observed["random"].append(rollout("ideas", seed, "random")["utility"])
        observed["engineered_concepts"].append(
            rollout("ideas", seed, "balanced")["utility"])
        world = make_ideas(seed)
        total = 0.
        for step in range(HORIZON):
            rows = raw_observations(world, wiring)
            action = max(rows, key=lambda row: (1-row[1][wiring.index(0)], -row[0]))[0]
            cost = ideas_step(world, action, step)
            total += ideas_utility(world)/HORIZON - cost
        observed["raw_urgency"].append(round(total, 8))
    mean = {key: round(statistics.mean(scores), 6)
            for key,scores in observed.items()}
    learned_mean = mean["learned_raw"]
    baseline = observed["naive_raw"]
    actual = observed["learned_raw"]
    report = {
        "schema": SCHEMA, "source_cases": len(source_seeds),
        "development_cases": len(development),
        "blind_cases": len(blind),
        "source_selected_policy": source_policy,
        "learned_raw_program": [list(expr) for expr in program],
        "generated_candidate_expressions": learned[
            "candidate_expressions_generated"],
        "distinct_programs_evaluated": learned[
            "independent_programs_evaluated"],
        "development_reward_rollouts": learned["development_rollouts"],
        "blind_means": mean,
        "gain_over_naive_raw": round(learned_mean-mean["naive_raw"], 6),
        "gain_over_random": round(learned_mean-mean["random"], 6),
        "gain_over_engineered_concepts": round(
            learned_mean-mean["engineered_concepts"], 6),
        "win_count_vs_naive_raw": sum(a>b for a,b in zip(actual,baseline)),
        "loss_count_vs_naive_raw": sum(a<b for a,b in zip(actual,baseline)),
        "tie_count_vs_naive_raw": sum(a==b for a,b in zip(actual,baseline)),
        "blind_rewards_available_at_selection": False,
        "raw_semantic_role_mapping_supplied": False,
        "engineer_authored_expression_grammar": True,
        "origin_journal_tip_before_blind": before_tip,
        "raw_observation_permutation": list(wiring),
    }
    report["report_hash"] = sha256(canonical(report)).hexdigest()
    bank = ExperienceBank(database)
    try:
        bank.record_trial({
            "schema": "bean.adaptive_lab026.v1",
            "experiment": SCHEMA, "phase": "post_program_blind_evaluation",
            "report_hash": report["report_hash"],
            "source_program_receipt": h,
            "blind_used_during_selection": False,
        })
        report["journal_tip_after_blind"] = bank.journal.export()["tip"]
    finally:
        bank.close()
    return report


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--database", type=Path, required=True)
    ap.add_argument("--output", type=Path)
    ap.add_argument("--wiring", choices=("a","b"), default="a")
    args = ap.parse_args(argv)
    result = run_experiment(
        args.database,
        wiring=WIRING_A if args.wiring == "a" else WIRING_B)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print("BEAN_RAW_CONCEPT_DISCOVERY " + json.dumps({
        key:val for key,val in result.items()
        if key not in ("origin_journal_tip_before_blind", "journal_tip_after_blind")
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
