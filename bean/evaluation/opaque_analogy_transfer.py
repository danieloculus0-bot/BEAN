"""BEAN blind concept-binding experiment: learn an analogy without a supplied mapping.

BEAN learns a policy on nonlinear shop maintenance, then sees *opaque numeric
channels* when working on an unrelated research portfolio. The learner is
never given the channel-to-concept permutation; it must discover a binding
from matched target-development intervention outcomes, freeze it in its own
SHA-linked SQLite evidence, and apply it to new untouched test situations.

Ablations: blindly assumed identity binding, scrambled binding, random,
urgent, and target-only joint arm+binding search. Target observation channels
are engineered by the independent environment. This tests learned *binding*
of existing concepts, not unsupervised invention of those concepts.
"""
from __future__ import annotations

from hashlib import sha256
from itertools import permutations
from pathlib import Path
import argparse
import json
import statistics

from bean.learning.experimental import ExperienceBank
from bean.optimization.autodev import canonical
from bean.evaluation.abstract_nonlinear_transfer import (
    HORIZON, POLICIES, TRAIN_SEEDS, clip,
    make_ideas, ideas_features, ideas_step, ideas_utility,
    compare, learn_principle, recover_principle, score_action,
)

SCHEMA = "bean.blind_concept_binding.v1"
ROLES = ("need", "leverage", "cost", "uncertainty", "near_tip")
ALL_BINDINGS = tuple(permutations(range(len(ROLES))))
DEVELOPMENT = tuple(range(71000, 71024))
BLIND = tuple(range(82000, 82080))
DEFAULT_WIRING = (4, 1, 3, 0, 2)
ALTERNATE_WIRING = (2, 4, 0, 3, 1)


def opaque_target_observations(world, wiring):
    """Environment-only encoder. Learner receives 5 unlabeled channels/action.

    The wiring is NOT an argument to the learner, binding search or policy
    scorer. Labels and action-feature semantics are withheld.
    """
    if sorted(wiring) != list(range(5)):
        raise ValueError("Invalid benchmark sensor wiring")
    vectors = []
    for item in ideas_features(world):
        values = tuple(clip(item[role]) for role in ROLES)
        vectors.append((item["id"], tuple(values[column] for column in wiring)))
    return vectors


def select_from_channels(arm, vectors, binding):
    if len(binding) != 5 or sorted(binding) != list(range(5)):
        raise ValueError("Candidate role binding is not a permutation")
    candidates = []
    for identifier, channels in vectors:
        bound = dict(zip(ROLES, (channels[i] for i in binding)))
        candidates.append((score_action(arm, bound), -identifier, identifier))
    return max(candidates)[-1]


def replay(seed, arm, binding, observed):
    """Use target observation callback ONLY; no privileged semantic mapping."""
    world = make_ideas(seed)
    total = 0.
    actions = []
    for stage in range(HORIZON):
        vectors = observed(world)
        action = select_from_channels(arm, vectors, binding)
        actions.append(action)
        fee = ideas_step(world, action, stage)
        total += ideas_utility(world)/HORIZON - fee
    return round(total, 8), actions


def evaluate_bindings(dev_seeds, arm, observed):
    """Rank every possible latent concept binding on identical dev cases."""
    if not dev_seeds or len(set(dev_seeds)) != len(dev_seeds):
        raise ValueError("Need independently identified development cases")
    scores = []
    for binding in ALL_BINDINGS:
        rewards = [replay(seed, arm, binding, observed)[0]
                   for seed in dev_seeds]
        scores.append({
            "binding": list(binding),
            "mean_reward": round(statistics.mean(rewards), 8),
            "cases": len(rewards),
        })
    scores.sort(key=lambda entry: (-entry["mean_reward"], entry["binding"]))
    return scores


def compare_target_only(dev_seeds, observed):
    """Strong control: target dev can choose BOTH policy and binding."""
    best = None
    for arm in POLICIES:
        for row in evaluate_bindings(dev_seeds, arm, observed):
            candidate = (row["mean_reward"], arm, row["binding"])
            if best is None or candidate[0] > best[0] + 1e-9 or (
                    abs(candidate[0]-best[0]) <= 1e-9
                    and (candidate[1], candidate[2]) < (best[1], best[2])):
                best = candidate
            # Sorted rows; only best binding per policy matters.
            break
    return {"arm": best[1], "binding": best[2], "dev_reward": best[0]}


def retain_binding(bank, *, source_policy, development_seeds, learned_rows,
                   target_only, observation_identifier):
    if recover_principle(bank) != source_policy:
        raise ValueError("Binding proposal is not linked to retained source policy")
    if len(development_seeds) < 16 or len(set(development_seeds)) != len(development_seeds):
        raise ValueError("Insufficient distinct development cases")
    if len(learned_rows) != len(ALL_BINDINGS) or (
            {tuple(row["binding"]) for row in learned_rows}
            != set(ALL_BINDINGS)):
        raise ValueError("Incomplete permutation exploration")
    if any(event["kind"] == "trial"
           and event["data"].get("experiment") == SCHEMA
           for event in bank.journal.events()):
        raise ValueError("Duplicate latent-mapping experiment")
    result = {
        "schema": "bean.adaptive_lab026.v1",
        "experiment": SCHEMA,
        "phase": "development_binding_selection",
        "source_policy": source_policy,
        "opaque_observation_id": observation_identifier,
        "development_cases": len(development_seeds),
        "development_seed_digest": sha256(
            canonical(list(development_seeds))).hexdigest(),
        "candidate_bindings": len(learned_rows),
        "selected_binding": learned_rows[0]["binding"],
        "binding_development_mean_reward": learned_rows[0]["mean_reward"],
        "development_ranked_bindings_sha256": sha256(canonical(learned_rows)).hexdigest(),
        "target_only_comparator": target_only,
        "decision_source": "empirical_matched_interventions",
        "blind_rewards_visible_when_deciding": False,
        "independently_authenticated": False,
        "actions_authorized": False,
    }
    result["record_sha256"] = sha256(canonical(result)).hexdigest()
    bank.record_trial(result)
    return result


def recover_binding(bank):
    items = [e["data"] for e in bank.journal.events()
             if e["kind"] == "trial"
             and e["data"].get("experiment") == SCHEMA
             and e["data"].get("phase") == "development_binding_selection"]
    if len(items) != 1:
        raise ValueError("Missing or duplicate retained binding")
    receipt = dict(items[0])
    supplied = receipt.pop("record_sha256", None)
    if supplied != sha256(canonical(receipt)).hexdigest():
        raise ValueError("Altered source-linked concept binding")
    if receipt["candidate_bindings"] != len(ALL_BINDINGS):
        raise ValueError("Not all concepts were considered")
    return items[0]


def run_experiment(database, *, source_seeds=TRAIN_SEEDS,
                   development=DEVELOPMENT, blind=BLIND,
                   wiring=DEFAULT_WIRING):
    if (not all(isinstance(x, int) for x in (*source_seeds, *development, *blind))
            or any(len(set(dataset)) != len(dataset) for dataset in
                   (source_seeds, development, blind))
            or set(source_seeds) & set(development)
            or set(source_seeds) & set(blind)
            or set(development) & set(blind)
            or len(source_seeds) < 16 or len(development) < 16
            or len(blind) < 32):
        raise ValueError("Experiment phases require distinct disjoint seeds")
    if sorted(wiring) != list(range(5)):
        raise ValueError("Invalid sensor permutation")
    observed = lambda world: opaque_target_observations(world, wiring)
    bank = ExperienceBank(database)
    try:
        source = learn_principle(bank, compare("shop", source_seeds))
        prior = recover_principle(bank)
        learned = evaluate_bindings(development, prior, observed)
        target_only = compare_target_only(development, observed)
        receipt = retain_binding(
            bank, source_policy=prior, development_seeds=development,
            learned_rows=learned, target_only=target_only,
            observation_identifier="opaque-five-channel-v1")
        pinned_tip = bank.journal.export()["tip"]
    finally:
        bank.close()

    reopened = ExperienceBank(database)
    try:
        saved = recover_binding(reopened)
        check_prior = recover_principle(reopened)
    finally:
        reopened.close()
    if saved["record_sha256"] != receipt["record_sha256"] or check_prior != prior:
        raise ValueError("Retained source policy and target binding changed on restart")

    controls = {
        "BEAN_source_plus_discovered_mapping":
            (prior, saved["selected_binding"]),
        "source_assumed_identity":
            (prior, list(range(5))),
        "source_shuffled_control":
            (prior, [2, 0, 4, 1, 3]),
        "no_source_target_only":
            (target_only["arm"], target_only["binding"]),
        "urgency_assumed_identity":
            ("urgent", list(range(5))),
    }
    results = {k: [] for k in (*controls, "random")}
    win_counts = {k: 0 for k in controls if k != "BEAN_source_plus_discovered_mapping"}
    for seed in blind:
        for label, (arm, binding) in controls.items():
            results[label].append(replay(seed, arm, binding, observed)[0])
        # Public fixed-random baseline from original experiment.
        from bean.evaluation.abstract_nonlinear_transfer import rollout
        results["random"].append(rollout("ideas", seed, "random")["utility"])
        primary = results["BEAN_source_plus_discovered_mapping"][-1]
        for k in win_counts:
            win_counts[k] += primary > results[k][-1]
    averaged = {k: round(statistics.mean(v), 6) for k,v in results.items()}
    source_reward = averaged["BEAN_source_plus_discovered_mapping"]
    report = {
        "schema": SCHEMA,
        "source_training_cases": len(source_seeds),
        "development_cases": len(development),
        "blind_cases": len(blind),
        "source_selected_policy": prior,
        "retained_binding": saved["selected_binding"],
        "source_policy_mean_utility": source_record_summary(source),
        "binding_search_candidates": len(learned),
        "development_best_binding_mean": saved["binding_development_mean_reward"],
        "development_target_only_control": target_only,
        "blind_means": averaged,
        "blind_wins_vs_controls": win_counts,
        "blind_delta_vs_identity": round(source_reward-averaged["source_assumed_identity"], 6),
        "blind_delta_vs_target_only": round(source_reward-averaged["no_source_target_only"], 6),
        "blind_delta_vs_random": round(source_reward-averaged["random"], 6),
        "ledger_tip_before_blind": pinned_tip,
        "retained_record_sha256": saved["record_sha256"],
        "observation_wiring_exposed_to_learner": False,
        "engineered_target_observation_channels": True,
        "blind_used_in_model_selection": False,
        "actions_authorized": False,
    }
    report["report_sha256"] = sha256(canonical(report)).hexdigest()
    bank = ExperienceBank(database)
    try:
        bank.record_trial({
            "schema": "bean.adaptive_lab026.v1",
            "experiment": SCHEMA, "phase": "post_selection_blind_scoring",
            "report_sha256": report["report_sha256"],
            "source_binding_receipt": saved["record_sha256"],
        })
        report["ledger_tip_after_blind"] = bank.journal.export()["tip"]
    finally:
        bank.close()
    return report


def source_record_summary(source):
    return {
        "source_policy": source["measured_selected_policy"],
        "source_policy_training_mean": source["source_mean_utility"][
            source["measured_selected_policy"]],
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--wiring", choices=("a", "b"), default="a")
    arg = parser.parse_args(argv)
    report = run_experiment(
        arg.database,
        wiring=DEFAULT_WIRING if arg.wiring == "a" else ALTERNATE_WIRING)
    if arg.output:
        arg.output.parent.mkdir(parents=True, exist_ok=True)
        arg.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print("BEAN_OPAQUE_ANALOGY_TRANSFER " + json.dumps({
        k:v for k,v in report.items()
        if k not in ("retained_record_sha256", "ledger_tip_before_blind",
                     "ledger_tip_after_blind")
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
