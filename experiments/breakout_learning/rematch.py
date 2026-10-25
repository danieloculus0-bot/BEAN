"""Paired original Breakout Q baseline vs current BEAN SpongeDQN; no lesson-transfer claims."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import numpy as np
import torch
from bean.optimization.autodev import Journal
from bean.optimization.sponge_dqn import SpongeDQN
from .game import Breakout, eval_q

def eval_agent(agent, seeds):
    games=[]
    for seed in seeds:
        env=Breakout(seed)
        games.append(env.play(lambda state: agent.choose(state, epsilon=0.0)))
    return {
        "bricks": round(sum(x["bricks"] for x in games)/len(games),4),
        "survival": round(100*sum(x["survived"] for x in games)/len(games),2),
        "avg_frames": round(sum(x["frames"] for x in games)/len(games),2),
    }

def original_baseline(episodes=3000):
    """Preserve original October 11 training RNG, Q update and seeds exactly."""
    rng=np.random.default_rng(20261011)
    q=np.zeros((15,2,2,3),dtype=float)
    checks=(0,500,1000,1500,2000,2500,3000)
    validation={}
    validation[0]=eval_q(q,range(18000,18200))
    for ep in range(1,episodes+1):
        env=Breakout(900000+ep)
        epsilon=.8*(1-ep/max(episodes,1))**1.15+.025
        while not env.done:
            state=env.state()
            action=int(rng.integers(3)) if rng.random()<epsilon else int(np.argmax(q[state]+rng.random(3)*1e-7))
            reward=env.step(action)
            following=env.state()
            delta=reward+(0 if env.done else .975*np.max(q[following]))-q[state+(action,)]
            q[state+(action,)]+=.23*delta
        if ep in checks:
            validation[ep]=eval_q(q,range(18000,18200))
    return q,validation

def run(root=Path("breakout-rematch-proof"), episodes=800):
    torch.set_num_threads(1)
    root=Path(root);root.mkdir(parents=True,exist_ok=True)
    train_seeds={"old": "900001 through 903000", "dqn": "960001 through "+str(960000+episodes)}
    q,old_checkpoints=original_baseline()
    holdout=range(21000,21200)
    old=eval_q(q,holdout)
    cold=eval_q(np.zeros_like(q),holdout)
    old_ref={"bricks":11.905,"survival":98.5,"avg_frames":989.4}
    assert old==old_ref, "Original benchmark did not reproduce: "+repr(old)
    agent=SpongeDQN(seed=20261025,domain="breakout",
                    batch_size=32,replay_capacity=12000,warmup=256,
                    learn_every=4,target_sync=300,lr=.0007,gamma=.99)
    new_untrained=eval_agent(agent,range(18000,18050))
    validation=[]
    for episode in range(1,episodes+1):
        env=Breakout(960000+episode)
        epsilon=.85*(1-episode/max(episodes,1))**1.1+.05
        while not env.done:
            state=env.state()
            action=agent.choose(state,epsilon=epsilon)
            reward=env.step(action)
            agent.observe(state,action,reward,env.state(),bool(env.done))
        if episode%200==0 or episode==episodes:
            result=eval_agent(agent,range(18000,18100))
            validation.append({"episode":episode,**result,"frames_trained":agent.frames,"gradient_updates":agent.updates})
    current=eval_agent(agent,holdout)
    receipt=hashlib.sha256(json.dumps({"baseline":old_checkpoints[3000],
                                        "dqn_validation":validation,
                                        "data":"100 validation seeds disjoint from final 200 holdout seeds"},
                                        sort_keys=True).encode()).hexdigest()
    journal=Journal(root/"bean_dqn_rematch.sqlite")
    saved=agent.checkpoint(journal,baseline=old_checkpoints[3000]["bricks"],
            candidate=validation[-1]["bricks"],samples=100,
            evaluation_sha256=receipt,episode=episodes,
            metadata={"domain":"original_breakout_24_bricks","train_source":"current main SpongeDQN",
                      "source_revision":"c8eada4fe83b3744ffd24082987cacf003882e25",
                      "prior_breakout_lessons_loaded":False,
                      "holdout_seeds_used_for_selection":False})
    journal.close()
    reopened=Journal(root/"bean_dqn_rematch.sqlite")
    recovered=SpongeDQN.recover_latest(reopened)
    assert recovered.weights_digest()==agent.weights_digest()
    assert recovered.choose((5,1,1))==agent.choose((5,1,1))
    tip=reopened.export()["tip"]
    reopened.close()
    report={
      "status":"completed","experiment":"BEAN current-core Breakout DQN rematch",
      "old_algorithm":"original Oct 11 numpy tabular Q, 3000 episodes",
      "new_algorithm":"BEAN main SpongeDQN replay neural Q, "+str(episodes)+" episodes",
      "same_game":True,"paired_final_seeds":"21000 through 21199",
      "train_seeds":train_seeds,
      "original_checkpoint_validation":old_checkpoints,
      "modern_neural_validation":validation,
      "original_unseen":old,"original_cold_unseen":cold,
      "modern_untrained_validation_50":new_untrained,
      "modern_unseen":current,
      "new_minus_original_bricks":round(current["bricks"]-old["bricks"],4),
      "new_minus_original_survival_pct_points":round(current["survival"]-old["survival"],2),
      "dqn_weights_digest":agent.weights_digest(),
      "journal_tip":tip,"memory_score":saved["quality"],
      "neural_gradient_updates":agent.updates,"checkpoint_recovered":True,
      "prior_lesson_transfer_demonstrated":False,
      "limitation":"Re-training current BEAN learning engine from scratch on same environment tests algorithm, not transferred abstract lessons; no previously trained Breakout DQN weights were supplied.",
    }
    (root/"results.json").write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps(report,indent=2))
    return report

if __name__=="__main__":
    run()
