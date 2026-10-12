"""BEAN Sponge: journal-backed contextual action-value learning.

This is a bounded contextual-bandit learner, not an LLM-weight trainer.
It learns action rewards per context, persists each observation in BEAN's
hash-chained Journal, and reconstructs policy from verified history.
"""
from __future__ import annotations

import hashlib
import json
import random
from pathlib import Path

from bean.optimization.autodev import Journal

OBJECTIVE = "sponge.v1"


class Sponge:
    def __init__(self, path: str | Path, actions: tuple[str, ...], *, alpha: float = 0.2, epsilon: float = 0.1, seed: int = 0):
        if not actions or len(set(actions)) != len(actions) or not all(isinstance(a, str) and a for a in actions):
            raise ValueError("actions must be unique nonempty strings")
        if not (0 < alpha <= 1 and 0 <= epsilon <= 1):
            raise ValueError("invalid alpha/epsilon")
        self.actions = tuple(actions)
        self.alpha = alpha
        self.epsilon = epsilon
        self.rng = random.Random(seed)
        self.journal = Journal(path)
        self.q: dict[tuple[str, str], float] = {}
        self.count = 0
        try:
            for event in self.journal.events(OBJECTIVE):
                if tuple(event["actions"]) != self.actions or event["alpha"] != alpha:
                    raise ValueError("policy configuration differs from persisted history")
                self._apply(event["context"], event["action"], event["reward"])
                self.count += 1
        except BaseException:
            # Initialization failed. Release the SQLite file immediately,
            # including on Windows, where open handles block temp-file deletion.
            self.journal.close()
            raise

    @staticmethod
    def context_key(context: object) -> str:
        serialized = json.dumps(context, sort_keys=True, separators=(",", ":"), allow_nan=False)
        return hashlib.sha256(serialized.encode()).hexdigest()

    def choose(self, context: object, *, explore: bool = True) -> str:
        key = self.context_key(context)
        if explore and self.rng.random() < self.epsilon:
            return self.rng.choice(self.actions)
        # Stable, documented deterministic tie-breaking.
        return max(self.actions, key=lambda a: self.q.get((key, a), 0.0))

    def _apply(self, key: str, action: str, reward: float) -> None:
        old = self.q.get((key, action), 0.0)
        self.q[(key, action)] = old + self.alpha * (reward - old)

    def observe(self, context: object, action: str, reward: float) -> str:
        if action not in self.actions or not isinstance(reward, (int, float)):
            raise ValueError("invalid action or reward")
        reward = float(reward)
        if not (-1e12 < reward < 1e12):
            raise ValueError("nonfinite or excessive reward")
        key = self.context_key(context)
        event = {"objective": OBJECTIVE, "iteration": self.count, "actions": list(self.actions),
                 "alpha": self.alpha, "context": key, "action": action, "reward": reward}
        tip = self.journal.append(event)
        self._apply(key, action, reward)
        self.count += 1
        return tip

    def close(self):
        self.journal.close()
