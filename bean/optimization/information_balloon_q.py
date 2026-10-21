"""BEAN Information Balloon: 3,000 real lossless compression Q-learning trials.

Reuses BEAN's existing PortfolioLedger Q updates and intact event replay.
Every episode compresses and decodes an actual synthetic byte-stream, computes
measured latency and budget fitness, and earns one signed outcome receipt.
No retained source byte can be discarded in order to earn a reward.
"""
from __future__ import annotations

import base64
from dataclasses import asdict
import hashlib
import math
import random
import time

from .information_balloon import (
    Recipe, canonical, contextual_recall, digest, pack, unpack,
    weissman_style)
from .portfolio_ledger import PortfolioLedger

APP="BEAN/InformationBalloon"
SCHEMA="bean.balloon.q3000.v1"
CHOICES={
    "raw":Recipe("raw",0),
    "fast":Recipe("zlib",1),
    "standard":Recipe("zlib",6),
    "high":Recipe("zlib",9),
    "invented_dictionary":Recipe("zlib",6,6,16),
    "bzip":Recipe("bz2",1),
}


def make_case(seed,episode):
    rng=random.Random(seed*1000003+episode)
    group=rng.choice(("repetitive","structured","noisy","mixed"))
    relaxed=rng.choice((False,True))
    records=[]
    for i in range(8):
        if group=="repetitive":
            text=("INSPECTION VERIFIED DIMENSION PASS ")*20
        elif group=="structured":
            text=" ".join(f"{rng.randrange(1000000):06d}" for _ in range(30))
        elif group=="noisy":
            text="".join(rng.choice(
                "abcdefghijklmnopqrstuvwxyz0123456789"
                ) for _ in range(210))
        else:
            text=(("REPEAT SAME SETUP A " * 9)+
                "".join(rng.choice("abcd0123456789") for _ in range(75)))
        records.append({"id":f"trial-{episode:06d}-row-{i}",
                        "text":text,
                        "tags":["ledger","quality" if i%2 else "scheduling"]})
    raw=canonical(records)
    return {"group":group,"relaxed":relaxed,"records":records,"raw":raw,
            "state":group+("/relaxed" if relaxed else "/tight")}


def choose(ledger,state,rng,epsilon=0):
    value=ledger._q(APP,state)
    if rng.random()<epsilon:
        return rng.choice(tuple(CHOICES))
    best=max(value.get(action,0.0) for action in CHOICES)
    ties=[action for action in CHOICES if math.isclose(
        value.get(action,0.0),best,abs_tol=1e-12)]
    return rng.choice(ties)


def attempt(source,recipe):
    start=time.perf_counter_ns()
    archive=pack(source,recipe,training=source)
    if unpack(archive)!=source:
        raise AssertionError("unrecovered source bytes")
    elapsed=max(0.000001,(time.perf_counter_ns()-start)/1000000)
    return archive,elapsed


def measure_case(case,action):
    raw=case["raw"]
    baseline_archive,baseline_ms=attempt(raw,CHOICES["standard"])
    budget=round(len(baseline_archive)*(1.45 if case["relaxed"] else 1.02))
    archive,elapsed_ms=attempt(raw,CHOICES[action])
    fits=len(archive)<=budget
    # Objective-first reward; no claim of gain if the budget is missed.
    if fits:
        reward=(0.65-0.23*(elapsed_ms/max(baseline_ms,0.005))+
                0.04*(len(baseline_archive)-len(archive))/
                max(1,len(baseline_archive)))
    else:
        reward=-1.0-(len(archive)-budget)/budget
    reward=round(max(-3.0,min(2.0,reward)),8)
    recall=contextual_recall(case["records"],
                             ["scheduling","quality"],2048)
    if recall["mean_recall"]<1.0:
        reward=-3.0
    return {"reward":reward,"fits":fits,"budget":budget,
            "source_bytes":len(raw),"archive_bytes":len(archive),
            "elapsed_ms":elapsed_ms,"baseline_ms":baseline_ms,
            "baseline_bytes":len(baseline_archive),
            "compression_ratio":len(raw)/len(archive),
            "weissman_style_diagnostic":weissman_style(
                len(raw)/len(archive),len(raw)/len(baseline_archive),
                elapsed_ms,baseline_ms),
            "reference_recall":recall["mean_recall"],
            "source_sha256":digest(raw),
            "package_sha256":digest(archive),
            "package":archive}


def evaluate(ledger,seed,count):
    """Read-only, frozen policy evaluation; no new Q learning on validation."""
    rng=random.Random(818281+seed)
    totals={"bean":0.0,"standard":0.0,"fast":0.0}
    fit={"bean":0,"standard":0,"fast":0}
    selections={a:0 for a in CHOICES}
    source_hashes=[]
    for ep in range(count):
        case=make_case(seed,ep)
        action=choose(ledger,case["state"],rng,0.0)
        selections[action]+=1
        for label,strategy in (("bean",action),("standard","standard"),
                               ("fast","fast")):
            m=measure_case(case,strategy)
            totals[label]+=m["reward"]
            fit[label]+=int(m["fits"] and m["reference_recall"]==1)
        source_hashes.append(digest(case["raw"]))
    return {"cases":count,"source_manifest_sha256":digest(canonical(source_hashes)),
            "mean_reward":{k:round(v/count,6) for k,v in totals.items()},
            "budget_and_recall_success":{k:fit[k]/count for k in fit},
            "selection_counts":selections}


def run_learning(db_path, *,episodes=3000,train_seed=101,
                 validation_seed=202,holdout_seed=303,eval_cases=120):
    if type(episodes) is not int or not 1<=episodes<=3000:
        raise ValueError("episode count must be 1..3000")
    if len({train_seed,validation_seed,holdout_seed})!=3:
        raise ValueError("distinct training, validation and holdout seeds needed")
    ledger=PortfolioLedger(db_path)
    rng=random.Random(9919+train_seed)
    trials=[]
    checkpoints=[]
    try:
        if ledger.verify()["events"]:
            raise ValueError("new independent learning ledger is required")
        before=evaluate(ledger,validation_seed,eval_cases)
        targets=set([250,500,1000,1500,2000,2500,episodes])
        for ep in range(episodes):
            case=make_case(train_seed,ep)
            epsilon=0.27-0.22*ep/max(1,episodes-1)
            action=choose(ledger,case["state"],rng,epsilon)
            measure=measure_case(case,action)
            evidence={"episode":ep,"state":case["state"],"action":action,
                "source_b64":base64.b64encode(case["raw"]).decode("ascii"),
                "package_b64":base64.b64encode(measure["package"]).decode("ascii"),
                "metrics":{k:v for k,v in measure.items() if k!="package"},
                "dataset":"synthetic"}
            event_sha=digest(canonical(evidence))
            result=ledger.observe(
                app=APP,event_id=f"compression_{ep:06d}",
                state=case["state"],action=action,
                reward=measure["reward"],next_state=None,done=True,
                evidence_ref=f"synthetic://balloon/{event_sha[:32]}",
                kind="synthetic",revision=SCHEMA,
                tags=("compression","data_integrity"))
            if not result["new"]:
                raise AssertionError("duplicate compression trial event")
            evidence["q_receipt"]=result["receipt"]
            trials.append(evidence)
            if ep+1 in targets:
                checkpoints.append({"episode":ep+1,"validation":evaluate(
                    ledger,validation_seed,eval_cases)})
        verified=ledger.verify()
        if verified["events"]!=episodes or verified["rewarded_events"]!=episodes:
            raise AssertionError("mismatched Q updates or lost receipts")
        # Cold heldout not used for selection, calibration or prior checkpoints.
        final=evaluate(ledger,holdout_seed,eval_cases)
        if ledger.event(APP,"compression_000000") is None:
            raise AssertionError("first receipt missing")
        if ledger.event(APP,f"compression_{episodes-1:06d}") is None:
            raise AssertionError("last receipt missing")
        return {"schema":SCHEMA,"episodes":episodes,
                "real_compression_evaluations":episodes,
                "q_updates":verified["rewarded_events"],
                "train_seed":train_seed,"validation_seed":validation_seed,
                "holdout_seed":holdout_seed,"pretraining_validation":before,
                "checkpoints":checkpoints,"independent_holdout":final,
                "ledger_verification":verified,
                "scoreboard":ledger.portfolio_context(),
                "all_trials_sha256":digest(canonical(trials))},trials
    finally:
        ledger.close()
