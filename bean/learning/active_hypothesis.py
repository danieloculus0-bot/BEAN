"""BEAN's CPU-only active hypothesis induction for bounded numeric controls.

The learner generates its own candidate rules from a fixed transparent grammar,
chooses informative probes, measures actual reward for each available action,
and may abstain. No expert candidate, correct sensor, action mapping or target
answers are supplied. Open-ended concept invention is NOT implemented.
"""
from __future__ import annotations
from hashlib import sha256
from itertools import combinations
import json
import math
import random

SCHEMA = "bean.native.active_hypothesis.v1"
ACTIONS = (-1, 0, 1)


def _number(value):
    return type(value) in (int, float) and math.isfinite(value)


def _vector(value, *, dimensions=None):
    if not isinstance(value, (list, tuple)) or not 2 <= len(value) <= 8:
        raise ValueError("Expected 2..8 numeric sensor channels")
    if dimensions is not None and len(value) != dimensions:
        raise ValueError("Sensor layout changed within a task")
    if not all(_number(x) and abs(x) <= 100000 for x in value):
        raise ValueError("Sensors must be bounded finite numbers")
    return tuple(float(x) for x in value)


def _sensor_fingerprint(value):
    """Stable fingerprint for a complete, validated numeric observation."""
    state = _vector(value)
    return sha256(json.dumps(
        state, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def generate(dimensions):
    """Compose candidate actions from channels, differences and constants."""
    if type(dimensions) is not int or not 2 <= dimensions <= 8:
        raise ValueError("Unsupported channel count")
    candidates = []
    for i in range(dimensions):
        for polarity in (-1, 1):
            candidates.append({"kind": "channel", "lhs": i, "rhs": None,
                               "polarity": polarity})
    for a, b in combinations(range(dimensions), 2):
        for polarity in (-1, 1):
            candidates.append({"kind": "difference", "lhs": a, "rhs": b,
                               "polarity": polarity})
    for constant in ACTIONS:
        candidates.append({"kind": "constant", "lhs": None, "rhs": None,
                           "polarity": constant})
    return candidates


def act(rule, state):
    if rule["kind"] == "constant":
        return rule["polarity"]
    score = state[rule["lhs"]]
    if rule["kind"] == "difference":
        score -= state[rule["rhs"]]
    elif rule["kind"] != "channel":
        raise ValueError("Unrecognized hypothesis kind")
    score *= rule["polarity"]
    return 1 if score > 0 else (-1 if score < 0 else 0)


def _entropy(actions):
    counts = [actions.count(value) for value in ACTIONS]
    length = len(actions)
    return 1 - sum((c / length) ** 2 for c in counts)


def discover(*, probe_ids, observe, reward, budget=12, method="disagreement",
             seed=0, tolerance=0.12, min_gap=0.08,
             validation_probe_ids=None):
    """Choose and execute bounded resettable paired-intervention experiments.

    observe(probe_id) exposes ONLY the sensor vector. reward(probe_id, action)
    is a *real* host simulation or observation callback for that action;
    each action is evaluated on the same resettable case. Neither callback
    may expose the withheld mapping or blind outcomes.

    The passive comparator uses identical actions and number of probes.
    Optional disjoint validation cases are evaluated only AFTER hypothesis
    selection, so they cannot influence the fitted candidate or probe order.
    Validation is an evidence gate, not a final independent blind benchmark.
    """
    if (not isinstance(probe_ids, (tuple, list)) or
            not 3 <= len(probe_ids) <= 96 or
            not all(isinstance(x, str) and 0 < len(x) <= 128
                    for x in probe_ids) or len(set(probe_ids)) != len(probe_ids)):
        raise ValueError("Require 3..96 unique bounded probe identifiers")
    if validation_probe_ids is not None:
        if (not isinstance(validation_probe_ids, (tuple, list)) or
                not 3 <= len(validation_probe_ids) <= 32 or
                any(not isinstance(pid, str) or not 0 < len(pid) <= 128
                    for pid in validation_probe_ids) or
                len(set(validation_probe_ids)) != len(validation_probe_ids) or
                set(validation_probe_ids) & set(probe_ids)):
            raise ValueError("Require 3..32 unique unseen validation probe IDs")
    if not callable(observe) or not callable(reward):
        raise ValueError("Live observation and reward callbacks required")
    if type(budget) is not int or not 1 <= budget <= 16 or budget > len(probe_ids):
        raise ValueError("Probe budget must be 1..16 and within pool size")
    if method not in ("disagreement", "passive"):
        raise ValueError("Unknown probe strategy")
    if not all(_number(v) and v >= 0 for v in (tolerance, min_gap)):
        raise ValueError("Nonnegative finite decision thresholds required")
    views = {pid: _vector(observe(pid)) for pid in probe_ids}
    n = len(next(iter(views.values())))
    if any(len(v) != n for v in views.values()):
        raise ValueError("Sensor vectors changed length")
    # Distinct IDs do not make duplicated sensor states independent probes.
    # Reject the full training pool before any reward evaluations so a
    # relabelled observation cannot inflate support for a hypothesis.
    if len(set(views.values())) != len(views):
        raise ValueError("Training requires distinct training sensor states")
    validation_views = {}
    if validation_probe_ids is not None:
        # IDs alone do not prove independent validation: a host may relabel
        # a previously observed state. Collect withheld observations before
        # reward probes, without exposing them to candidate selection.
        validation_views = {
            pid: _vector(observe(pid), dimensions=n)
            for pid in validation_probe_ids
        }
        training_states = set(views.values())
        validation_states = list(validation_views.values())
        if (len(set(validation_states)) != len(validation_states)
                or any(state in training_states for state in validation_states)):
            raise ValueError(
                "Validation requires sensor states unseen in training and "
                "distinct within validation")
    rules = generate(n)
    losses = [0.0] * len(rules)
    remaining = list(probe_ids)
    rng = random.Random(seed)
    records = []
    for index in range(budget):
        best = min(losses)
        # Do not explore candidates already disproven by several probes.
        considered = [i for i, loss in enumerate(losses)
                      if loss - best <= max(0.9, 0.3 * (index + 1))]
        if method == "disagreement":
            chosen = max(remaining, key=lambda pid:
                         (_entropy([act(rules[i], views[pid])
                                    for i in considered]), -remaining.index(pid)))
        else:
            chosen = remaining[rng.randrange(len(remaining))]
        remaining.remove(chosen)
        outcomes = []
        for action in ACTIONS:
            measurement = reward(chosen, action)
            if not _number(measurement):
                raise ValueError("Non-finite or invalid real reward")
            outcomes.append(float(measurement))
        optimal = max(outcomes)
        for i, rule in enumerate(rules):
            prediction = act(rule, views[chosen])
            losses[i] += optimal - outcomes[ACTIONS.index(prediction)]
        records.append({
            "probe_id": chosen, "sensors": views[chosen],
            "rewards_by_action": list(zip(ACTIONS, outcomes)),
            "candidate_pool_size": len(considered),
            "informational_split": round(_entropy(
                [act(rules[i], views[chosen]) for i in considered]), 8),
        })
    order = sorted(range(len(rules)), key=lambda i: (losses[i], i))
    first, second = order[:2]
    gap = losses[second] - losses[first]
    selected = (rules[first] if
                losses[first] / budget <= tolerance and gap / budget >= min_gap
                else None)
    validation = None
    failure_reason = None if selected else "insufficient_evidence_or_model_mismatch"
    if validation_probe_ids is not None:
        validation_records = []
        for pid in validation_probe_ids:
            sensors = validation_views[pid]
            scores = []
            for action in ACTIONS:
                measurement = reward(pid, action)
                if not _number(measurement):
                    raise ValueError("Non-finite or invalid validation reward")
                scores.append(float(measurement))
            prediction = act(selected, sensors) if selected is not None else None
            regret = (max(scores) - scores[ACTIONS.index(prediction)]
                      if prediction is not None else None)
            validation_records.append({
                "probe_id": pid, "sensors": sensors,
                "rewards_by_action": list(zip(ACTIONS, scores)),
                "predicted_action": prediction, "regret": regret,
            })
        average_regret = (sum(row["regret"] for row in validation_records) /
                          len(validation_records) if selected is not None else None)
        passed = (average_regret <= tolerance if average_regret is not None
                  else False)
        validation = {
            "probe_ids": list(validation_probe_ids),
            "records": validation_records,
            "mean_regret": average_regret,
            "tolerance": tolerance,
            "passed": passed,
            "measured_by": "host_reward_callback",
            "independently_authenticated": False,
            "used_for_candidate_generation": False,
            "separate_from_final_blind_evaluation": True,
        }
        if selected is not None and not passed:
            selected = None
            failure_reason = "fresh_validation_regret_exceeded_tolerance"
    result = {
        "schema": SCHEMA, "method": method, "grammar": (
            "signed_sensor", "signed_sensor_difference", "constant_action"),
        "hypotheses_generated": len(rules),
        "candidate_source": "local_compositional_search",
        "correct_sensor_or_policy_supplied": False,
        "probe_selection": "candidate_action_disagreement" if method == "disagreement"
            else "random_without_replacement",
        "probes_used": budget, "reward_calls": budget * len(ACTIONS),
        # All candidate sensors are observed before reward probes are chosen.
        # Retain the entire observed pool so later revisions cannot recycle
        # unrewarded observations and mislabel them as fresh evidence.
        "observed_probe_ids": (list(probe_ids) +
                               (list(validation_probe_ids)
                                if validation_probe_ids is not None else [])),
        # Every observation, not only rewarded probes, is fingerprinted so
        # later revisions can reject the same sensor state under a new ID.
        # This is a local evidence identity check, not a claim that two
        # distinct states are statistically independent.
        "observed_sensor_fingerprints": {
            pid: _sensor_fingerprint(state)
            for pid, state in (*views.items(), *validation_views.items())
        },
        "sensor_fingerprint_coverage": "all_observed_probe_ids",
        "sensor_observations": len(views) + (
            len(validation_probe_ids) if validation_probe_ids is not None else 0),
        "records": records,
        "best_rule": rules[first], "best_loss_per_probe": losses[first] / budget,
        "second_best_gap_per_probe": gap / budget,
        "selected_rule": selected,
        "status": "provisional_rule" if selected else "abstain",
        "failure_reason": failure_reason,
        "blind_cases_used": False,
        "truth_oracle_used": False,
    }
    if validation is not None:
        result["validation"] = validation
        result["reward_calls"] += len(validation_probe_ids) * len(ACTIONS)
    result["evidence_sha256"] = sha256(json.dumps(
        result, sort_keys=True, separators=(",", ":"),
        allow_nan=False).encode()).hexdigest()
    return result
