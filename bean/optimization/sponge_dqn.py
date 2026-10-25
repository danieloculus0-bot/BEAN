"""BEAN's existing experimental DQN, extended for named observation/action domains.

Ported from BEAN 2eb05f655cbefce888fc38316a24cfb52b571deb. The original
replay/target-network/Huber-loss/Adam update is retained. New checkpoints retain
optimizer, target network, replay and RNG as well as learned online weights.
The default encoder remains the original engineered Breakout encoder.
"""
from __future__ import annotations

from collections import deque
import math
import random
import hashlib
import json

import torch
from torch import nn

from bean.optimization.autodev import Journal
from bean.optimization.sponge_td import score_memory
from bean.optimization.sponge_codec import pack, unpack

OBJECTIVE = "sponge.dqn.domain.v2"
ACTIONS = ("left", "stay", "right")


def features(state):
    if not isinstance(state, (list, tuple)) or len(state) != 3:
        raise ValueError("expected 3-element Breakout observation")
    if not all(type(x) in (int, float) and math.isfinite(x) for x in state):
        raise ValueError("nonfinite observation")
    return ((float(state[0]) - 7.0) / 7.0, float(state[1]), float(state[2]))


def network(observation_size=3, action_count=3):
    return nn.Sequential(nn.Linear(observation_size, 64), nn.ReLU(), nn.Linear(64, 64),
                         nn.ReLU(), nn.Linear(64, action_count))


def _encode(value):
    if isinstance(value, torch.Tensor):
        return {"tensor":value.detach().cpu().tolist(),"dtype":str(value.dtype).split(".")[-1]}
    if isinstance(value,dict):return {"mapping":[[_encode(k),_encode(v)] for k,v in value.items()]}
    if isinstance(value,tuple):return {"tuple":[_encode(v) for v in value]}
    if isinstance(value,list):return [_encode(v) for v in value]
    return value


def _decode(value):
    if isinstance(value,list):return [_decode(v) for v in value]
    if isinstance(value,dict):
        if set(value)=={"tensor","dtype"}:
            if value["dtype"] not in ("float32","float64","int64","int32","bool"):raise ValueError("Unsupported stored tensor dtype")
            tensor=torch.tensor(value["tensor"],dtype=getattr(torch,value["dtype"]))
            if not bool(torch.isfinite(tensor).all()):raise ValueError("Nonfinite optimizer state")
            return tensor
        if set(value)=={"tuple"}:return tuple(_decode(v) for v in value["tuple"])
        if set(value)=={"mapping"}:return {_decode(k):_decode(v) for k,v in value["mapping"]}
        raise ValueError("Unknown stored training-state type")
    return value


class SpongeDQN:
    def __init__(self, *, seed=0, gamma=0.99, lr=0.0007,
                 batch_size=32, replay_capacity=20000, warmup=256,
                 learn_every=4, target_sync=300, observation_size=None,
                 actions=ACTIONS, domain="breakout"):
        if not 0 <= gamma <= 1 or not 0 < lr <= 1:
            raise ValueError("invalid network optimizer settings")
        if batch_size < 2 or replay_capacity < batch_size or warmup < batch_size:
            raise ValueError("invalid replay budget")
        if learn_every < 1 or target_sync < 1:
            raise ValueError("invalid update cadence")
        if observation_size is not None and (type(observation_size) is not int or not 1<=observation_size<=256):raise ValueError("Invalid observation size")
        if not actions or len(set(actions))!=len(actions) or not all(isinstance(x,str) and x for x in actions):raise ValueError("Invalid action names")
        if not isinstance(domain,str) or not domain:raise ValueError("Domain required")
        self.actions=tuple(actions)
        self.observation_size=observation_size
        self.domain=domain
        self.config=dict(seed=seed,gamma=gamma,lr=lr,batch_size=batch_size,replay_capacity=replay_capacity,warmup=warmup,learn_every=learn_every,target_sync=target_sync,observation_size=observation_size,actions=list(actions),domain=domain)
        self.seed = seed
        self.rng = random.Random(seed)
        # A scoped RNG context avoids resetting other components' torch seeds.
        with torch.random.fork_rng(devices=[]):
            torch.manual_seed(seed)
            self.online = network(observation_size or 3,len(actions))
            self.target = network(observation_size or 3,len(actions))
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

    def encode(self,state):
        if self.observation_size is None:return features(state)
        if not isinstance(state,(list,tuple)) or len(state)!=self.observation_size:raise ValueError("Wrong observation dimensions")
        if not all(type(x) in (int,float) and math.isfinite(x) for x in state):raise ValueError("Nonfinite observation")
        return tuple(float(x) for x in state)

    def choose(self, state, epsilon=0.0):
        if not 0 <= epsilon <= 1:
            raise ValueError("epsilon outside 0..1")
        obs = self.encode(state)
        if self.rng.random() < epsilon:
            return self.rng.randrange(len(self.actions))
        with torch.no_grad():
            values = self.online(torch.tensor([obs], dtype=torch.float32))
            return int(values.argmax(dim=1).item())

    def observe(self, state, action, reward, next_state, done):
        obs = self.encode(state)
        if type(action) is not int or not 0 <= action < len(self.actions):
            raise ValueError("invalid action")
        if type(reward) not in (int, float) or not math.isfinite(reward):
            raise ValueError("invalid reward")
        if type(done) is not bool or (not done and next_state is None):
            raise ValueError("invalid transition")
        after = (0.0,) * (self.observation_size or 3) if done else self.encode(next_state)
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

    def training_state(self):
        return {"schema":"bean.dqn.training_state.v2","config":self.config,
                "online":self.weights(),"target":{k:v.detach().cpu().tolist() for k,v in self.target.state_dict().items()},
                "optimizer":_encode(self.optimizer.state_dict()),"replay":_encode(list(self.replay)),
                "rng":_encode(self.rng.getstate()),"frames":self.frames,"updates":self.updates,"last_loss":self.last_loss}

    def weights_digest(self):
        return hashlib.sha256(json.dumps(self.weights(),sort_keys=True,separators=(",",":"),allow_nan=False).encode()).hexdigest()

    @classmethod
    def from_training_state(cls,state):
        if state.get("schema")!="bean.dqn.training_state.v2":raise ValueError("Unknown training checkpoint")
        model=cls(**state["config"])
        model.load_weights(state["online"])
        target={k:torch.tensor(v,dtype=model.target.state_dict()[k].dtype) for k,v in state["target"].items()}
        if any(v.shape!=model.target.state_dict()[k].shape or not bool(torch.isfinite(v).all()) for k,v in target.items()):raise ValueError("Invalid target network")
        model.target.load_state_dict(target)
        model.optimizer.load_state_dict(_decode(state["optimizer"]))
        model.replay=deque(_decode(state["replay"]),maxlen=state["config"]["replay_capacity"])
        model.rng.setstate(_decode(state["rng"]))
        model.frames=state["frames"];model.updates=state["updates"];model.last_loss=state["last_loss"]
        return model

    def checkpoint(self, journal: Journal, *, baseline, candidate,
                   samples, evaluation_sha256, episode, metadata=None):
        # Score first; only after validation can it enter durable memory.
        quality = score_memory(baseline=baseline, candidate=candidate,
                               samples=samples, evaluation_sha256=evaluation_sha256)
        capsule = pack(self.training_state())
        prior = journal.events(OBJECTIVE)
        event = {
            "objective": OBJECTIVE, "iteration": len(prior), "episode": episode,
            "architecture":f"mlp-{self.observation_size or 3}-64-64-{len(self.actions)}", "algorithm": "DQN-replay-target",
            "frames": self.frames, "updates": self.updates,
            "quality": quality, "training_state": capsule,"metadata":metadata or {},
            "online_weights_sha256":self.weights_digest(),"domain":self.domain
        }
        tip = journal.append(event)
        if unpack(capsule) != self.training_state():
            raise AssertionError("compressed neural checkpoint did not round-trip")
        return {"journal_tip": tip, "mnemonic": capsule["mnemonic"],
                "sha256": capsule["sha256"], "quality": quality,
                "capsule_score": quality["score"],"online_weights_sha256":self.weights_digest()}

    @staticmethod
    def recover_latest(journal: Journal, *, seed=0):
        rows = journal.events(OBJECTIVE)
        if not rows:
            raise ValueError("no deep learning checkpoints")
        row = rows[-1]
        learner=SpongeDQN.from_training_state(unpack(row["training_state"]))
        if learner.weights_digest()!=row["online_weights_sha256"]:raise ValueError("Restored weights differ")
        return learner
