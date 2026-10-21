"""Lab031: BEAN Factory Fault Detective, 3,000 distinct hidden-fault problems.

Active diagnosis from uncertain observations, real tabular temporal-difference
Q updates, and full compressed per-case evidence through IndexedLedger.
The simulation is synthetic; no industrial diagnosis or LLM training is implied.
"""
from __future__ import annotations

import argparse
import copy
import gzip
import hashlib
import json
import math
import random
from collections import defaultdict
from pathlib import Path

from indexed_ledger import IndexedLedger, encode, sha

SCHEMA="bean.fault_detective.lab031.v1"
FAULTS=("motor","drive","encoder","bearing","pneumatic","relay","sensor","power")
TESTS=("voltage","vibration","temperature","phase","actuator","relay_click","optical","current")
PRIOR=(.14,.12,.11,.15,.10,.12,.13,.13)
COST=(1.6,1.2,2.0,1.1,1.4,.9,1.4,1.7)
# P(positive diagnostic | hidden failure). Overlaps make inference uncertain.
LIKELIHOOD=(
    (.35,.85,.15,.10,.35,.80,.18,.92),
    (.24,.12,.08,.88,.75,.15,.12,.15),
    (.75,.80,.10,.92,.20,.45,.08,.13),
    (.12,.76,.90,.18,.12,.35,.80,.22),
    (.28,.33,.22,.15,.93,.48,.35,.30),
    (.20,.20,.15,.08,.18,.95,.24,.83),
    (.10,.28,.94,.12,.15,.22,.95,.10),
    (.85,.81,.20,.69,.12,.50,.15,.75),
)
ACTIONS=("diagnose","cheapest","information","discriminate")

def specimen(number:int,seed:int,shift:float):
    """Independent generator with distinct numerical seeds across all cohorts."""
    rng=random.Random(seed*100003+(number+1)*7919)
    truth=rng.choices(range(8),weights=PRIOR,k=1)[0]
    observations=[int(rng.random()<((1-shift)*LIKELIHOOD[t][truth]+shift*.5)) for t in range(8)]
    return {"id":f"FAULT-{number:04d}","seed":seed,"shift":shift,
            "fault":truth,"outcomes":observations}

def update(prior,test,positive):
    weights=[p*(LIKELIHOOD[test][i] if positive else 1-LIKELIHOOD[test][i]) for i,p in enumerate(prior)]
    denom=sum(weights)
    return tuple(p/denom for p in weights)

def entropy(probs):
    return -sum(p*math.log2(p) for p in probs if p>0)

def information_gain(prior,test):
    positive=sum(prior[i]*LIKELIHOOD[test][i] for i in range(8))
    return entropy(prior)-(positive*entropy(update(prior,test,1))+
                           (1-positive)*entropy(update(prior,test,0)))

def diagnostic(prior,already,tactic):
    remaining=[i for i in range(8) if i not in already]
    if not remaining: raise ValueError("no tests left")
    if tactic=="cheapest":
        return min(remaining,key=lambda t:(COST[t],t))
    if tactic=="information":
        return max(remaining,key=lambda t:(information_gain(prior,t)/COST[t],-t))
    if tactic=="discriminate":
        leaders=sorted(range(8),key=lambda i:(-prior[i],i))[:2]
        return max(remaining,key=lambda t:(abs(LIKELIHOOD[t][leaders[0]]-
                                                LIKELIHOOD[t][leaders[1]])/COST[t],-t))
    raise ValueError("unknown diagnostic tactic")

class Scoreboard:
    def __init__(self,games=0,wins=0,reward=0.,probes=0):
        self.games=games;self.wins=wins;self.reward=float(reward);self.probes=probes
    def view(self):
        return {"games":self.games,"wins":self.wins,
                "total_reward":round(self.reward,6),"probes":self.probes}
    def record(self,correct,reward,probes):
        self.games+=1;self.wins+=int(correct);self.reward+=reward;self.probes+=probes

def state(prior,already,scoreboard):
    ranked=sorted(prior,reverse=True)
    bucket=lambda value,marks:sum(value>=m for m in marks)
    rate=scoreboard.wins/max(1,scoreboard.games)
    # BEAN's live scoreboard is an actual part of the decision state.
    rating=0 if scoreboard.games<25 else (1 if rate<.40 else 2)
    return ":".join(map(str,(len(already),bucket(ranked[0],(.2,.35,.55,.75,.9)),
            bucket(ranked[0]-ranked[1],(.08,.2,.4)),
            bucket(entropy(prior),(1.,1.7,2.3)),rating)))

class QBrain:
    def __init__(self,seed):
        self.rng=random.Random(seed)
        self.q=defaultdict(lambda:[0.]*len(ACTIONS))
        self.updates=0
    def select(self,code,epsilon=0.):
        values=self.q[code]
        if self.rng.random()<epsilon:return self.rng.randrange(len(ACTIONS))
        return max(range(len(ACTIONS)),key=lambda action:(values[action],-action))
    def learn(self,code,action,reward,next_code=None):
        values=self.q[code]
        future=max(self.q[next_code]) if next_code is not None else 0.
        values[action]=round(values[action]+.18*(reward+.97*future-values[action]),8)
        self.updates+=1
    def snapshot(self):
        return {"schema":SCHEMA,"updates":self.updates,
                "q":{k:v for k,v in sorted(self.q.items())}}
    def digest(self):return sha(encode(self.snapshot()))

def play(case,policy,board,*,brain=None,learning=False,epsilon=0.,seed=0):
    """Only the oracle uses case['fault']; action policy never receives truth."""
    prior=tuple(PRIOR); used=[];trace=[];reward=0.
    rng=random.Random(seed)
    max_tests=8 if policy=="exhaustive" else 5
    for turn in range(max_tests+1):
        code=state(prior,used,board)
        score_view=board.view()
        q_before=brain.digest() if brain else None
        if len(used)>=max_tests:action="diagnose"
        elif policy=="bean":action=ACTIONS[brain.select(code,epsilon if learning else 0.)]
        elif policy=="untrained":action="diagnose"
        elif policy=="cheap4":action="cheapest" if turn<4 else "diagnose"
        elif policy=="info5":action="information"
        elif policy=="discrim5":action="discriminate"
        elif policy=="exhaustive":action="information"
        elif policy=="random":action=("cheapest","information","discriminate")[rng.randrange(3)]
        else:raise ValueError(policy)
        if action=="diagnose":
            answer=max(range(8),key=lambda i:(prior[i],-i))
            correct=answer==case["fault"]
            step_reward=40. if correct else -40.
            reward+=step_reward
            if learning:brain.learn(code,ACTIONS.index(action),step_reward)
            trace.append({"turn":turn,"action":action,"state":code,
                          "scoreboard_seen":score_view,"scoreboard_sha256":sha(encode(score_view)),
                          "q_before_sha256":q_before,"q_after_sha256":brain.digest() if brain else None,
                          "posterior_before":[round(p,10) for p in prior],
                          "answer":answer,"reward":step_reward})
            break
        test=diagnostic(prior,used,action)
        observed=case["outcomes"][test]
        prior=update(prior,test,observed)
        used.append(test)
        step_reward=-COST[test]
        reward+=step_reward
        if learning:
            next_code=state(prior,used,board)
            brain.learn(code,ACTIONS.index(action),step_reward,next_code)
        trace.append({"turn":turn,"action":action,"state":code,
                      "scoreboard_seen":score_view,"scoreboard_sha256":sha(encode(score_view)),
                      "q_before_sha256":q_before,"q_after_sha256":brain.digest() if brain else None,
                      "posterior_before":[round(p,10) for p in
                        (tuple(PRIOR) if turn==0 else pre_update)],
                      "test":test,"observation":observed,"reward":step_reward})
        pre_update=prior
    board.record(correct,reward,len(used))
    return {"policy":policy,"correct":correct,"diagnosed_fault":answer,
            "probes":len(used),"reward":round(reward,6),
            "trace":trace,"final_board":board.view(),
            "truth_revealed_after":case["fault"]}

def summarize(results):
    size=len(results)
    return {"cases":size,"correct":sum(x["correct"] for x in results),
            "mean_reward":round(sum(x["reward"] for x in results)/size,5),
            "mean_probes":round(sum(x["probes"] for x in results)/size,5),
            "wrong":sum(not x["correct"] for x in results)}

def run(seed=61309):
    """All 3000 specimens are disjoint; dev selects epoch, holdout remains unseen."""
    cases=[
        specimen(i,seed+11,.05) if i<1600 else
        specimen(i,seed+29,.13) if i<2000 else
        specimen(i,seed+7919,.15)
        for i in range(3000)
    ]
    records=[{"kind":"test","name":case["id"],"case":case,"trials":[]}
             for case in cases]
    brain=QBrain(seed)
    board=Scoreboard()
    best=None
    checkpoints=[]
    for epoch in range(1,4):
        for i in range(1600):
            epsilon=max(.05,.35*(1-i/1600))
            trial=play(cases[i],"bean",board,brain=brain,learning=True,epsilon=epsilon)
            trial["epoch"]=epoch
            records[i]["trials"].append(trial)
        candidate=copy.deepcopy(brain)
        dev_board=Scoreboard(**{"games":board.games,"wins":board.wins,
                               "reward":board.reward,"probes":board.probes})
        dev=[]
        for i in range(1600,2000):
            trial=play(cases[i],"bean",dev_board,brain=candidate)
            trial["checkpoint_epoch"]=epoch
            records[i]["trials"].append(trial)
            dev.append(trial)
        score=summarize(dev)
        checkpoints.append({"epoch":epoch,"validation":score,"q_sha256":brain.digest()})
        if best is None or (score["mean_reward"],score["correct"],-epoch) > best[0]:
            best=((score["mean_reward"],score["correct"],-epoch),
                  copy.deepcopy(brain),copy.deepcopy(board),epoch)
    _,selected,training_board,selected_epoch=best
    chosen_digest=selected.digest()
    frozen_before=selected.snapshot()
    policies=("bean","untrained","cheap4","info5","discrim5","exhaustive")
    holdout_rows={policy:[] for policy in policies}
    for policy in policies:
        current_board=copy.deepcopy(training_board) if policy=="bean" else Scoreboard()
        # Fresh baseline policy instances; only trained BEAN has Q learned from training.
        learner=selected if policy=="bean" else None
        for i in range(2000,3000):
            trial=play(cases[i],policy,current_board,brain=learner,seed=seed+i)
            records[i]["trials"].append(trial)
            holdout_rows[policy].append(trial)
    assert frozen_before==selected.snapshot(),"frozen policy changed during holdout"
    scoreboard={
        "schema":SCHEMA,"seed":seed,"unique_problems":3000,
        "training_problems":1600,"development_problems":400,"holdout_problems":1000,
        "training_epochs":3,"training_attempts":4800,
        "checkpoint_selection":"highest validation mean reward (then accuracy, then earlier epoch)",
        "checkpoints":checkpoints,"selected_epoch":selected_epoch,
        "selected_policy_sha256":chosen_digest,"selected_q_states":len(selected.q),
        "holdout":{key:summarize(value) for key,value in holdout_rows.items()},
        "evidence_classification":"synthetic noisy diagnosis, not real machine diagnosis",
        "claims":{"q_values_updated":True,"neural_network_trained":False,
                  "model_weights_updated":False,"general_intelligence_proven":False},
        "limits":"Chosen policies are preprogrammed; Q selects diagnostic strategy and stopping point."
    }
    for rec in records:
        important=rec["trials"][-1] if len(rec["trials"])==1 else (
            next((t for t in rec["trials"] if t["policy"]=="bean"),rec["trials"][0]))
        rec["status"]="passed" if important["correct"] else "failed"
    policy=encode(selected.snapshot())
    return records,scoreboard,policy

def archive(output,seed=61309,verify_only=False):
    output=Path(output)
    events,report,policy=run(seed)
    ledger=IndexedLedger(output/"ledger")
    if not verify_only:
        output.mkdir(parents=True,exist_ok=True)
        for batch in range(30):
            ledger.append(f"faults-{batch:02d}",events[batch*100:(batch+1)*100])
        digest=sha(policy)
        (output/"trained-policy.json.gz").write_bytes(gzip.compress(policy,mtime=0))
        report["trained_policy_sha256"]=digest
        report["source_case_set_sha256"]=sha(encode([rec["case"] for rec in events]))
        (output/"scoreboard.json").write_bytes(encode(report)+b"\n")
    stored=json.loads((output/"scoreboard.json").read_bytes())
    if stored["source_case_set_sha256"] != sha(encode([rec["case"] for rec in events])):
        raise ValueError("case truth/set differs from archive manifest")
    if stored["trained_policy_sha256"] != sha(gzip.decompress(
            (output/"trained-policy.json.gz").read_bytes())):
        raise ValueError("Q checkpoint hash mismatch")
    for key in report:
        if stored[key]!=report[key]:raise ValueError("scoreboard replay divergence: "+key)
    if ledger.rebuild()!=3000:raise ValueError("incomplete archived case set")
    ids=ledger.ids()
    if len(ids)!=3000 or len(set(ids))!=3000:raise ValueError("duplicate case IDs")
    for event in events:
        found=ledger.ids(name=event["name"])
        if len(found)!=1 or ledger.get(found[0])!=event:
            raise ValueError("exact case replay mismatch: "+event["name"])
    # The index is disposable; true source of truth is immutable compressed data.
    ledger.cache.unlink()
    if ledger.rebuild()!=3000:raise ValueError("cold restart lost events")
    return {**report,"archived_case_events":3000,"replay_after_restart":True,
            "compressed_archive_files":30}

if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--output",type=Path,default=Path("fault-detective-evidence"))
    ap.add_argument("--verify",action="store_true")
    args=ap.parse_args()
    result=archive(args.output,verify_only=args.verify)
    print(json.dumps(result,indent=2))
