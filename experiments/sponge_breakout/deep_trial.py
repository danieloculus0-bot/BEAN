"""Matched Breakout trial: neural DQN vs tabular SpongeTD vs untrained policy.

Same game instances and episode counts, not identical transition counts.
Selection uses validation only; final held-out scores are reported once.
Run: python -m experiments.sponge_breakout.deep_trial --out /tmp/dqn-1 --seed 1
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path
from statistics import mean

import torch

from bean.memory.compression import file_memory, recover_memory
from bean.optimization.autodev import Journal
from bean.optimization.sponge_dqn import SpongeDQN
from bean.optimization.sponge_td import SpongeTD
from .game import Breakout

TRAIN_START = 900000
VALID_START = 18000
HOLDOUT_START = 21000


def metric_sha(data):
    return hashlib.sha256(json.dumps(data, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def evaluate(action, first, games):
    if games < 30:
        raise ValueError("at least 30 games needed for scored evaluation")
    records = []
    for seed in range(first, first + games):
        env = Breakout(seed)
        while not env.done:
            env.step(action(env.state()))
        records.append({"bricks": env.hit, "survival": int(not env.miss)})
    return {"bricks": round(mean(x["bricks"] for x in records), 5),
            "survival": round(mean(x["survival"] for x in records), 5),
            "games": games, "seed_start": first}


def run(out, *, seed=1, episodes=450, validation_games=60, holdout_games=100):
    if episodes < 30 or validation_games < 30 or holdout_games < 30:
        raise ValueError("experiment requires >=30 training and evaluation games")
    torch.set_num_threads(1)
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    if any(out.iterdir()):
        raise ValueError("output directory must be empty, preventing overwritten evidence")
    neural = SpongeDQN(seed=seed * 10 + 1)
    table = SpongeTD(out / "tabular.sqlite", seed=seed * 10 + 2,
                     alpha=0.23, gamma=0.975, epsilon=0.1)
    journal = Journal(out / "neural.sqlite")
    best_neural = None
    best_table = None
    checkpoints = []
    cold = evaluate(lambda state: 0, VALID_START, validation_games)
    try:
        schedule = sorted(set([0, episodes // 3, 2 * episodes // 3, episodes]))
        for episode in range(episodes + 1):
            if episode in schedule:
                dqn_validation = evaluate(lambda s: neural.choose(s, epsilon=0), VALID_START, validation_games)
                table_snapshot = copy.deepcopy(table.q)
                tabular_validation = evaluate(
                    lambda s: max(range(3), key=lambda a: table_snapshot.get(
                        json.dumps(s, separators=(",", ":")), [0, 0, 0])[a]),
                    VALID_START, validation_games)
                deep_record = neural.checkpoint(
                    journal, baseline=cold["bricks"], candidate=dqn_validation["bricks"],
                    samples=validation_games, evaluation_sha256=metric_sha(dqn_validation),
                    episode=episode)
                table_record = table.checkpoint(
                    baseline=cold["bricks"], candidate=tabular_validation["bricks"],
                    samples=validation_games, evaluation_sha256=metric_sha(tabular_validation))
                checkpoints.append({"episode": episode, "deep": dqn_validation,
                                    "tabular": tabular_validation,
                                    "dqn_receipt": deep_record, "tabular_receipt": table_record})
                if best_neural is None or dqn_validation["bricks"] > best_neural["score"]:
                    best_neural = {"episode": episode, "score": dqn_validation["bricks"],
                                   "weights": copy.deepcopy(neural.weights())}
                if best_table is None or tabular_validation["bricks"] > best_table["score"]:
                    best_table = {"episode": episode, "score": tabular_validation["bricks"],
                                  "q": table_snapshot}
            if episode == episodes:
                break
            training_seed = TRAIN_START + seed * 100000 + episode
            env_deep = Breakout(training_seed)
            while not env_deep.done:
                old = env_deep.state()
                epsilon = max(0.05, 1.0 - 0.95 * neural.frames / 25000.0)
                act = neural.choose(old, epsilon=epsilon)
                reward = env_deep.step(act)
                neural.observe(old, act, reward, None if env_deep.done else env_deep.state(), env_deep.done)
            env_table = Breakout(training_seed)
            while not env_table.done:
                old = env_table.state()
                act = table.choose(old, explore=True)
                reward = env_table.step(act)
                table.learn(old, act, reward, None if env_table.done else env_table.state(), env_table.done)
        before_restore = metric_sha(neural.weights())
        journal_tip = journal.export()["tip"]
        journal.close()
        verified = Journal(out / "neural.sqlite")
        recovered = SpongeDQN.recover_latest(verified, seed=seed * 10 + 1)
        if metric_sha(recovered.weights()) != before_restore or verified.export()["tip"] != journal_tip:
            raise AssertionError("failed lossless neural restart or hash chain")
        verified.close()
        neural.load_weights(best_neural["weights"])
        selected_capsule = file_memory(
            best_neural["weights"],
            accuracy=max(0, min(1, best_neural["score"] / 24.0)),
            relevance=1.0, provenance=0.5, sample_count=validation_games)
        (out / "selected-neural.json").write_text(json.dumps(selected_capsule), encoding="utf-8")
        if recover_memory(selected_capsule) != neural.weights():
            raise AssertionError("selected memory altered")
        table_q = best_table["q"]
        cold_holdout = evaluate(lambda s: 0, HOLDOUT_START, holdout_games)
        deep_holdout = evaluate(lambda s: neural.choose(s, epsilon=0), HOLDOUT_START, holdout_games)
        table_holdout = evaluate(
            lambda s: max(range(3), key=lambda a: table_q.get(
                json.dumps(s, separators=(",", ":")), [0, 0, 0])[a]),
            HOLDOUT_START, holdout_games)
        result = {
            "schema": "bean.dqn.breakout.v1", "seed": seed,
            "protocol": {"episodes": episodes, "validation": validation_games,
                         "holdout": holdout_games,
                         "same_environment_seeds": True,
                         "different_transition_counts": True,
                         "input": "engineered three-value game state; NOT pixels",
                         "selection": "highest validation score; final holdout not used in selection"},
            "training": {"dqn_frames": neural.frames, "dqn_updates": neural.updates,
                         "dqn_last_loss": neural.last_loss, "tabular_frames": table.steps},
            "checkpoint_results": checkpoints,
            "selected": {"deep_episode": best_neural["episode"],
                         "tabular_episode": best_table["episode"],
                         "capsule_sha256": selected_capsule["sha256"],
                         "capsule_score": selected_capsule["score"]["value"],
                         "journal_tip": journal_tip},
            "holdout": {"cold": cold_holdout, "dqn": deep_holdout, "tabular": table_holdout},
            "delta_dqn_vs_cold": round(deep_holdout["bricks"] - cold_holdout["bricks"], 5),
            "delta_dqn_vs_tabular": round(deep_holdout["bricks"] - table_holdout["bricks"], 5),
            "interpretation": "No generalized superiority claim; report all regressions."
        }
        (out / "results.json").write_text(json.dumps(result, indent=2))
        return result
    finally:
        table.close()
        try:
            journal.close()
        except Exception:
            pass


if __name__ == "__main__":
    cli = argparse.ArgumentParser()
    cli.add_argument("--out", required=True)
    cli.add_argument("--seed", type=int, default=1)
    cli.add_argument("--episodes", type=int, default=450)
    cli.add_argument("--validation", type=int, default=60)
    cli.add_argument("--holdout", type=int, default=100)
    args = cli.parse_args()
    result = run(args.out, seed=args.seed, episodes=args.episodes,
                 validation_games=args.validation, holdout_games=args.holdout)
    print(json.dumps({"seed": result["seed"],
                      "holdout": result["holdout"],
                      "dqn_vs_tabular": result["delta_dqn_vs_tabular"]}, indent=2))
