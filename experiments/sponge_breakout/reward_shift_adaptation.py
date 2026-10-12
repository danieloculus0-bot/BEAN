"""Preregistered diagnostic of DQN task-reversal adaptation, not proof of AGI.

See docs/neuroevolution-reward-shift-adaptation-prereg-20261012.md.
Different seed domain from Breakout, no sealed Breakout data accessed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import statistics
from pathlib import Path

import torch

from bean.optimization.sponge_dqn import SpongeDQN, features

SEEDS = (2001, 2002, 2003)
PHASE_A_STEPS = 2400
PHASE_B_STEPS = 1800
NOISE_STEPS = 1800
VALIDATION_SIZE = 300
HOLDOUT_SIZE = 600
CURVE_STEPS = (0, 300, 600, 900, 1200, 1500, 1800)
EPSILON = 0.15


def make_states(rng, n):
    return [(rng.randrange(15), rng.randrange(2), rng.randrange(2))
            for _ in range(n)]


def correct_action(state, changed=False):
    base = (state[0] // 5 + state[1]) % 3
    return 2 - base if changed else base


def reward(action, expected):
    return 1.0 if action == expected else -1.0


def fresh_agent(seed):
    return SpongeDQN(seed=seed, batch_size=32, replay_capacity=5000,
                     warmup=64, learn_every=2, target_sync=100)


def train_step(agent, state, correct):
    action = agent.choose(state, epsilon=EPSILON)
    agent.observe(state, action, reward(action, correct), None, True)


def prediction(agent, state):
    # Unlike choose(...,epsilon=0), this does not advance the learner RNG.
    with torch.no_grad():
        q = agent.online(torch.tensor([features(state)], dtype=torch.float32))
        return int(q.argmax(dim=1).item())


def accuracy(agent, states, expected):
    return sum(prediction(agent, s) == label
               for s, label in zip(states, expected)) / len(states)


def hash_model(agent):
    blob = json.dumps(agent.weights(), sort_keys=True, separators=(",", ":"),
                      allow_nan=False).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


def run_seed(seed):
    if seed not in SEEDS:
        raise ValueError("seed not preregistered")
    torch.set_num_threads(1)
    training_rng = random.Random(10_000 + seed)
    validation = make_states(random.Random(50_000 + seed), VALIDATION_SIZE)
    valid_expected_b = [correct_action(x, changed=True) for x in validation]
    learner = fresh_agent(seed)

    for _ in range(PHASE_A_STEPS):
        state = make_states(training_rng, 1)[0]
        train_step(learner, state, correct_action(state, changed=False))

    trained_a_weights = learner.weights()
    a_model_sha = hash_model(learner)
    pre_frames, pre_updates = learner.frames, learner.updates
    curve = [{"post_change_steps": 0,
              "validation_b_accuracy": accuracy(learner, validation, valid_expected_b)}]

    for step in range(1, PHASE_B_STEPS + 1):
        state = make_states(training_rng, 1)[0]
        train_step(learner, state, correct_action(state, changed=True))
        if step in CURVE_STEPS:
            curve.append({"post_change_steps": step,
                          "validation_b_accuracy": accuracy(learner, validation, valid_expected_b)})

    adapted_model_sha = hash_model(learner)
    frozen = fresh_agent(seed + 100_000)
    frozen.load_weights(trained_a_weights)
    cold = fresh_agent(seed)
    noise = fresh_agent(seed + 200_000)
    noise_data_rng = random.Random(20_000 + seed)
    noise_label_rng = random.Random(30_000 + seed)
    for _ in range(NOISE_STEPS):
        state = make_states(noise_data_rng, 1)[0]
        train_step(noise, state, noise_label_rng.randrange(3))

    # Final confirmation dataset is generated for the first time only here.
    final_states = make_states(random.Random(70_000 + seed), HOLDOUT_SIZE)
    truth_a = [correct_action(s, changed=False) for s in final_states]
    truth_b = [correct_action(s, changed=True) for s in final_states]
    # Independently sampled noise evaluation labels have no state signal.
    independent_label_rng = random.Random(90_000 + seed)
    noise_eval_labels = [independent_label_rng.randrange(3) for _ in final_states]

    results = {
        "seed": seed,
        "setup": {
            "problem": "one-step engineered-state contextual bandit",
            "phase_A_training": PHASE_A_STEPS,
            "phase_B_training": PHASE_B_STEPS,
            "uncorrelated_control_training": NOISE_STEPS,
            "holdout_samples": HOLDOUT_SIZE,
            "validation_samples_opened_repeatedly": VALIDATION_SIZE,
            "epsilon": EPSILON,
            "rule_A": "(x // 5 + flag) % 3",
            "rule_B": "2 - rule_A",
            "holdout_rng": 70_000 + seed
        },
        "frames_updates": {
            "adapted": {"frames": learner.frames, "updates": learner.updates},
            "frozen_at_switch": {"frames": pre_frames, "updates": pre_updates},
            "random_label_control": {"frames": noise.frames, "updates": noise.updates}
        },
        "sha256": {"trained_A": a_model_sha,
                   "adapted_B": adapted_model_sha,
                   "uncorrelated_control": hash_model(noise)},
        "diagnostic_curve": curve,
        "holdout": {
            "frozen_A_on_A": accuracy(frozen, final_states, truth_a),
            "frozen_A_on_B": accuracy(frozen, final_states, truth_b),
            "adapted_B_on_B": accuracy(learner, final_states, truth_b),
            "cold_on_B": accuracy(cold, final_states, truth_b),
            "uncorrelated_control_against_random_labels":
                accuracy(noise, final_states, noise_eval_labels)
        }
    }
    results["primary_adaptation_delta"] = round(
        results["holdout"]["adapted_B_on_B"] -
        results["holdout"]["frozen_A_on_B"], 8)
    if (learner.frames != PHASE_A_STEPS + PHASE_B_STEPS
            or noise.frames != NOISE_STEPS
            or a_model_sha == adapted_model_sha
            or len(curve) != len(CURVE_STEPS)
            or not all(math.isfinite(v) for v in results["holdout"].values())):
        raise AssertionError("task or neural training contract violated")
    return results


def self_test():
    r1, r2 = random.Random(500), random.Random(500)
    assert make_states(r1, 200) == make_states(r2, 200)
    for x in range(15):
        for flag in range(2):
            for distractor in range(2):
                state = x, flag, distractor
                a, b = correct_action(state), correct_action(state, changed=True)
                assert 0 <= a < 3 and b == 2 - a
                assert correct_action((x, flag, 1 - distractor)) == a
    assert reward(1, 1) == 1.0 and reward(1, 2) == -1.0
    assert set(CURVE_STEPS) == set(range(0, 1801, 300))
    assert len(SEEDS) == len(set(SEEDS))
    return {"result": "protocol_passed", "seeds": list(SEEDS),
            "training_steps": [PHASE_A_STEPS, PHASE_B_STEPS, NOISE_STEPS]}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--self-test", action="store_true")
    p.add_argument("--seed", type=int)
    p.add_argument("--out")
    args = p.parse_args()
    if args.self_test:
        print(json.dumps(self_test(), indent=2))
        return
    if args.seed is None or not args.out:
        p.error("--seed and --out required except self-test")
    destination = Path(args.out)
    destination.mkdir(parents=True, exist_ok=True)
    if any(destination.iterdir()):
        raise ValueError("evidence output must be empty")
    result = run_seed(args.seed)
    (destination / "results.json").write_text(
        json.dumps(result, indent=2, allow_nan=False), encoding="utf-8")
    print(json.dumps({"seed": args.seed,
                      "primary_adaptation_delta": result["primary_adaptation_delta"],
                      "holdout": result["holdout"],
                      "frames_updates": result["frames_updates"]}, indent=2))


if __name__ == "__main__":
    main()
