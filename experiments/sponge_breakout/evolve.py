"""Experimental neural evolution: select, inherit, mutate, learn, and independently test.

Each DQN child inherits learned neural weights from a measured parent, receives
bounded genetic changes to optimizer/exploration and weights, then performs real
gradient learning. Candidates are scored BEFORE their compressed SHA-256 memory
is filed in the append-only BEAN Journal. Validation selects parents, never the
sealed holdout. Not pixel DQN, AGI, or an established learning advantage.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import random
from pathlib import Path
from statistics import mean

import torch

from bean.memory.compression import file_memory, recover_memory
from bean.optimization.autodev import Journal
from bean.optimization.sponge_dqn import SpongeDQN
from bean.optimization.sponge_td import score_memory
from .game import Breakout

OBJECTIVE = "sponge.neuroevolution.v1"
TRAIN_BASE, VALID_BASE, HOLDOUT_BASE = 1_000_000, 30_000, 80_000


def fingerprint(obj):
    return hashlib.sha256(json.dumps(obj, sort_keys=True,
                                     separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def evaluate(agent, *, start, games):
    outcomes = []
    for seed in range(start, start + games):
        env = Breakout(seed)
        while not env.done:
            env.step(agent.choose(env.state(), epsilon=0.0))
        outcomes.append((env.hit, int(not env.miss)))
    return {"bricks": round(mean(x[0] for x in outcomes), 5),
            "survival": round(mean(x[1] for x in outcomes), 5),
            "games": games, "seed_start": start}


def breed(parent_weights, parent_config, *, seed, mutate=True):
    rng = random.Random(seed)
    config = dict(parent_config)
    if mutate:
        config["lr"] = round(min(0.003, max(0.0001,
                              config["lr"] * rng.choice([0.7, 1.0, 1.4]))), 8)
        config["gamma"] = round(min(0.999, max(0.90,
                                 config["gamma"] + rng.choice([-0.015, 0.0, 0.015]))), 5)
        config["epsilon_floor"] = round(min(0.30, max(0.02,
                                         config["epsilon_floor"] + rng.choice([-0.04, 0.0, 0.04]))), 5)
    agent = SpongeDQN(seed=seed, lr=config["lr"], gamma=config["gamma"])
    if parent_weights is not None:
        agent.load_weights(copy.deepcopy(parent_weights))
        if mutate:
            generator = torch.Generator(device="cpu")
            generator.manual_seed(seed)
            with torch.no_grad():
                for param in agent.online.parameters():
                    param.add_(torch.randn(param.shape, generator=generator) * 0.012)
            agent.target.load_state_dict(agent.online.state_dict())
    return agent, config


def train_game(agent, episode_seed, epsilon_floor):
    env = Breakout(episode_seed)
    while not env.done:
        state = env.state()
        epsilon = max(epsilon_floor, 0.85 - 0.8 * agent.frames / 18_000)
        action = agent.choose(state, epsilon=epsilon)
        reward = env.step(action)
        agent.observe(state, action, reward, None if env.done else env.state(), env.done)


def compete(out, *, seed=41, population=3, generations=3,
            games_per_candidate=70, validation_games=60, holdout_games=120):
    if not 2 <= population <= 8 or not 1 <= generations <= 12:
        raise ValueError("invalid search breadth or generations")
    if not 1 <= games_per_candidate <= 3000:
        raise ValueError("invalid training budget")
    if not 30 <= validation_games <= 500 or not 30 <= holdout_games <= 2000:
        raise ValueError("insufficient or excessive evaluation budget")
    torch.set_num_threads(1)
    folder = Path(out)
    folder.mkdir(parents=True, exist_ok=True)
    if any(folder.iterdir()):
        raise ValueError("output must be empty; no evidence overwritten")
    journal = Journal(folder / "evolution.sqlite")
    controls = {"lr": 0.0007, "gamma": 0.99, "epsilon_floor": 0.06}
    cold_agent, _ = breed(None, controls, seed=seed, mutate=False)
    # Validation baseline and final baseline are separate evaluations.
    cold_validation = evaluate(cold_agent, start=VALID_BASE + seed*1000, games=validation_games)
    lineage = []
    champions = []
    global_best = None
    parent = None
    parent_config = controls
    try:
        for generation in range(generations):
            generation_candidates = []
            for index in range(population):
                agent_seed = seed * 100_000 + generation * 100 + index
                inherit = parent is not None
                agent, config = breed(parent, parent_config, seed=agent_seed,
                                      mutate=inherit and index != 0)
                # One unmutated elite child protects prior validated behavior.
                # Initial generation diversifies via independent initialization.
                if generation == 0 and index > 0:
                    config = dict(controls)
                    config["lr"] = round(min(0.003, controls["lr"] *
                                             [1.0, 1.4, 0.7, 1.8, 0.5, 2.0, 0.9, 1.1][index]), 8)
                    agent.optimizer.param_groups[0]["lr"] = config["lr"]
                source_hash = fingerprint(parent) if inherit else None
                for episode in range(games_per_candidate):
                    training_seed = TRAIN_BASE + seed*100_000 + generation*1000 + episode
                    train_game(agent, training_seed, config["epsilon_floor"])
                validation = evaluate(agent, start=VALID_BASE + seed*1000,
                                      games=validation_games)
                quality = score_memory(baseline=cold_validation["bricks"],
                                       candidate=validation["bricks"],
                                       samples=validation_games,
                                       evaluation_sha256=fingerprint(validation))
                # File BOTH successes and failures, with immutable quality metadata.
                memory = file_memory(agent.weights(),
                                     accuracy=min(1.0, validation["bricks"]/24.0),
                                     relevance=1.0, provenance=0.5,
                                     sample_count=validation_games)
                if recover_memory(memory) != agent.weights():
                    raise AssertionError("evolutionary offspring weights changed in memory")
                event = {
                    "objective": OBJECTIVE, "iteration": generation*population+index,
                    "generation": generation, "candidate": index,
                    "parent_sha256": source_hash, "mutation": inherit and index != 0,
                    "config": config, "training_games": games_per_candidate,
                    "frames": agent.frames, "updates": agent.updates,
                    "validation": validation, "fitness": validation["bricks"],
                    "quality": quality, "memory": memory
                }
                receipt = journal.append(event)
                note = {
                    "generation": generation, "candidate": index, "config": config,
                    "parent_sha256": source_hash, "mutated": event["mutation"],
                    "fitness": validation["bricks"], "validation": validation,
                    "frames": agent.frames, "updates": agent.updates,
                    "quality_score": quality["score"],
                    "memory_mnemonic": memory["mnemonic"],
                    "memory_sha256": memory["sha256"], "journal_receipt": receipt
                }
                lineage.append(note)
                saved = {"weights": copy.deepcopy(agent.weights()), "config": dict(config),
                         "fitness": validation["bricks"], "generation": generation,
                         "candidate": index, "hash": memory["sha256"]}
                generation_candidates.append(saved)
                if global_best is None or saved["fitness"] > global_best["fitness"]:
                    global_best = saved
            champion = max(generation_candidates, key=lambda c: c["fitness"])
            champions.append({"generation": generation, "candidate": champion["candidate"],
                              "fitness": champion["fitness"], "sha256": champion["hash"]})
            parent = copy.deepcopy(champion["weights"])
            parent_config = dict(champion["config"])
        # Final evaluation is accessed exactly once for each selected final policy.
        evolved, _ = breed(global_best["weights"], global_best["config"],
                           seed=seed, mutate=False)
        # The no-evolution control uses the SAME total number of training games
        # but in one uninterrupted DQN. Frames and updates are reported separately.
        control, _ = breed(None, controls, seed=seed, mutate=False)
        for generation in range(generations):
            for _candidate in range(population):
                for episode in range(games_per_candidate):
                    # Identical environment seed multiset and total game count,
                    # albeit a single control policy sees all episodes serially.
                    training_seed = TRAIN_BASE + seed*100_000 + generation*1000 + episode
                    train_game(control, training_seed, controls["epsilon_floor"])
        final_cold = evaluate(cold_agent, start=HOLDOUT_BASE + seed*1000,
                              games=holdout_games)
        final_control = evaluate(control, start=HOLDOUT_BASE + seed*1000,
                                 games=holdout_games)
        final_evolved = evaluate(evolved, start=HOLDOUT_BASE + seed*1000,
                                 games=holdout_games)
        tip = journal.export()["tip"]
        journal.close()
        reopened = Journal(folder / "evolution.sqlite")
        events = reopened.events(OBJECTIVE)
        if len(events) != generations*population or reopened.export()["tip"] != tip:
            raise AssertionError("BEAN journal not continuous after restart")
        for event in events:
            if not event.get("quality"):
                raise AssertionError("unscored weight memory")
            if fingerprint(recover_memory(event["memory"])) != event["memory"]["sha256"]:
                raise AssertionError("restored weights differ from scored SHA-256 memory")
        reopened.close()
        result = {
            "schema": OBJECTIVE, "seed": seed,
            "protocol": {"population": population, "generations": generations,
                         "games_per_candidate": games_per_candidate,
                         "validation_games": validation_games, "holdout_games": holdout_games,
                         "inputs": "engineered state, not game pixels",
                         "holdout_isolated_from_selection": True,
                         "control_game_budget": generations*population*games_per_candidate},
            "lineage": lineage, "champions": champions,
            "selected": {"generation": global_best["generation"],
                         "candidate": global_best["candidate"],
                         "fitness": global_best["fitness"],
                         "sha256": global_best["hash"]},
            "control_training": {"frames": control.frames, "updates": control.updates},
            "holdout": {"cold": final_cold, "dqn_no_evolution": final_control,
                        "evolved_dqn": final_evolved},
            "gain_over_cold": round(final_evolved["bricks"]-final_cold["bricks"],5),
            "gain_over_single_dqn": round(final_evolved["bricks"]-final_control["bricks"],5),
            "journal_tip": tip,
            "limitations": "Single seed and engineered-state game; neural evolution needs independent"
                           " seeds, budget-aware controls and different environments before claims."
        }
        (folder / "results.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
        return result
    finally:
        try:
            journal.close()
        except Exception:
            pass


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--out", required=True)
    p.add_argument("--seed", type=int, default=41)
    p.add_argument("--population", type=int, default=3)
    p.add_argument("--generations", type=int, default=3)
    p.add_argument("--games", type=int, default=70)
    p.add_argument("--validation", type=int, default=60)
    p.add_argument("--holdout", type=int, default=120)
    a = p.parse_args()
    answer = compete(a.out, seed=a.seed, population=a.population,
                     generations=a.generations, games_per_candidate=a.games,
                     validation_games=a.validation, holdout_games=a.holdout)
    print(json.dumps({"seed": a.seed, "holdout": answer["holdout"],
                      "gain_over_single_dqn": answer["gain_over_single_dqn"]}, indent=2))
