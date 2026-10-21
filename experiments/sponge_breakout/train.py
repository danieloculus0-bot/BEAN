"""Run BEAN's real SpongeTD against Breakout with segregated evaluation seeds.

Run: python -m experiments.sponge_breakout.train --episodes 3000 --out sponge-breakout
Requires only BEAN Core standard library. No model/provider or trading credentials.
"""
import argparse
import hashlib
import json
from pathlib import Path
from statistics import mean
from .ledger import append_result
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

def run(out, episodes=3000, *, train_offset=TRAIN_OFFSET,
        validation_offset=VALID_OFFSET, holdout_offset=HOLDOUT_OFFSET,
        learner_seed=20261011, run_key="original", ledger_path=None):
    if episodes != 3000:
        raise ValueError("First preregistered protocol uses 3000 episodes")
    if not isinstance(run_key, str) or not run_key or len(run_key) > 80:
        raise ValueError("invalid run key")
    if any(type(x) is not int or x < 0 for x in
           (train_offset, validation_offset, holdout_offset, learner_seed)):
        raise ValueError("seed offsets and learner seed must be nonnegative integers")
    windows = [(train_offset, train_offset + episodes),
               (validation_offset, validation_offset + 200),
               (holdout_offset, holdout_offset + 200)]
    if any(a < d and c < b for i, (a, b) in enumerate(windows)
           for c, d in windows[i + 1:]):
        raise ValueError("training/validation/holdout seed windows must be disjoint")
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    if any(out.iterdir()):
        raise ValueError("output must start empty")
    learner = SpongeTD(out / "learning.sqlite", epsilon=.1, seed=learner_seed)
    checkpoints = []
    best_score = float("-inf")
    best_snapshot = {}
    baseline_policy = {}
    baseline = evaluate(baseline_policy, validation_offset, 200)
    for episode in range(episodes + 1):
        if episode in STEPS:
            validation = evaluate(learner.q, validation_offset, 200)
            receipt = learner.checkpoint(baseline=baseline["bricks"], candidate=validation["bricks"],
                                         samples=200, evaluation_sha256=digest_metrics(validation))
            if validation["bricks"] > best_score:
                best_score = validation["bricks"]
                best_snapshot = {k:list(v) for k,v in learner.q.items()}
                best_episode = episode
            checkpoints.append({"episode":episode,"validation":validation,"receipt":receipt})
        if episode == episodes:
            break
        env = Breakout(train_offset + episode)
        while not env.done:
            state = env.state()
            action = learner.choose(state)
            reward = env.step(action)
            learner.learn(state, action, reward, None if env.done else env.state(), env.done)
    journal_tip = learner.journal.export()["tip"]
    learner.close()
    recovered = SpongeTD(out / "learning.sqlite", epsilon=.1, seed=learner_seed)
    if recovered.journal.export()["tip"] != journal_tip or recovered.checkpoints != len(STEPS):
        raise AssertionError("BEAN learning journal failed restart check")
    recovered.close()
    result = {
        "schema":"bean.sponge.breakout.v1",
        "run_key": run_key,
        "protocol": {"training_games": episodes, "train_offset": train_offset,
                     "validation_offset": validation_offset,
                     "holdout_offset": holdout_offset, "learner_seed": learner_seed,
                     "selection": "best of seven checkpoints on 200 validation games"},
        "source_digests": {
            "game_py": hashlib.sha256((Path(__file__).parent / "game.py").read_bytes()).hexdigest(),
            "sponge_td_py": hashlib.sha256((Path(__file__).resolve().parents[2] /
                                          "bean/optimization/sponge_td.py").read_bytes()).hexdigest(),
        },
        "training_games":episodes,"validation_games":200,"holdout_games":200,
        "checkpoint_selection":"best validation score only, holdout never seen during selection",
        "checkpoints":checkpoints,"selected_episode":best_episode,
        "holdout":{"cold":evaluate(baseline_policy,holdout_offset,200),
                   "selected":evaluate(best_snapshot,holdout_offset,200)},
        "journal_tip":journal_tip,
        "limits":"Single training seed and simple environment; same-game improvement only; not general cognitive transfer."
    }
    result["holdout_delta"] = round(result["holdout"]["selected"]["bricks"]-result["holdout"]["cold"]["bricks"],4)
    (out/"results.json").write_text(json.dumps(result,indent=2,sort_keys=True) + "\n",
                                   encoding="utf-8")
    if ledger_path is not None:
        receipt = append_result(ledger_path, result)
        result["ledger_entry_sha256"] = receipt["entry_sha256"]
        # Save explicit receipt identity into the per-run JSON as well.
        (out/"results.json").write_text(json.dumps(result,indent=2,sort_keys=True) + "\n",
                                       encoding="utf-8")
    return result

if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--out",default="sponge-breakout")
    parser.add_argument("--episodes",type=int,default=3000)
    parser.add_argument("--train-offset",type=int,default=TRAIN_OFFSET)
    parser.add_argument("--validation-offset",type=int,default=VALID_OFFSET)
    parser.add_argument("--holdout-offset",type=int,default=HOLDOUT_OFFSET)
    parser.add_argument("--learner-seed",type=int,default=20261011)
    parser.add_argument("--run-key",default="original")
    parser.add_argument("--ledger",type=Path)
    args=parser.parse_args()
    summary=run(args.out,args.episodes,train_offset=args.train_offset,
                validation_offset=args.validation_offset,
                holdout_offset=args.holdout_offset,learner_seed=args.learner_seed,
                run_key=args.run_key,ledger_path=args.ledger)
    print(json.dumps({"run_key":summary["run_key"],
                      "holdout":summary["holdout"],"delta":summary["holdout_delta"],
                      "selected_episode":summary["selected_episode"],
                      "journal_tip":summary["journal_tip"],
                      "ledger_entry_sha256":summary.get("ledger_entry_sha256")},sort_keys=True))
