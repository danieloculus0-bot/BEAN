"""Preregistered, training-only seed-66 numerical reproducibility probe.

Never evaluates validation or holdout environments. No adaptive tuning.
"""
from __future__ import annotations

import argparse
import json
import os
import platform
from pathlib import Path
import subprocess
import sys

import torch

from .evolve import TRAIN_BASE, breed, fingerprint, train_game

EXPECTED_BLOBS = {
    "experiments/sponge_breakout/evolve.py": "c4ec948dce71a6f00c51efcf032493e8a83435fa",
    "bean/optimization/sponge_dqn.py": "769da37ac2e13566ddc0d83c770d7323cbfc0da7",
    "experiments/sponge_breakout/test_evolve.py": "c24a3f7b2ad3166e52da63726c5aa0ddf21671ae",
}


def probe(out: Path):
    out.mkdir(parents=True, exist_ok=False)
    observed_blobs = {}
    for path, expected in EXPECTED_BLOBS.items():
        actual = subprocess.check_output(
            ["git", "rev-parse", "HEAD:" + path], text=True
        ).strip()
        if actual != expected:
            raise RuntimeError(f"source drift: {path} {actual} != {expected}")
        observed_blobs[path] = actual
    source_sha = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], text=True
    ).strip()
    torch.set_num_threads(1)
    seed = 66
    config = {"lr": 0.0007, "gamma": 0.99, "epsilon_floor": 0.06}
    agent, _ = breed(None, config, seed=seed * 100_000, mutate=False)
    trajectory = []
    for episode in range(30):
        training_seed = TRAIN_BASE + seed * 100_000 + episode
        train_game(agent, training_seed, config["epsilon_floor"], shaped=True)
        if (episode + 1) % 5 == 0:
            trajectory.append({
                "episodes": episode + 1,
                "frames": agent.frames,
                "updates": agent.updates,
                "weights_sha256": fingerprint(agent.weights()),
                "last_loss": agent.last_loss,
            })
    result = {
        "schema": "bean.seed66.numeric-repro.v1",
        "preregistered": True,
        "training_only": True,
        "seed": seed,
        "generation": 0,
        "candidate": 0,
        "games": 30,
        "source_commit": source_sha,
        "learner_blobs": observed_blobs,
        "torch_version": torch.__version__,
        "python_version": sys.version,
        "platform": platform.platform(),
        "processor": platform.processor(),
        "cpu_count": os.cpu_count(),
        "torch_num_threads": torch.get_num_threads(),
        "frames": agent.frames,
        "updates": agent.updates,
        "final_weights_sha256": fingerprint(agent.weights()),
        "trajectory": trajectory,
    }
    (out / "probe.json").write_text(
        json.dumps(result, sort_keys=True, indent=2), encoding="utf-8"
    )
    print(json.dumps(result, sort_keys=True, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    probe(args.out)
