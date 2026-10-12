"""Experimental Deep Q-Network with replay, target network and BEAN scored memory.

Inspired by the 2015 DQN algorithm, but this intentionally consumes BEAN's
three-element engineered Breakout state, NOT raw Atari pixels. PyTorch is an
optional research dependency. Neural weights really train via backpropagation.
Never treat the host-attested quality assessment as independent verification.
"""
from __future__ import annotations

from collections import deque
import copy
import math
import random

import torch
from torch import nn

from bean.memory.compression import file_memory, recover_memory
from bean.optimization.autodev import Journal
from bean.optimization.sponge_td import score_memory

OBJECTIVE = "sponge.dqn.v1"
ACTIONS = ("left", "stay", "right")


def features(state):
    if not isinstance(state, (list, tuple)) or len(state) != 3:
        raise ValueError("expected 3-element Breakout observation")
    if not all(type(x) in (int, float) and math.isfinite(x) for x in state):
        raise ValueError("nonfinite observation")
    return ((float(state[0]) - 7.0) / 7.0, float(state[1]), float(state[2]))


def network():
    return nn.Sequential(nn.Linear(3, 64), nn.ReLU(), nn.Linear(64, 64),
                         nn.ReLU(), nn.Linear(64, len(ACTIONS)))


class SpongeDQN:
    def __init__(self, *, seed=0, gamma=0.99, lr=0.0007,
                 batch_size=32, replay_capacity=20000, warmup=256,
                 learn_every=4, target_sync=300):
        if not 0 <= gamma <= 1 or not 0 < lr <= 1:
            raise ValueError("invalid network optimizer settings")
        if batch_size < 2 or replay_capacity < batch_size or warmup < batch_size:
            raise ValueError("invalid replay budget")
        if learn_every < 1 or target_sync < 1:
            raise ValueError("invalid update cadence")
        self.seed = seed
        self.rng = random.Random(seed)
        # A scoped RNG context avoids resetting other components' torch seeds.
        with torch.random.fork_rng(devices=[]):
            torch.manual_seed(seed)
            self.online = network()
        self.target = network()
        self.target.load_state_dict(self.online.state_dict())
        self.target.eval()
        self.optimizer = torch.optim.Adam(self.online.parameters(), lr=lr)
        self.replay = deque(maxlen=replay_capacity)
        self.gamma = gamma
        self.batch_size = batch_size
        self.warmup = warmup
        self.learn_every = learn_every
        self.target_sync = target_sync
        self.frames = 0
        self.updates = 0
        self.last_loss = None

    def choose(self, state, epsilon=0.0):
        if not 0 <= epsilon <= 1:
            raise ValueError("epsilon outside 0..1")
        obs = features(state)
        if self.rng.random() < epsilon:
            return self.rng.randrange(len(ACTIONS))
        with torch.no_grad():
            values = self.online(torch.tensor([obs], dtype=torch.float32))
            return int(values.argmax(dim=1).item())

    def observe(self, state, action, reward, next_state, done):
        obs = features(state)
        if type(action) is not int or not 0 <= action < len(ACTIONS):
            raise ValueError("invalid action")
        if type(reward) not in (int, float) or not math.isfinite(reward):
            raise ValueError("invalid reward")
        if type(done) is not bool or (not done and next_state is None):
            raise ValueError("invalid transition")
        after = (0.0, 0.0, 0.0) if done else features(next_state)
        self.replay.append((obs, action, float(reward), after, done))
        self.frames += 1
        if len(self.replay) >= self.warmup and self.frames % self.learn_every == 0:
            return self.train_batch()
        return None

    def train_batch(self):
        batch = self.rng.sample(self.replay, self.batch_size)
        states = torch.tensor([b[0] for b in batch], dtype=torch.float32)
        actions = torch.tensor([b[1] for b in batch], dtype=torch.int64).unsqueeze(1)
        rewards = torch.tensor([b[2] for b in batch], dtype=torch.float32)
        next_states = torch.tensor([b[3] for b in batch], dtype=torch.float32)
        nonterminal = torch.tensor([not b[4] for b in batch], dtype=torch.float32)
        values = self.online(states).gather(1, actions).squeeze(1)
        with torch.no_grad():
            future = self.target(next_states).max(dim=1).values
            targets = rewards + self.gamma * future * nonterminal
        loss = nn.functional.smooth_l1_loss(values, targets)
        if not torch.isfinite(loss):
            raise ValueError("nonfinite deep Q loss")
        self.optimizer.zero_grad(set_to_none=True)
        loss.backward()
        nn.utils.clip_grad_norm_(self.online.parameters(), max_norm=10.0)
        self.optimizer.step()
        self.updates += 1
        if self.updates % self.target_sync == 0:
            self.target.load_state_dict(self.online.state_dict())
        self.last_loss = float(loss.detach().item())
        return self.last_loss

    def weights(self):
        return {k: v.detach().cpu().tolist() for k, v in self.online.state_dict().items()}

    def load_weights(self, weights):
        expected = self.online.state_dict()
        if not isinstance(weights, dict) or set(weights) != set(expected):
            raise ValueError("wrong network weights")
        restored = {}
        for name, tensor in expected.items():
            value = torch.tensor(weights[name], dtype=tensor.dtype)
            if value.shape != tensor.shape or not bool(torch.isfinite(value).all()):
                raise ValueError("invalid neural weight dimensions or values")
            restored[name] = value
        self.online.load_state_dict(restored)
        self.target.load_state_dict(self.online.state_dict())

    def learner_state(self):
        """In-memory lineage snapshot; not a published or durable checkpoint."""
        return {
            "online": copy.deepcopy(self.online.state_dict()),
            "target": copy.deepcopy(self.target.state_dict()),
            "optimizer": copy.deepcopy(self.optimizer.state_dict()),
            "replay": list(self.replay),
            "frames": self.frames, "updates": self.updates,
            "rng": self.rng.getstate(),
        }

    def load_learner_state(self, state):
        """Restore replay, optimizer, target and exploration clock together."""
        self.online.load_state_dict(copy.deepcopy(state["online"]))
        self.target.load_state_dict(copy.deepcopy(state["target"]))
        self.optimizer.load_state_dict(copy.deepcopy(state["optimizer"]))
        self.replay.clear()
        self.replay.extend(copy.deepcopy(state["replay"]))
        self.frames = int(state["frames"])
        self.updates = int(state["updates"])
        self.rng.setstate(state["rng"])
        self.last_loss = None

    def checkpoint(self, journal: Journal, *, baseline, candidate,
                   samples, evaluation_sha256, episode):
        # Score first; only after validation can it enter durable memory.
        quality = score_memory(baseline=baseline, candidate=candidate,
                               samples=samples, evaluation_sha256=evaluation_sha256)
        capsule = file_memory(self.weights(),
                              accuracy=max(0.0, min(1.0, float(candidate) / 24.0)),
                              relevance=1.0, provenance=0.5,
                              sample_count=samples)
        prior = journal.events(OBJECTIVE)
        event = {
            "objective": OBJECTIVE, "iteration": len(prior), "episode": episode,
            "architecture": "mlp-3-64-64-3", "algorithm": "DQN-replay-target",
            "frames": self.frames, "updates": self.updates,
            "quality": quality, "weights": capsule
        }
        tip = journal.append(event)
        if recover_memory(capsule) != self.weights():
            raise AssertionError("compressed neural checkpoint did not round-trip")
        return {"journal_tip": tip, "mnemonic": capsule["mnemonic"],
                "sha256": capsule["sha256"], "quality": quality,
                "capsule_score": capsule["score"]["value"]}

    @staticmethod
    def recover_latest(journal: Journal, *, seed=0):
        rows = journal.events(OBJECTIVE)
        if not rows:
            raise ValueError("no deep learning checkpoints")
        row = rows[-1]
        if row.get("architecture") != "mlp-3-64-64-3":
            raise ValueError("incompatible checkpoint architecture")
        learner = SpongeDQN(seed=seed)
        learner.load_weights(recover_memory(row["weights"]))
        return learner
