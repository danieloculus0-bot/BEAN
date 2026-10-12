"""Preregistered replay-reset task reversal, seeds 2004-2006 only.

Research-only paired within-learner intervention. Do not tune opened holdouts.
See docs/bean-replay-reset-adaptation-prereg-2004-2006-20261012.md.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import os
import random
import subprocess
import tempfile
from pathlib import Path

import torch

from .reward_shift_adaptation import (
    EPSILON, PHASE_A_STEPS, PHASE_B_STEPS, VALIDATION_SIZE, HOLDOUT_SIZE,
    CURVE_STEPS, make_states, correct_action, fresh_agent, train_step,
    accuracy, prediction, hash_model,
)

SEEDS = (2004, 2005, 2006)
EXPECTED_BLOBS = {
    "bean/optimization/sponge_dqn.py": "769da37ac2e13566ddc0d83c770d7323cbfc0da7",
    "experiments/sponge_breakout/reward_shift_adaptation.py": "7a986b6d0b25705dc1ba6d5e5aa1f0829fffdcfa",
}


def canonical(value):
    if isinstance(value, torch.Tensor):
        return value.detach().cpu().tolist()
    if isinstance(value, dict):
        return {str(k): canonical(v) for k, v in sorted(value.items(), key=lambda p: str(p[0]))}
    if isinstance(value, (tuple, list)):
        return [canonical(v) for v in value]
    return value


def digest(value):
    data = json.dumps(canonical(value), sort_keys=True, separators=(",", ":"),
                      allow_nan=False).encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def state_without_replay(state):
    return {key: value for key, value in state.items() if key != "replay"}


def verify_frozen_sources():
    root = Path(__file__).resolve().parents[2]
    for name, expected in EXPECTED_BLOBS.items():
        actual = subprocess.check_output(
            ["git", "hash-object", str(root / name)], cwd=root, text=True).strip()
        if actual != expected:
            raise AssertionError(f"frozen learner/task blob changed: {name} {actual}")
    return True


def diagnostics(agents, states, truth_a, truth_b, step):
    return {
        "post_change_steps": step,
        "arms": {
            name: {
                "A_accuracy": accuracy(agent, states, truth_a),
                "B_accuracy": accuracy(agent, states, truth_b),
                "frames": agent.frames,
                "updates": agent.updates,
                "replay_size": len(agent.replay),
            }
            for name, agent in agents.items()
        },
    }


def restart_predictions_sha(agent, states):
    return digest([prediction(agent, state) for state in states])


def write_json(path, obj, *, pretty=False):
    content = json.dumps(obj, sort_keys=True, indent=2 if pretty else None,
                         separators=None if pretty else (",", ":"),
                         allow_nan=False) + "\n"
    path.write_text(content, encoding="utf-8")
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def run_seed(seed, folder):
    if seed not in SEEDS:
        raise ValueError("only preregistered synthetic seeds 2004-2006")
    verify_frozen_sources()
    torch.set_num_threads(1)
    rng = random.Random(10_000 + seed)
    a_contexts = make_states(rng, PHASE_A_STEPS)
    b_contexts = make_states(rng, PHASE_B_STEPS)
    b_labels = [correct_action(s, changed=True) for s in b_contexts]
    validation = make_states(random.Random(50_000 + seed), VALIDATION_SIZE)
    valid_a = [correct_action(s) for s in validation]
    valid_b = [correct_action(s, changed=True) for s in validation]
    learner = fresh_agent(seed)
    cold = fresh_agent(seed)
    cold_sha = hash_model(cold)
    for state in a_contexts:
        train_step(learner, state, correct_action(state))
    assert learner.frames == PHASE_A_STEPS
    initial_state = learner.learner_state()
    before_hash = digest(initial_state)
    initial_model_sha = hash_model(learner)
    frozen = fresh_agent(seed + 100_000)
    frozen.load_weights(learner.weights())
    arms = {}
    for name in ("retain", "reset"):
        agent = fresh_agent(seed)
        agent.load_learner_state(copy.deepcopy(initial_state))
        if digest(agent.learner_state()) != before_hash:
            raise AssertionError("paired full learner state mismatch at switch")
        arms[name] = agent
    if hash_model(arms["retain"]) != hash_model(arms["reset"]):
        raise AssertionError("paired policies differ before replay intervention")
    arms["reset"].replay.clear()
    if len(arms["retain"].replay) != PHASE_A_STEPS or len(arms["reset"].replay) != 0:
        raise AssertionError("replay-only intervention did not occur")
    if digest(state_without_replay(arms["retain"].learner_state())) != digest(
            state_without_replay(arms["reset"].learner_state())):
        raise AssertionError("intervention changed more than replay")
    curves = [diagnostics(arms, validation, valid_a, valid_b, 0)]
    for step, (state, label) in enumerate(zip(b_contexts, b_labels), 1):
        for agent in arms.values():
            train_step(agent, state, label)
        if step in CURVE_STEPS:
            curves.append(diagnostics(arms, validation, valid_a, valid_b, step))
    if [row["post_change_steps"] for row in curves] != list(CURVE_STEPS):
        raise AssertionError("missing preregistered diagnostic checkpoint")
    if any(agent.frames != PHASE_A_STEPS + PHASE_B_STEPS for agent in arms.values()):
        raise AssertionError("unequal training interactions")
    # Open the single 600-context final paired holdout only after training finishes.
    holdout = make_states(random.Random(70_000 + seed), HOLDOUT_SIZE)
    hold_a = [correct_action(s) for s in holdout]
    hold_b = [correct_action(s, changed=True) for s in holdout]
    results_holdout = {
        "reset_B": accuracy(arms["reset"], holdout, hold_b),
        "retain_B": accuracy(arms["retain"], holdout, hold_b),
        "frozen_A_on_B": accuracy(frozen, holdout, hold_b),
        "cold_on_B": accuracy(cold, holdout, hold_b),
        "reset_A": accuracy(arms["reset"], holdout, hold_a),
        "retain_A": accuracy(arms["retain"], holdout, hold_a),
        "frozen_A_on_A": accuracy(frozen, holdout, hold_a),
    }
    if not all(math.isfinite(v) for v in results_holdout.values()):
        raise AssertionError("nonfinite final evidence")
    models = {"trained_A": frozen, "reset_B": arms["reset"],
              "retain_B": arms["retain"], "cold": cold}
    folder.mkdir(parents=True, exist_ok=True)
    if any(folder.iterdir()):
        raise ValueError("evidence output must be empty")
    model_files = {}
    for name, agent in models.items():
        filename = name + "-weights.json"
        model_files[filename] = write_json(folder / filename, agent.weights())
        if model_files[filename] != hash_model(agent):
            # The saved file has a final newline, so compare canonical payload separately.
            if digest(agent.weights()) != hash_model(agent):
                raise AssertionError("model serialization mismatch")
    results = {
        "schema": "bean.replay_reset_adaptation.v1",
        "seed": seed,
        "source_sha": os.environ.get("GITHUB_SHA", "local-unattested"),
        "frozen_git_blobs": EXPECTED_BLOBS,
        "protocol": {
            "phase_A_interactions": PHASE_A_STEPS,
            "phase_B_interactions_per_arm": PHASE_B_STEPS,
            "validation_contexts_reused": VALIDATION_SIZE,
            "final_holdout_contexts": HOLDOUT_SIZE,
            "epsilon": EPSILON,
            "paired_B_contexts": True,
            "intervention": "clear replay only at rule reversal",
            "holdout_domain": 70_000 + seed,
        },
        "switch_state_sha256": before_hash,
        "switch_nonreplay_sha256": digest(state_without_replay(initial_state)),
        "switch_replay_sizes": {"retain": PHASE_A_STEPS, "reset": 0},
        "initial_model_sha256": initial_model_sha,
        "cold_model_sha256": cold_sha,
        "diagnostic_curve": curves,
        "holdout": results_holdout,
        "primary_reset_minus_retain_B": round(
            results_holdout["reset_B"] - results_holdout["retain_B"], 8),
        "B_gain_from_switch_diagnostic": {
            name: round(curves[-1]["arms"][name]["B_accuracy"]
                        - curves[0]["arms"][name]["B_accuracy"], 8)
            for name in arms
        },
        "B_curve_mean": {
            name: round(sum(row["arms"][name]["B_accuracy"] for row in curves)
                        / len(curves), 8)
            for name in arms
        },
        "final_frames_updates": {
            name: {"frames": agent.frames, "updates": agent.updates,
                   "replay_size": len(agent.replay)}
            for name, agent in arms.items()
        },
        "model_sha256": {name: hash_model(agent) for name, agent in models.items()},
        "restart_prediction_sha256": {
            name: restart_predictions_sha(agent, validation)
            for name, agent in models.items()
        },
        "limitations": "n=3 independent seeds; repeated diagnostics are not holdouts; "
                       "clearing replay changes update count and sampling history; "
                       "single synthetic task is not general intelligence or longitudinal growth.",
    }
    results_sha = write_json(folder / "results.json", results, pretty=True)
    write_json(folder / "manifest.json", {
        "results_sha256": results_sha, "model_file_sha256": model_files,
        "model_content_sha256": results["model_sha256"],
    }, pretty=True)
    return results


def verify_dir(folder):
    torch.set_num_threads(1)
    folder = Path(folder)
    manifest = json.loads((folder / "manifest.json").read_text(encoding="utf-8"))
    results_bytes = (folder / "results.json").read_bytes()
    if hashlib.sha256(results_bytes).hexdigest() != manifest["results_sha256"]:
        raise AssertionError("results.json SHA mismatch")
    results = json.loads(results_bytes)
    validation = make_states(random.Random(50_000 + results["seed"]), VALIDATION_SIZE)
    for name in ("trained_A", "reset_B", "retain_B", "cold"):
        path = folder / (name + "-weights.json")
        if hashlib.sha256(path.read_bytes()).hexdigest() != manifest["model_file_sha256"][path.name]:
            raise AssertionError("saved model file SHA mismatch")
        weights = json.loads(path.read_text(encoding="utf-8"))
        if digest(weights) != results["model_sha256"][name]:
            raise AssertionError("saved model content SHA mismatch")
        restored = fresh_agent(results["seed"] + 900_000)
        restored.load_weights(weights)
        if hash_model(restored) != results["model_sha256"][name]:
            raise AssertionError("restored model differs")
        if restart_predictions_sha(restored, validation) != results["restart_prediction_sha256"][name]:
            raise AssertionError("restart predictions differ")
    return {"seed": results["seed"], "result": "separate_process_restart_verified",
            "model_sha256": results["model_sha256"],
            "results_sha256": manifest["results_sha256"]}


def self_test():
    torch.set_num_threads(1)
    verify_frozen_sources()
    assert len(set(SEEDS)) == 3 and all(s > 2003 for s in SEEDS)
    assert PHASE_A_STEPS == 2400 and PHASE_B_STEPS == 1800
    assert HOLDOUT_SIZE == 600 and list(CURVE_STEPS) == list(range(0, 1801, 300))
    a = fresh_agent(2001)
    for state in make_states(random.Random(999), 80):
        train_step(a, state, correct_action(state))
    saved = a.learner_state()
    left, right = fresh_agent(2001), fresh_agent(2001)
    left.load_learner_state(copy.deepcopy(saved))
    right.load_learner_state(copy.deepcopy(saved))
    assert digest(left.learner_state()) == digest(right.learner_state())
    right.replay.clear()
    assert digest(state_without_replay(left.learner_state())) == digest(
        state_without_replay(right.learner_state()))
    assert len(left.replay) == 80 and len(right.replay) == 0
    toy = make_states(random.Random(123), 12)
    for state in toy:
        train_step(left, state, correct_action(state, changed=True))
        train_step(right, state, correct_action(state, changed=True))
    with tempfile.TemporaryDirectory() as temp:
        path = Path(temp) / "model.json"
        write_json(path, right.weights())
        restored = fresh_agent(2001)
        restored.load_weights(json.loads(path.read_text(encoding="utf-8")))
        assert hash_model(restored) == hash_model(right)
        assert restart_predictions_sha(restored, toy) == restart_predictions_sha(right, toy)
    return {"result": "protocol_passed", "source_blobs": EXPECTED_BLOBS,
            "fresh_seeds_not_opened": list(SEEDS)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--verify-dir")
    parser.add_argument("--seed", type=int)
    parser.add_argument("--out")
    args = parser.parse_args()
    if args.self_test:
        print(json.dumps(self_test(), sort_keys=True))
    elif args.verify_dir:
        print(json.dumps(verify_dir(args.verify_dir), sort_keys=True))
    elif args.seed is not None and args.out:
        result = run_seed(args.seed, Path(args.out))
        print(json.dumps({"seed": result["seed"],
                          "primary_reset_minus_retain_B": result["primary_reset_minus_retain_B"],
                          "holdout": result["holdout"],
                          "final_frames_updates": result["final_frames_updates"]},
                         sort_keys=True))
    else:
        parser.error("choose --self-test, --verify-dir, or --seed with --out")


if __name__ == "__main__":
    main()
