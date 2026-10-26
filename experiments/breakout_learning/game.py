"""Deterministic simplified Breakout environment used in the independent pilot.
Three actions: left, stay, right. Ball/paddle physics exactly follow the pilot.
"""
import random
import numpy as np
W=320;PW=57
class Breakout:
    def __init__(self,seed,max_steps=1000):
        if not isinstance(max_steps,int) or isinstance(max_steps,bool) or max_steps<1:
            raise ValueError("max_steps must be a positive integer")
        self.max_steps=max_steps
        self.r=random.Random(seed);self.reset()
    def reset(self):
        self.px=W/2;self.x=self.r.uniform(65,W-65);self.y=190
        self.vx=self.r.choice([-2.7,-2.0,2.0,2.7]);self.vy=-3.5
        self.bricks=set((i,j) for i in range(8) for j in range(3))
        self.hit=0;self.miss=0;self.steps=0;self.done=False
    def impact(self):
        if self.vy<=0:return self.x
        z=self.x+self.vx*(246-self.y)/max(self.vy,.05)
        z=z%(2*(W-12))
        return (z if z<=W-12 else 2*(W-12)-z)+6
    def state(self):
        delta=self.impact()-self.px
        return (max(0,min(14,int((delta+112)/16))),int(self.vx>=0),int(self.vy>=0))
    def step(self,act):
        if self.done:return 0.
        self.px=max(PW/2+4,min(W-PW/2-4,self.px+(act-1)*6.5))
        self.x+=self.vx;self.y+=self.vy;self.steps+=1;reward=-.001
        if self.x<6:self.x=12-self.x;self.vx=abs(self.vx)
        if self.x>W-6:self.x=2*(W-6)-self.x;self.vx=-abs(self.vx)
        if self.y<9:self.y=18-self.y;self.vy=abs(self.vy)
        if self.vy<0 and 47<=self.y<=115:
            ix=int(self.x/(W/8));jy=int((self.y-47)/22)
            if (ix,jy) in self.bricks:
                self.bricks.remove((ix,jy));self.hit+=1;reward+=3;self.vy=abs(self.vy)
        if self.vy>0 and self.y>=244:
            if abs(self.x-self.px)<=PW/2+3:
                self.y=488-self.y;self.vy=-abs(self.vy)
                self.vx=max(-4.2,min(4.2,self.vx+(self.x-self.px)/18));reward+=12
            else:
                self.miss=1;reward-=18;self.done=True
        if not self.bricks or self.steps>=self.max_steps:self.done=True
        return reward
    def play(self,policy):
        while not self.done:
            self.step(policy(self.state()))
        return {"bricks":self.hit,"survived":int(not self.miss),"frames":self.steps,
                "won":int(not self.bricks and not self.miss)}
def eval_q(q,seeds):
    vals=[]
    for seed in seeds:
        env=Breakout(seed)
        vals.append(env.play(lambda state:int(np.argmax(q[state]))))
    return {"bricks":round(float(np.mean([v["bricks"] for v in vals])),4),
            "survival":round(100*float(np.mean([v["survived"] for v in vals])),2),
            "avg_frames":round(float(np.mean([v["frames"] for v in vals])),2)}
