"""BEAN experimental claim calibration: mistakes become independently scored Q experience.

The Q-updater is BEAN's EXISTING PortfolioLedger; its hash-linked event stream
is the authority for learned values. The environment supplies synthetic
*hidden* truth after each decision, not an agent-authored success narrative.
No live-world "verified" claims can be minted by these methods, and no
host-supplied text/source label authenticates itself.

This is a model-free *claim decision* experiment, not a neural language model,
a general fact checker, or autonomous BEAN improvement of the whole system.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import gzip
import hashlib
import json
import math
from pathlib import Path
import random

from bean.optimization.portfolio_ledger import PortfolioLedger, canonical

APP="BEAN/claim_calibration_growth"
SCHEMA="bean.claim_growth.synthetic.v1"
ACTIONS=("tentative","qualify","unknown")
SOURCES=("measured_report","partial_report","boastful_agent")
KINDS=("test_result","learning_gain","self_repair","release_claim")
TRAIN_DOMAINS=("quality","scheduling","compression")
HOLDOUT_DOMAINS=("robotics","maintenance","inventory")
TRIAL_COUNT=3000


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


@dataclass(frozen=True)
class Claim:
    case_id: str
    domain: str
    source: str
    kind: str
    declared_verified: bool
    source_confidence: float
    statement: str


@dataclass(frozen=True)
class AdjudicatedOutcome:
    """Synthetic oracle value held back until AFTER decision and evaluation.

    Real-world outcomes would require an independently authenticated verifier
    outside this module; strings saying 'verified' are NEVER such a verifier.
    """
    case_id: str
    actually_supported: bool
    synthetic_oracle_sha256: str


def make_case(seed, index, *, phase):
    if phase not in ("train","holdout"):
        raise ValueError("phase must be train or holdout")
    rng=random.Random((seed<<24)+index)
    domains=TRAIN_DOMAINS if phase=="train" else HOLDOUT_DOMAINS
    source=rng.choice(SOURCES)
    kind=rng.choice(KINDS)
    declared_verified=rng.random()<{
        "measured_report":.88,"partial_report":.53,"boastful_agent":.97
    }[source]
    p={"measured_report":.95,
       "partial_report":.58,
       "boastful_agent":.12}[source]
    if kind=="self_repair":p*=.8
    if kind=="release_claim":p*=.65
    if phase=="holdout":
        p=max(0.01,p-.04)
    actual=rng.random()<p
    domain=domains[index%len(domains)]
    case_id=f"{phase}_{seed}_{index:06d}"
    statement=f"{domain} experiment reported {kind} success"
    claim=Claim(case_id,domain,source,kind,declared_verified,
                .99 if source=="boastful_agent" else (.84 if declared_verified else .53),
                statement)
    oracle=AdjudicatedOutcome(
        case_id,actual,digest({"case_id":case_id,"supported":actual,
                                "source":"synthetic_hidden_oracle_v1"}))
    return claim,oracle


def state_for(claim):
    # The model never sees truth, the oracle receipt, or the domain label.
    # Cross-domain transfer must be genuine reuse of observed evidence patterns.
    return f"{claim.source}/{claim.kind}/{int(claim.declared_verified)}"


def decide(ledger,claim,rng,*,epsilon=0.0):
    if not 0<=epsilon<=1:
        raise ValueError("epsilon must be in [0,1]")
    if rng.random()<epsilon:
        return rng.choice(ACTIONS)
    values=ledger._q(APP,state_for(claim))
    high=max(values.get(action,0.0) for action in ACTIONS)
    choices=[a for a in ACTIONS
             if math.isclose(values.get(a,0.),high,abs_tol=1e-12)]
    return rng.choice(choices)


def message(claim,action):
    """No action asserts that public internet claims are proven."""
    if action=="tentative":
        return "Tentatively supported by prior calibration; verify source and outcome before claiming success."
    if action=="qualify":
        return "An outcome is reported; independent verification and attribution are not established."
    if action=="unknown":
        return "Not established. Preserve the claim and request independent measurement."
    raise ValueError("unknown action")


def reward_for(action,actually_supported):
    """Outcome scoring comes ONLY from the withheld synthetic oracle.

    The false-positive cost is intentionally high. Correct uncertainty is
    rewarded, but always refusing also loses utility on legitimately supported
    successes. No reward can be earned from an agent's own declaration.
    """
    if type(actually_supported) is not bool or action not in ACTIONS:
        raise ValueError("unverified score input")
    matrix={
        "tentative":(2.0,-4.0),
        "qualify":(.4,.2),
        "unknown":(-.3,.8),
    }
    return matrix[action][0 if actually_supported else 1]


def accept_feedback(ledger,claim,action,oracle):
    """Only bench's synthetic oracle may score this *research* learner.

    In production, actual CI/physical measurements need an external verified
    receipt adapter. A caller saying 'passed' or giving a URL is NOT proof.
    """
    if not isinstance(oracle,AdjudicatedOutcome) or claim.case_id!=oracle.case_id:
        raise ValueError("independent synthetic oracle outcome required")
    expected=digest({"case_id":oracle.case_id,
                     "supported":oracle.actually_supported,
                     "source":"synthetic_hidden_oracle_v1"})
    if oracle.synthetic_oracle_sha256!=expected:
        raise ValueError("synthetic oracle checksum mismatch")
    feedback=reward_for(action,oracle.actually_supported)
    source_hash=digest(asdict(claim))
    evidence_ref="synthetic://claim/"+digest({
        "claim_sha256":source_hash,"oracle_sha256":expected})[:40]
    result=ledger.observe(
        app=APP,event_id=claim.case_id,state=state_for(claim),
        action=action,reward=feedback,done=True,evidence_ref=evidence_ref,
        kind="synthetic",revision=SCHEMA,
        tags=("evidence","claim_calibration","synthetic"))
    return {"reward":feedback,"new":result["new"],
            "receipt":result["receipt"],"source_sha256":source_hash,
            "oracle_sha256":expected}


def score(action,label):
    return {"reward":reward_for(action,label),
            "supported_tentative":int(action=="tentative" and label),
            "false_tentative":int(action=="tentative" and not label),
            "correct_unknown":int(action=="unknown" and not label),
            "missed_success":int(action=="unknown" and label),
            "qualified":int(action=="qualify")}


def evaluate(ledger,seed,count,*,no_learning=False):
    """Frozen policies on sealed, DIFFERENT-domain cases. No ledger mutation."""
    rng=random.Random(seed+77219)
    metrics={a:[] for a in ("BEAN_Q","boast_accepting","always_qualify","always_unknown")}
    sha_sources=[]
    full=[]
    for index in range(count):
        claim,oracle=make_case(seed,index,phase="holdout")
        chosen=decide(ledger,claim,rng,epsilon=0)
        methods={"BEAN_Q":chosen,
                 "boast_accepting":("tentative" if claim.declared_verified else "qualify"),
                 "always_qualify":"qualify","always_unknown":"unknown"}
        result={name:score(action,oracle.actually_supported)
                for name,action in methods.items()}
        for name,data in result.items():metrics[name].append(data)
        sha_sources.append(digest(asdict(claim)))
        full.append({"claim":asdict(claim),"oracle":asdict(oracle),
                     "decisions":methods,"scores":result})
    n=count
    summary={}
    for name,rows in metrics.items():
        summary[name]={
            "mean_reward":round(sum(row["reward"] for row in rows)/n,6),
            "false_tentative":sum(row["false_tentative"] for row in rows),
            "supported_tentative":sum(row["supported_tentative"] for row in rows),
            "correct_unknown":sum(row["correct_unknown"] for row in rows),
            "missed_success":sum(row["missed_success"] for row in rows),
            "qualified":sum(row["qualified"] for row in rows)}
    return {"seed":seed,"count":count,"domain_scope":list(HOLDOUT_DOMAINS),
            "source_manifest_sha256":digest(sha_sources),
            "metrics":summary},full


def experiment(out,seed,*,episodes=TRIAL_COUNT,holdout=400):
    if type(episodes) is not int or not 1<=episodes<=3000:
        raise ValueError("training episodes must be 1..3000")
    if type(holdout) is not int or not 20<=holdout<=2000:
        raise ValueError("holdout outside 20..2000")
    out=Path(out)
    out.mkdir(parents=True,exist_ok=True)
    ledger=PortfolioLedger(out/"claim_q.sqlite")
    rng=random.Random(seed+489)
    training=[]
    checkpoints=[]
    try:
        if ledger.verify()["events"]:
            raise ValueError("new isolated BEAN research database required")
        for i in range(episodes):
            claim,oracle=make_case(seed,i,phase="train")
            action=decide(ledger,claim,rng,
                          epsilon=.22-.18*i/max(1,episodes-1))
            # Decision must precede any oracle score or Q update.
            decision={"index":i,"claim":asdict(claim),"action":action,
                      "claimed_confidence":claim.source_confidence,
                      "output":message(claim,action)}
            graded=accept_feedback(ledger,claim,action,oracle)
            if not graded["new"]:
                raise AssertionError("duplicate reward event")
            training.append({**decision,"oracle":asdict(oracle),
                             "outcome":graded})
            if i+1 in (250,500,1000,1500,2000,2500,episodes):
                checkpoints.append({"episode":i+1,"scoreboard":ledger.portfolio_context()})
        verified=ledger.verify()
        if verified["events"]!=episodes or verified["rewarded_events"]!=episodes:
            raise AssertionError("actual BEAN learning updates mismatch")
        # Holdout has never been called or used for policy selection.
        baseline_state=ledger.verify()
        frozen,held=evaluate(ledger,seed+90001,holdout)
        if ledger.verify()!=baseline_state:
            raise AssertionError("holdout must NOT update Q")
        first=ledger.event(APP,f"train_{seed}_000000")
        last=ledger.event(APP,f"train_{seed}_{episodes-1:06d}")
        if not first or not last:
            raise AssertionError("cold event retrieval lost training evidence")
        doc={"training":training,"holdout":held}
        raw=canonical(doc)
        packed=gzip.compress(raw,compresslevel=9,mtime=0)
        if gzip.decompress(packed)!=raw:
            raise AssertionError("lossless evidence corruption")
        (out/"original_trial_evidence.json.gz").write_bytes(packed)
        report={"schema":SCHEMA,"training_episodes":episodes,
                "actual_BEAN_Q_updates":verified["rewarded_events"],
                "learner":"Existing BEAN PortfolioLedger temporal-difference Q",
                "trainer":"synthetic hidden oracle, not actual authenticated internet evidence",
                "claim_types":list(KINDS),"train_domains":list(TRAIN_DOMAINS),
                "holdout_domains":list(HOLDOUT_DOMAINS),
                "holdout":frozen,"Q_verification":verified,
                "checkpoints":checkpoints,
                "ledger_context":ledger.state_context(app=APP,query="claim",max_bytes=4096),
                "archive":{"rows":episodes+holdout,
                           "source_bytes":len(raw),
                           "compressed_bytes":len(packed),
                           "source_sha256":hashlib.sha256(raw).hexdigest(),
                           "compressed_sha256":hashlib.sha256(packed).hexdigest(),
                           "reversible":True},
                "real_external_evidence_authenticated":False,
                "claims_promoted_to_verified":0,
                "language_model_calls":0}
        (out/"summary.json").write_text(json.dumps(report,indent=2,sort_keys=True)+"\n")
        return report
    finally:
        ledger.close()


def run_all(out,*,seeds=(11,23,47),episodes=3000,holdout=400):
    out=Path(out)
    if not seeds or len(set(seeds))!=len(seeds):
        raise ValueError("distinct experiment seeds required")
    results=[experiment(out/str(s),s,episodes=episodes,holdout=holdout) for s in seeds]
    methods=("BEAN_Q","boast_accepting","always_qualify","always_unknown")
    scores={name:round(sum(r["holdout"]["metrics"][name]["mean_reward"] for r in results)/len(results),6)
            for name in methods}
    stats={name:{
        key:sum(r["holdout"]["metrics"][name][key] for r in results)
        for key in ("false_tentative","supported_tentative","qualified","missed_success")
        } for name in methods}
    wins=[r["holdout"]["metrics"]["BEAN_Q"]["mean_reward"] >
          r["holdout"]["metrics"]["boast_accepting"]["mean_reward"]
          for r in results]
    summary={"schema":SCHEMA,"real_bean_Q_updates":episodes*len(results),
             "training_cases":episodes*len(results),
             "sealed_holdout_cases":holdout*len(results),
             "mean_heldout_utility":scores,"measured_counts":stats,
             "win_vs_uncritical_acceptor_by_seed":wins,
             "per_seed":[{"seed":r["holdout"]["seed"],
                          "metrics":r["holdout"]["metrics"],
                          "source_hash":r["holdout"]["source_manifest_sha256"],
                          "ledger_tip":r["Q_verification"]["tip"]} for r in results],
             "claim_scope":"synthetic_calibration_only",
             "independent_real_world_success_proven":False,
             "language_model_calls":0}
    (out/"comparison.json").write_text(json.dumps(summary,indent=2,sort_keys=True)+"\n")
    return summary
