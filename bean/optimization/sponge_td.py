"""BEAN Sponge: temporal-difference Q-learning with scored, SHA-verified memories.

A Q-learning policy trains in memory. Before durable filing, the caller must
supply validation measurements from an independent evaluation harness. Sponge
calculates the score and attaches it to a compressed SHA-256 checkpoint in the
existing hash-chained BEAN Journal. Host-provided measurements are not
independently authenticated by this module.
"""
from __future__ import annotations

import hashlib
import json
import math
import random

from bean.optimization.autodev import Journal
from bean.optimization.sponge_codec import pack, unpack

OBJECTIVE = "sponge.td.v1"


def _finite(value):
    return type(value) in (int, float) and math.isfinite(value)


def score_memory(*, baseline, candidate, samples, evaluation_sha256):
    """Pre-file quality score: bounded gain and validation sample count.

    This is a deterministic host-attested score, NOT statistically verified
    improvement. The holdout grader must remain a separate process.
    """
    if not all(_finite(x) for x in (baseline, candidate)):
        raise ValueError("nonfinite validation scores")
    if type(samples) is not int or samples < 30:
        raise ValueError("at least 30 evaluation episodes required")
    if (not isinstance(evaluation_sha256, str) or len(evaluation_sha256) != 64
            or any(c not in "0123456789abcdef" for c in evaluation_sha256)):
        raise ValueError("missing evaluation receipt sha256")
    # Bounded relative gain; prevents tiny baselines and extreme values
    # from inflating the assigned score beyond 100.
    gain = (candidate - baseline) / max(abs(baseline), 1.0)
    performance = max(0.0, min(1.0, 0.5 + 0.5 * gain))
    evidence = min(1.0, samples / 200.0)
    score = round(100 * (0.8 * performance + 0.2 * evidence), 2)
    return {"score": score, "delta": round(candidate - baseline, 6),
            "sample_count": samples, "receipt_sha256": evaluation_sha256,
            "promotable": score >= 60 and candidate > baseline,
            "verification": "host_attested_not_independently_verified"}


class SpongeTD:
    """Online one-step Q-learning, durable *scored* checkpoint restoration."""

    def __init__(self, path, actions=("left", "stay", "right"), *,
                 alpha=.23, gamma=.975, epsilon=.1, seed=0):
        if not actions or len(set(actions)) != len(actions) or not all(
                isinstance(a, str) and a for a in actions):
            raise ValueError("invalid action set")
        if not (0 < alpha <= 1 and 0 <= gamma <= 1 and 0 <= epsilon <= 1):
            raise ValueError("invalid learner parameters")
        self.actions = tuple(actions)
        self.alpha, self.gamma, self.epsilon = alpha, gamma, epsilon
        self.rng = random.Random(seed)
        self.journal = Journal(path)
        self.q = {}
        self.steps = 0
        rows = self.journal.events(OBJECTIVE)
        self.checkpoints = len(rows)
        if rows:
            row = rows[-1]
            if (tuple(row["actions"]) != self.actions or
                row["alpha"] != alpha or row["gamma"] != gamma):
                raise ValueError("saved policy configuration mismatch")
            if not isinstance(row.get("quality"), dict):
                raise ValueError("unscored historical memory is not eligible")
            self.q = unpack(row["memory"])
            for values in self.q.values():
                if (not isinstance(values, list) or len(values) != len(self.actions)
                        or not all(_finite(x) for x in values)):
                    raise ValueError("invalid restored Q values")
            self.steps = row["steps"]

    @staticmethod
    def key(state):
        return json.dumps(state, sort_keys=True, separators=(",", ":"), allow_nan=False)

    def values(self, state):
        return self.q.setdefault(self.key(state), [0.0] * len(self.actions))

    def choose(self, state, *, explore=True):
        if explore and self.rng.random() < self.epsilon:
            return self.rng.randrange(len(self.actions))
        # Choosing from a frozen policy must not insert unseen zero-valued
        # states. Inference and learning have separate mutation semantics.
        values = self.q.get(self.key(state), [0.0] * len(self.actions))
        return max(range(len(values)), key=lambda i: values[i])

    def learn(self, state, action, reward, next_state, done):
        if (type(action) is not int or not 0 <= action < len(self.actions)
                or type(done) is not bool or not _finite(reward)
                or not -1e12 < reward < 1e12):
            raise ValueError("invalid transition")
        if not done and next_state is None:
            raise ValueError("nonterminal transition requires next state")
        current = self.values(state)
        # Read next state's value BEFORE updating the current action.
        future = 0.0 if done else max(self.values(next_state))
        target = reward + self.gamma * future
        updated = current[action] + self.alpha * (target - current[action])
        if not math.isfinite(updated):
            raise ValueError("nonfinite learning update")
        current[action] = updated
        self.steps += 1

    def checkpoint(self, *, baseline, candidate, samples, evaluation_sha256):
        # Score BEFORE writing anything. An invalid assessment is never filed.
        quality = score_memory(baseline=baseline, candidate=candidate,
                               samples=samples, evaluation_sha256=evaluation_sha256)
        memory = pack(self.q)
        event = {"objective": OBJECTIVE, "iteration": self.checkpoints,
                 "actions": list(self.actions), "alpha": self.alpha,
                 "gamma": self.gamma, "steps": self.steps,
                 "quality": quality, "memory": memory}
        tip = self.journal.append(event)
        self.checkpoints += 1
        return {"journal_tip": tip, "memory_mnemonic": memory["mnemonic"],
                "memory_sha256": memory["sha256"], **quality}

    def close(self):
        self.journal.close()
