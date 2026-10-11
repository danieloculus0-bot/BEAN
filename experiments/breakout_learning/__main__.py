"""BEAN Breakout proof: real journal-backed policy selection, no LLM retraining.
Run from repository root: python -m experiments.breakout_learning
Requires numpy and user-supplied breakout implementation in experiments/breakout_learning/game.py.
"""
from pathlib import Path
import json, hashlib
import numpy as np
from bean.optimization.autodev import Journal
from .game import Breakout, eval_q

def run(root=Path("breakout-proof"), episodes=3000):
    root=Path(root);root.mkdir(parents=True,exist_ok=True)
    journal=Journal(root/"bean_learning.sqlite")
    random=np.random.default_rng(20261011)
    q=np.zeros((15,2,2,3),dtype=float)
    holdout=range(18000,18200)
    checks=(0,500,1000,1500,2000,2500,3000)
    best=-1.;best_step=None
    outputs=[]
    def check(step):
        nonlocal best,best_step
        metrics=eval_q(q,holdout)
        digest=hashlib.sha256(q.tobytes()).hexdigest()
        improved=metrics["bricks"]>best
        # This is a measured checkpoint selection policy, NOT a proof of cognitive transfer.
        if improved:
            best=metrics["bricks"];best_step=step
            np.save(root/"best_policy.npy",q,allow_pickle=False)
        journal.append({"objective":"breakout_policy","iteration":len(outputs),"episode":step,
            "policy_sha256":digest,"metrics":metrics,"promoted":improved,
            "best_episode":best_step,"best_bricks":best})
        outputs.append({"episode":step,**metrics,"promoted":improved})
    check(0)
    for ep in range(1,episodes+1):
        env=Breakout(900000+ep)
        epsilon=.8*(1-ep/max(episodes,1))**1.15+.025
        while not env.done:
            state=env.state()
            act=int(random.integers(3)) if random.random()<epsilon else int(np.argmax(q[state]+random.random(3)*1e-7))
            reward=env.step(act);next_state=env.state()
            delta=reward+(0 if env.done else .975*np.max(q[next_state]))-q[state+(act,)]
            q[state+(act,)]+=.23*delta
        if ep in checks:check(ep)
    tip=journal.export()["tip"]
    journal.close()
    reopened=Journal(root/"bean_learning.sqlite")
    recorded=reopened.events("breakout_policy")
    assert len(recorded)==len(checks) and reopened.export()["tip"]==tip
    winner=np.load(root/"best_policy.npy",allow_pickle=False)
    assert hashlib.sha256(winner.tobytes()).hexdigest()==next(r["policy_sha256"] for r in recorded if r["episode"]==best_step)
    final=eval_q(q,range(21000,21200))
    selected=eval_q(winner,range(21000,21200))
    cold=eval_q(np.zeros_like(q),range(21000,21200))
    verdict={"method":"real BEAN autodev.Journal with independent Q-learning trainer","journal_sha256_tip":tip,
       "training_checkpoints":outputs,"chosen_checkpoint":best_step,
       "unseen_evaluation":{"cold":cold,"last":final,"journal_selected":selected},
       "net_gain_unseen":selected["bricks"]-cold["bricks"],
       "limitations":"Checkpoint selection used 200 validation seeds; 200 disjoint final seeds. Not an LLM/BEAN cognitive transfer result."}
    (root/"results.json").write_text(json.dumps(verdict,indent=2))
    reopened.close()
    return verdict
if __name__=="__main__":
    print(json.dumps(run(),indent=2))
