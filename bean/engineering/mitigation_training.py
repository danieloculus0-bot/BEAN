"""Teach BEAN's *existing* Q learner using measured engineering-screen outcomes.

Training signals come from a deterministic elastic-beam SIMULATOR, not a
real FEA solver, a building code, a constructed building, or an independent
material experiment. The purpose is to retain/rank interventions and test
transfer to held-out parameter values, while preserving failures.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import random

from bean.learning.runtime import LearningRuntime
from .jobsite import analyze_beams

ACTIONS = ("increase_depth", "shorten_span", "reduce_line_load")
DOMAIN = "engineering_member_mitigation.v1"


def beam_case(seed):
    rng = random.Random(seed)
    member = {
        "id": "B",
        "width_in": 1.5,
        "depth_in": rng.choice([3.5, 5.5, 7.25]),
        "span_ft": rng.choice([8., 10., 12., 14., 16.]),
        "load_plf": rng.choice([30., 45., 60., 85., 110.]),
        "modulus_psi": rng.choice([1000000., 1200000., 1400000.]),
        "allowable_bending_psi": rng.choice([600., 900., 1200.]),
        "allowable_shear_psi": rng.choice([75., 120., 150.]),
        "deflection_limit_ratio": rng.choice([240., 360., 480.]),
    }
    # These three synthetic site opportunities deliberately have different
    # feasible amounts of change. They are NOT inferred from a real building.
    # Equal depth/span percentage changes can be algebraically equivalent
    # under ideal beam models and teach BEAN nothing about selection.
    member["mitigation_context"] = rng.choice(
        ("section_opportunity","support_opportunity","load_opportunity")
    )
    return member


# Dimensions are purely teaching scenarios, not purchased beam sizes,
# true support locations, permission to add supports or verified costs.
TRAINING_FACTORS = {
    "section_opportunity": {
        "increase_depth":1.50, "shorten_span":.95,"reduce_line_load":.95
    },
    "support_opportunity": {
        "increase_depth":1.10,"shorten_span":.65,"reduce_line_load":.90
    },
    "load_opportunity": {
        "increase_depth":1.10,"shorten_span":.95,"reduce_line_load":.50
    },
}


def intervention(member, action):
    """A synthetic comparison, NEVER permission to modify a building."""
    copy = dict(member)
    context = copy.get("mitigation_context")
    if context not in TRAINING_FACTORS:
        raise ValueError("Missing bounded mitigation opportunity context")
    if action not in TRAINING_FACTORS[context]:
        raise ValueError("Unknown mitigation")
    factor = TRAINING_FACTORS[context][action]
    if action == "increase_depth":
        copy["depth_in"] *= factor
    elif action == "shorten_span":
        copy["span_ft"] *= factor
    elif action == "reduce_line_load":
        copy["load_plf"] *= factor
    return copy


def experience(member, action):
    original = analyze_beams([member])["members"][0]
    changed = analyze_beams([intervention(member, action)])["members"][0]
    baseline = original["worst_utilization"]
    after = changed["worst_utilization"]
    # Reward reflects scalar utilization reduction only. It does not price
    # labor, altered foundations, bracing, approvals or life-cycle performance.
    reduction = (baseline-after)/max(baseline, 1e-12)
    return {
        "action": action, "before_utilization": baseline,
        "after_utilization": after, "relative_reduction": reduction,
        "governing": original["governing"],
        "engineering_authority": "none",
    }


def _state(member):
    original = analyze_beams([member])["members"][0]
    peak = original["worst_utilization"]
    severity = "over_limit" if peak > 1 else "within_supplied_limits"
    context=member.get("mitigation_context")
    if context not in TRAINING_FACTORS:
        raise ValueError("Unknown mitigation scenario opportunity")
    return {"governing": original["governing"], "severity": severity,
            "constraint_context": context,
            "geometry": "rectangular", "loading": "uniform_simple_support"}


def _pick_greedy(svc, state):
    key = svc.policy.key(svc.scoped(DOMAIN, state))
    q = svc.policy.q.get(key, [0.0]*len(ACTIONS))
    return ACTIONS[max(range(len(ACTIONS)), key=lambda i:q[i])]


def _compare_holdout(svc, cases):
    outcomes=[]
    for member in cases:
        state=_state(member)
        selected=_pick_greedy(svc,state)
        learned=experience(member, selected)
        baseline=experience(member, ACTIONS[0])
        outcomes.append({
            "state":state,
            "member":member,
            "bean_action":selected,
            "bean_reduction":learned["relative_reduction"],
            "baseline_action":ACTIONS[0],
            "baseline_reduction":baseline["relative_reduction"],
        })
    return {
        "episodes": len(outcomes),
        "baseline_mean": sum(x["baseline_reduction"] for x in outcomes)/len(outcomes),
        "bean_mean": sum(x["bean_reduction"] for x in outcomes)/len(outcomes),
        "outcomes":outcomes,
    }


def run_curriculum(root="runs/bean_jobsite_learning", *, train_cases=100,
                   holdout_cases=30, seed=11):
    if type(train_cases) is not int or train_cases < 10:
        raise ValueError("Need at least ten synthetic training cases")
    if type(holdout_cases) is not int or holdout_cases < 30:
        raise ValueError("Need at least 30 held-out cases for a scored checkpoint")
    root=Path(root)
    root.mkdir(parents=True,exist_ok=True)
    # The seeds are deliberately disjoint. This is parameter holdout, not a
    # different mechanics model or independently measured FEA ground truth.
    train=[beam_case(seed*100000 + i) for i in range(train_cases)]
    holdout=[beam_case(seed*100000 + 10000 + i) for i in range(holdout_cases)]
    svc=LearningRuntime(root/"sponge_q.sqlite",actions=ACTIONS,seed=seed)
    updates=0
    records=[]
    checkpoint=None
    try:
        pre=_compare_holdout(svc,holdout)
        for idx, member in enumerate(train):
            state=_state(member)
            for action in ACTIONS:
                episode=f"case-{idx:05d}-{action}"
                choice=svc.choose(
                    episode_id=episode,domain=DOMAIN,state=state,
                    location_ref=["beam",idx],legal_actions=[action])
                if choice["action"]!=action:
                    raise RuntimeError("Learning action differs from evaluated mitigation")
                observation=experience(member,action)
                feedback=svc.feedback(
                    episode_id=episode,reward=observation["relative_reduction"],done=True)
                if not feedback["learned"]:
                    raise RuntimeError("BEAN failed to learn engineering feedback")
                updates += 1
                records.append({"case_id":idx,"state":state,"observation":observation})
        post=_compare_holdout(svc,holdout)
        payload={
            "schema":"bean.engineering_mitigation_training.v1",
            "source":"local_deterministic_beam_simulator_with_varying_synthetic_opportunities",
            "synthetic_mitigation_factors":TRAINING_FACTORS,
            "reasoning_learner":"existing BEAN SpongeTD Q learning",
            "train_scenarios":train_cases,
            "trained_choices":updates,
            "actions":list(ACTIONS),
            "training_observations":records,
            "heldout_before":pre,
            "heldout_after":post,
            "measured_heldout_gain":post["bean_mean"]-post["baseline_mean"],
            "learned_model_weights":False,
            "trained_q_values":True,
            "independent_real_fea_reference":False,
            "engineering_validation":"not_established",
        }
        # SHA is over all measured evaluations before recording the checkpoint.
        evidence=json.dumps(payload,sort_keys=True,separators=(",",":"),allow_nan=False)
        digest=hashlib.sha256(evidence.encode("utf-8")).hexdigest()
        checkpoint=svc.checkpoint(
            baseline=post["baseline_mean"],candidate=post["bean_mean"],
            samples=holdout_cases,evaluation_sha256=digest)
        payload["checkpoint"] = checkpoint
        payload["evaluation_sha256"] = digest
        (root/"engineering_learning.json").write_text(
            json.dumps(payload,indent=2,allow_nan=False)+"\n",encoding="utf-8")
        # Write every observation; never keep only examples that improved.
        (root/"engineering_training_ledger.jsonl").write_text(
            "".join(json.dumps(x,sort_keys=True,allow_nan=False)+"\n" for x in records),
            encoding="utf-8")
    finally:
        svc.close()
    reopened=LearningRuntime(root/"sponge_q.sqlite",actions=ACTIONS,seed=seed)
    try:
        if reopened.status()["q_updates"]!=updates or reopened.status()["checkpoints"]!=1:
            raise RuntimeError("BEAN engineering Q memory did not recover after restart")
    finally:
        reopened.close()
    return payload


def main():
    p=argparse.ArgumentParser(description="Teach BEAN mitigations on bounded synthetic beams")
    p.add_argument("--out",default="runs/bean_jobsite_learning")
    p.add_argument("--train",type=int,default=100)
    p.add_argument("--holdout",type=int,default=30)
    p.add_argument("--seed",type=int,default=11)
    args=p.parse_args()
    result=run_curriculum(args.out,train_cases=args.train,
                          holdout_cases=args.holdout,seed=args.seed)
    print(json.dumps({
      "trained_choices":result["trained_choices"],
      "heldout_baseline":result["heldout_after"]["baseline_mean"],
      "heldout_bean":result["heldout_after"]["bean_mean"],
      "gain":result["measured_heldout_gain"],
      "checkpoint_quality":result["checkpoint"],
      "engineer_status":"synthetic simulation, not independent FEA validation",
    },indent=2))


if __name__=="__main__":
    main()
