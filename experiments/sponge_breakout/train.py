"""Run BEAN's real SpongeTD against Breakout with segregated evaluation seeds.

Run: python -m experiments.sponge_breakout.train --episodes 3000 --out sponge-breakout
Requires only BEAN Core standard library. No model/provider or trading credentials.
"""
import argparse
import hashlib
import json
from pathlib import Path
from statistics import mean
from bean.optimization.sponge_td import SpongeTD
from .game import Breakout

TRAIN_OFFSET = 900000
VALID_OFFSET = 18000
HOLDOUT_OFFSET = 21000
STEPS = (0, 500, 1000, 1500, 2000, 2500, 3000)

def evaluate(policy, start, n):
    output = []
    for seed in range(start, start + n):
        env = Breakout(seed)
        output.append(env.play(lambda state: max(range(3), key=lambda a: policy.get(json.dumps(state, separators=(",", ":")), [0.0] * 3)[a])))
    return {"bricks": round(mean(x["bricks"] for x in output), 4),
            "survival": round(mean(x["survived"] for x in output), 4),
            "games": n}

def digest_metrics(metrics):
    return hashlib.sha256(json.dumps(metrics, sort_keys=True, separators=(",", ":")).encode()).hexdigest()

def run(out, episodes=3000):
    if episodes != 3000:
        raise ValueError("First preregistered protocol uses 3000 episodes")
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    if any(out.iterdir()):
        raise ValueError("output must start empty")
    learner = SpongeTD(out / "learning.sqlite", epsilon=.1, seed=20261011)
    checkpoints = []
    best_score = float("-inf")
    best_snapshot = {}
    baseline_policy = {}
    baseline = evaluate(baseline_policy, VALID_OFFSET, 200)
    for episode in range(episodes + 1):
        if episode in STEPS:
            validation = evaluate(learner.q, VALID_OFFSET, 200)
            receipt = learner.checkpoint(baseline=baseline["bricks"], candidate=validation["bricks"],
                                         samples=200, evaluation_sha256=digest_metrics(validation))
            if validation["bricks"] > best_score:
                best_score = validation["bricks"]
                best_snapshot = {k:list(v) for k,v in learner.q.items()}
                best_episode = episode
            checkpoints.append({"episode":episode,"validation":validation,"receipt":receipt})
        if episode == episodes:
            break
        env = Breakout(TRAIN_OFFSET + episode)
        while not env.done:
            state = env.state()
            action = learner.choose(state)
            reward = env.step(action)
            learner.learn(state, action, reward, None if env.done else env.state(), env.done)
    journal_tip = learner.journal.export()["tip"]
    learner.close()
    recovered = SpongeTD(out / "learning.sqlite", epsilon=.1, seed=20261011)
    if recovered.journal.export()["tip"] != journal_tip or recovered.checkpoints != len(STEPS):
        raise AssertionError("BEAN learning journal failed restart check")
    recovered.close()
    result = {
        "schema":"bean.sponge.breakout.v1",
        "training_games":episodes,"validation_games":200,"holdout_games":200,
        "checkpoint_selection":"best validation score only, holdout never seen during selection",
        "checkpoints":checkpoints,"selected_episode":best_episode,
        "holdout":{"cold":evaluate(baseline_policy,HOLDOUT_OFFSET,200),
                   "selected":evaluate(best_snapshot,HOLDOUT_OFFSET,200)},
        "journal_tip":journal_tip,
        "limits":"Single training seed and simple environment; same-game improvement only; not general cognitive transfer."
    }
    result["holdout_delta"] = round(result["holdout"]["selected"]["bricks"]-result["holdout"]["cold"]["bricks"],4)
    (out/"results.json").write_text(json.dumps(result,indent=2))
    return result

if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--out",default="sponge-breakout")
    parser.add_argument("--episodes",type=int,default=3000)
    args=parser.parse_args()
    summary=run(args.out,args.episodes)
    print(json.dumps({"holdout":summary["holdout"],"delta":summary["holdout_delta"],"selected_episode":summary["selected_episode"]},indent=2))
