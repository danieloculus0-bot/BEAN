"""Free Range BEAN experiment: 3-switch lock puzzle, BFS oracle, tabular Q-learning.

Standalone stdlib study. Three actions are left/toggle/right (toggle is DQN's
'stay' slot). This does NOT import the research-only SpongeDQN or claim it ran.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass
import gzip
import hashlib
import json
from pathlib import Path
from random import Random

ACTIONS=(-1,0,1)
N=3
MAX_STEPS=18
SCHEMA="bean.free_range.switch_puzzle.v1"

@dataclass(frozen=True)
class State:
    bits:int
    cursor:int
    target:int

def move(s:State, action:int)->State:
    if action not in ACTIONS:raise ValueError("invalid action")
    if action==0:return State(s.bits^(1<<s.cursor),s.cursor,s.target)
    return State(s.bits,(s.cursor+action)%N,s.target)

def optimal(start:State)->list[int]:
    if start.bits==start.target:return []
    queue=deque([(start,())]);seen={start}
    while queue:
        state,history=queue.popleft()
        for action in ACTIONS:
            nxt=move(state,action)
            if nxt in seen:continue
            seq=history+(action,)
            if nxt.bits==start.target:return list(seq)
            queue.append((nxt,seq));seen.add(nxt)
    raise RuntimeError("unreachable lock")

def key(s:State)->str:return f"{s.bits}:{s.cursor}:{s.target}"

class QBean:
    """Actual temporal-difference Q update. Values are not neural weights."""
    def __init__(self,seed=17,alpha=.22,gamma=.93):
        self.rng=Random(seed);self.alpha=alpha;self.gamma=gamma
        self.q:dict[str,list[float]]={}
        self.updates=0;self.reward_total=0.0
    def values(self,s:State)->list[float]:
        return self.q.setdefault(key(s),[0.0]*3)
    def choose(self,s:State,epsilon:float=0)->int:
        if self.rng.random()<epsilon:return self.rng.randrange(3)
        values=self.values(s);maximum=max(values)
        return next(i for i,v in enumerate(values) if v==maximum)
    def episode(self,target:int,*,epsilon:float=.15,learn=True,cap:int=MAX_STEPS):
        s=State(self.rng.randrange(8),self.rng.randrange(N),target)
        path=[];total=0.
        if s.bits==s.target:
            return {"solved":True,"steps":0,"reward":10.,"path":[]}
        for step in range(cap):
            a=self.choose(s,epsilon if learn else 0)
            nxt=move(s,ACTIONS[a]);done=nxt.bits==target
            reward=10. if done else (-1. if step==cap-1 else -.1)
            total+=reward;path.append(ACTIONS[a])
            if learn:
                current=self.values(s)
                desired=reward+(0 if done else self.gamma*max(self.values(nxt)))
                current[a]+=self.alpha*(desired-current[a])
                self.updates+=1
            s=nxt
            if done:break
        if learn:self.reward_total+=total
        return {"solved":s.bits==target,"steps":len(path),"reward":round(total,5),"path":path}
    def train(self,episodes=9000):
        for episode in range(episodes):
            self.episode(episode%8,epsilon=max(.04,.85*(1-episode/episodes)))
        return self
    def save(self,path:Path):
        payload={"schema":SCHEMA,"q":self.q,"updates":self.updates,
                 "reward_total":self.reward_total}
        original=json.dumps(payload,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
        packed=gzip.compress(original,compresslevel=9,mtime=0)
        path.parent.mkdir(parents=True,exist_ok=True)
        path.write_bytes(packed)
        return hashlib.sha256(original).hexdigest()
    def load(self,path:Path,expected_sha:str):
        raw=gzip.decompress(path.read_bytes())
        if hashlib.sha256(raw).hexdigest()!=expected_sha:raise ValueError("checkpoint checksum mismatch")
        saved=json.loads(raw)
        if saved["schema"]!=SCHEMA:raise ValueError("invalid checkpoint")
        self.q={k:list(map(float,v)) for k,v in saved["q"].items()}
        self.updates=int(saved["updates"]);self.reward_total=float(saved["reward_total"])
        return self

def frozen_evaluate(agent:QBean):
    """No Q updates; all 8 goals x 8 start states x 3 cursor positions."""
    result=[]
    for target in range(8):
        for initial in range(8):
            for cursor in range(N):
                s=State(initial,cursor,target)
                solution=optimal(s)
                actions=[]
                for _ in range(MAX_STEPS):
                    if s.bits==target:break
                    a=ACTIONS[agent.choose(s,epsilon=0)]
                    s=move(s,a);actions.append(a)
                solved=s.bits==target
                result.append({"target":target,"initial":initial,"cursor":cursor,
                               "solved":solved,"steps":len(actions),
                               "oracle_steps":len(solution),"reward":round((10 if solved else -1)-.1*len(actions),4)})
    return result

def run(seed=17,episodes=9000):
    agent=QBean(seed=seed)
    before=frozen_evaluate(agent)
    agent.train(episodes)
    after=frozen_evaluate(agent)
    def summarize(rows):
        solved=sum(x["solved"] for x in rows)
        return {"cases":len(rows),"solved":solved,
                "optimal_when_solved":sum(x["solved"] and x["steps"]==x["oracle_steps"] for x in rows),
                "average_reward":round(sum(x["reward"] for x in rows)/len(rows),4),
                "total_moves":sum(x["steps"] for x in rows)}
    return agent,{"schema":SCHEMA,"seed":seed,"episodes":episodes,
                  "baseline":summarize(before),"q_learning":summarize(after),
                  "q_updates":agent.updates,"brute_force_oracle_cases":len(after),
                  "no_neural_network_training":True,"case_events":after}

if __name__=="__main__":
    import argparse
    parser=argparse.ArgumentParser()
    parser.add_argument("--episodes",type=int,default=9000)
    parser.add_argument("--output",type=Path,default=Path("bean-puzzle-results.json"))
    args=parser.parse_args()
    agent,report=run(episodes=args.episodes)
    path=args.output;path.parent.mkdir(parents=True,exist_ok=True)
    digest=agent.save(path.with_suffix(".q.json.gz"))
    report["policy_checksum"]=digest
    path.write_text(json.dumps(report,indent=2,sort_keys=True)+"\n")
    print(json.dumps({k:v for k,v in report.items() if k!="case_events"},indent=2))
