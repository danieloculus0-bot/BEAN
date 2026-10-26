"""Blind benchmark: generated hypotheses on unseen numeric-control tasks.

World construction and hidden correct response live only in the environment.
The learner sees unlabeled sensor vectors plus reward for its tried actions.
Tested against an equal-budget random-probe learner and a no-learning baseline.
"""
from __future__ import annotations
import argparse
import json
import random
import statistics
from pathlib import Path
from bean.learning.active_hypothesis import act, discover


class World:
    def __init__(self, world_id, kind):
        self.world_id = world_id
        self.kind = kind
        rng = random.Random(world_id * 179)
        self.a, self.b = rng.sample(range(4), 2)
        self.polarity = rng.choice((-1, 1))
        self.constant = rng.choice((-1, 0, 1))

    def observe(self, case):
        rng = random.Random(self.world_id * 1000003 + int(case) * 13)
        return tuple(rng.uniform(-1, 1) for _ in range(4))

    def correct_action(self, case):
        state = self.observe(case)
        if self.kind == "constant":
            return self.constant
        if self.kind == "channel":
            signal = state[self.a] * self.polarity
        elif self.kind == "difference":
            signal = (state[self.a] - state[self.b]) * self.polarity
        elif self.kind == "parity":
            signal = state[self.a] * state[self.b] * self.polarity
        else:
            raise ValueError("Unknown evaluation fixture")
        return 1 if signal > 0 else -1 if signal < 0 else 0

    def feedback(self, case, action):
        # The learner only receives the reward for the action it *actually* tests.
        return 1.0 if action == self.correct_action(case) else 0.0


def evaluate(learned, world, heldout):
    if learned["selected_rule"] is None:
        return {"correct": 0, "abstained": len(heldout), "attempted": 0}
    accuracy = sum(act(learned["selected_rule"], world.observe(case)) ==
                   world.correct_action(case) for case in heldout)
    return {"correct": accuracy, "abstained": 0, "attempted": len(heldout)}


def benchmark(worlds_per_family=35, budgets=(3, 6, 12)):
    families=("channel", "difference", "constant", "parity")
    rows=[]
    for family_index, family in enumerate(families):
        for world_index in range(worlds_per_family):
            world=World(family_index*1000+world_index+100, family)
            training=[str(100+i) for i in range(40)]
            blind=[str(50000+i) for i in range(60)]
            for budget in budgets:
                arms={}
                for method in ("disagreement", "passive"):
                    report=discover(probe_ids=training,
                        observe=world.observe, reward=world.feedback,
                        budget=budget, method=method,
                        seed=world_index*100+budget)
                    arms[method]={**evaluate(report,world,blind),
                                  "selected":report["selected_rule"],
                                  "probes":report["probes_used"],
                                  "reward_calls":report["reward_calls"]}
                baseline=sum(world.feedback(case, 0) for case in blind)
                rows.append({"world":world.world_id,"family":family,
                             "budget":budget,"arms":arms,
                             "always_stay_correct":int(baseline),
                             "blind_cases":len(blind)})
    summary={}
    for family in families:
        for budget in budgets:
            part=[r for r in rows if r["family"]==family and r["budget"]==budget]
            summary[family+"_"+str(budget)]={
                "worlds":len(part),"blind_per_world":60,
                "active_correct":sum(r["arms"]["disagreement"]["correct"] for r in part),
                "passive_correct":sum(r["arms"]["passive"]["correct"] for r in part),
                "stay_correct":sum(r["always_stay_correct"] for r in part),
                "active_rule_accepted":sum(r["arms"]["disagreement"]["selected"] is not None for r in part),
                "passive_rule_accepted":sum(r["arms"]["passive"]["selected"] is not None for r in part),
                "active_abstentions":sum(r["arms"]["disagreement"]["abstained"] for r in part),
                "passive_abstentions":sum(r["arms"]["passive"]["abstained"] for r in part),
                "probe_reward_calls_per_world":budget*3,
                "blind_data_seen_by_agent":False,
            }
    report={
        "schema":"bean.active_hypothesis.blind_benchmark.v1",
        "methods":"generated rule + active disagreement probes vs generated rule + passive random probes",
        "worlds":len(families)*worlds_per_family,
        "no_supplied_correct_sensor":True,
        "no_supplied_correct_action_mapping":True,
        "hypothesis_grammar_is_handwritten":True,
        "blind_data_not_used_for_policy_selection":True,
        "family_definitions":"channel, channel difference, constant, and out-of-grammar parity",
        "model_independently_builds_grammar":False,
        "summary":summary,"individual_world_results":rows,
        "interpretation":"Bounded numerical program search, not open-domain or unrestricted abstract reasoning.",
    }
    return report


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--worlds",type=int,default=35)
    parser.add_argument("--out",type=Path,default=Path("active-abstraction-proof/results.json"))
    args=parser.parse_args()
    if not 2 <= args.worlds <= 100:
        raise ValueError("Requires 2..100 held-out worlds per family")
    result=benchmark(args.worlds)
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps(result["summary"],indent=2))

if __name__=="__main__":
    main()
