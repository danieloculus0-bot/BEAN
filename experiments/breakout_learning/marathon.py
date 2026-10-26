"""BEAN Breakout marathon: teach, test, retain, resume, and stop on a real blind win.

The old Breakout benchmark remains exactly 1000 frames. This challenge uses
5000 frames so clearing all 24 bricks is physically possible.

Guided imitation of a simple tested paddle-tracking rule is explicit. The
teacher is never consulted by the neural policy during evaluation, and the
result must be independently demonstrated on new seeds.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
from pathlib import Path

import torch
from torch.nn import functional as F

from bean.optimization.autodev import Journal
from bean.optimization.sponge_dqn import SpongeDQN, features
from .game import Breakout

OBJECTIVE = "breakout.marathon.v1"
MAX_FRAMES = 5000
TARGET_BRICKS = 24
VALIDATION_SEEDS = tuple(range(650000, 650020))


def teaching_action(state):
    """Proven basic idea: move toward the projected ball interception."""
    bucket = state[0]
    return 0 if bucket < 7 else (2 if bucket > 7 else 1)


def demonstrate(learner, updates=250):
    """Real PyTorch supervised weight updates; no hardcoded inference actions."""
    if updates < 1:
        raise ValueError("Need at least one demonstration update")
    samples = [(b, vx, vy) for b in range(15) for vx in (0, 1) for vy in (0, 1)]
    inputs = torch.tensor([features(state) for state in samples], dtype=torch.float32)
    labels = torch.tensor([teaching_action(state) for state in samples], dtype=torch.long)
    for _ in range(updates):
        learner.optimizer.zero_grad(set_to_none=True)
        loss = F.cross_entropy(learner.online(inputs), labels)
        loss.backward()
        learner.optimizer.step()
    learner.target.load_state_dict(learner.online.state_dict())
    with torch.no_grad():
        fidelity = float((learner.online(inputs).argmax(1) == labels).float().mean())
    return {"source": "explicit_projected_interception_rule",
            "method": "supervised_neural_imitation",
            "optimizer_steps": updates, "demonstration_fidelity": round(fidelity, 4),
            "teacher_actions_used_at_inference": False}


def evaluate(learner, seeds):
    results = []
    for seed in seeds:
        env = Breakout(seed, max_steps=MAX_FRAMES)
        played = env.play(lambda state: learner.choose(state, epsilon=0.0))
        results.append({"seed": seed, **played})
    winners = [r for r in results if r["won"] == 1 and r["bricks"] == TARGET_BRICKS]
    return {
        "games": len(results),
        "wins": len(winners),
        "win_rate_percent": round(100 * len(winners) / len(results), 2),
        "mean_bricks": round(sum(x["bricks"] for x in results) / len(results), 4),
        "mean_frames": round(sum(x["frames"] for x in results) / len(results), 2),
        "first_win": winners[0] if winners else None,
        "max_bricks": max(x["bricks"] for x in results),
    }


def rank(metrics):
    return (metrics["wins"], metrics["mean_bricks"],
            metrics["win_rate_percent"], metrics["mean_frames"])


def state_bytes(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"),
                      allow_nan=False).encode("utf-8")


def save_resume(root, *, learner, episode, cycle, selected, demonstration, journal_tip):
    obj = {
        "schema": "bean.breakout.marathon.resume.v1",
        "episode": episode, "cycle": cycle, "selected": selected,
        "demonstration": demonstration, "journal_tip": journal_tip,
        "network": learner.training_state(),
        "network_sha256": learner.weights_digest(),
    }
    payload = state_bytes(obj)
    path = root / "resume.json.gz"
    with gzip.open(path, "wb", compresslevel=6) as fp:
        fp.write(payload)
    (root / "resume.sha256").write_text(hashlib.sha256(payload).hexdigest() + "\n")


def load_resume(root):
    state = root / "resume.json.gz"
    digest = root / "resume.sha256"
    if not state.exists():
        if digest.exists():
            raise ValueError("Resume digest without saved state")
        return None
    if not digest.exists():
        raise ValueError("Missing resume checksum")
    with gzip.open(state, "rb") as fp:
        payload = fp.read()
    if hashlib.sha256(payload).hexdigest() != digest.read_text().strip():
        raise ValueError("Tampered or damaged BEAN marathon state")
    obj = json.loads(payload)
    if obj.get("schema") != "bean.breakout.marathon.resume.v1":
        raise ValueError("Unknown marathon state")
    learner = SpongeDQN.from_training_state(obj["network"])
    if learner.weights_digest() != obj["network_sha256"]:
        raise ValueError("Restored neural weights do not match saved state")
    return learner, obj


def run(root=Path("breakout-marathon-state"), *, episode_budget=40,
        demonstration_updates=250, validation_seeds=VALIDATION_SEEDS):
    if episode_budget < 1:
        raise ValueError("episode_budget must be positive")
    torch.set_num_threads(1)
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    saved = load_resume(root)
    if saved:
        learner, prior = saved
        cycle = prior["cycle"] + 1
        episode_start = prior["episode"]
        demonstration = prior["demonstration"]
        incumbent_metrics = evaluate(learner, validation_seeds)
    else:
        learner = SpongeDQN(seed=20261025, domain="breakout-marathon",
                           batch_size=32, replay_capacity=12000, warmup=256,
                           learn_every=4, target_sync=300, lr=0.0007, gamma=0.99)
        cycle, episode_start = 1, 0
        demonstration = demonstrate(learner, updates=demonstration_updates)
        incumbent_metrics = evaluate(learner, validation_seeds)

    champion = learner.training_state()
    best_metrics = incumbent_metrics
    best_stage = "recovered_or_demonstrated"
    training_wins = 0
    # Don't waste another chunk if a genuine blind win has already happened.
    # Every cycle draws previously unseen final seeds, never development seeds.
    for local_episode in range(1, episode_budget + 1):
        index = episode_start + local_episode
        env = Breakout(960000 + index, max_steps=MAX_FRAMES)
        epsilon = max(0.03, 0.18 * (0.999 ** index))
        while not env.done:
            state = env.state()
            action = learner.choose(state, epsilon=epsilon)
            reward = env.step(action)
            learner.observe(state, action, reward, env.state(), bool(env.done))
        training_wins += int(not env.bricks and not env.miss)
        if local_episode % 10 == 0 or local_episode == episode_budget:
            candidate_metrics = evaluate(learner, validation_seeds)
            if rank(candidate_metrics) > rank(best_metrics):
                champion = learner.training_state()
                best_metrics = candidate_metrics
                best_stage = "reinforcement"
    # Final evaluation uses distinct, never-trained seeds. Do NOT select using it.
    restored = SpongeDQN.from_training_state(champion)
    assert restored.weights_digest() == hashlib.sha256(
        json.dumps(restored.weights(), sort_keys=True, separators=(",", ":"),
                   allow_nan=False).encode()).hexdigest()
    final_seeds = range(800000 + cycle * 100, 800000 + cycle * 100 + 40)
    holdout = evaluate(restored, final_seeds)
    won = bool(holdout["wins"])
    total_episodes = episode_start + episode_budget
    journal = Journal(root / "marathon-ledger.sqlite3")
    event = {
        "objective": OBJECTIVE, "iteration": len(journal.events(OBJECTIVE)),
        "cycle": cycle, "total_episodes": total_episodes,
        "game":"breakout", "max_frames":MAX_FRAMES, "target_bricks":TARGET_BRICKS,
        "demonstration":demonstration, "best_stage":best_stage,
        "development":best_metrics, "holdout":holdout,
        "training_wins":training_wins,
        "learner_gradient_updates":learner.updates,
        "frozen_weight_sha256":restored.weights_digest(),
        "raw_final_gradient_weight_sha256":learner.weights_digest(),
        "win_proven":won, "unseen_seeds_used_for_selection":False,
    }
    tip = journal.append(event)
    journal.close()
    save_resume(root, learner=restored, episode=total_episodes, cycle=cycle,
                selected=best_metrics, demonstration=demonstration,
                journal_tip=tip)
    recovered = load_resume(root)
    if recovered[0].weights_digest() != restored.weights_digest():
        raise AssertionError("Marathon neural policy did not survive restart")
    report = {
        "status":"won" if won else "continue", "cycle":cycle,
        "total_training_episodes":total_episodes, "teacher":demonstration,
        "development":best_metrics, "best_stage":best_stage,
        "fresh_blind_holdout":holdout,
        "real_win_on_unseen_seed": won,
        "stop_condition": "at least one full 24-brick clearance on a new seed",
        "policy_weight_sha256":restored.weights_digest(),
        "checkpoint_recovery_verified":True,
        "ledger_sha256_tip":tip,
        "limitation":"The initial neural learner imitates an explicitly supplied basic tracking strategy before RL. A neural policy winning is real, but this does not show autonomous discovery of the rule or transfer of earlier BEAN abstract lessons.",
    }
    (root / "results.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2), flush=True)
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("breakout-marathon-state"))
    parser.add_argument("--episodes", type=int, default=40)
    parser.add_argument("--demonstration-updates", type=int, default=250)
    args = parser.parse_args()
    run(args.root, episode_budget=args.episodes,
        demonstration_updates=args.demonstration_updates)
