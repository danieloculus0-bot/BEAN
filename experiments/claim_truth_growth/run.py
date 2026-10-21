"""Run three sealed model-free experiments: BEAN learns not to invent success."""
from __future__ import annotations
import argparse
import json
from pathlib import Path

from bean.evaluation.claim_calibration_growth import run_all

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--out",type=Path,required=True)
    parser.add_argument("--episodes",type=int,default=3000)
    parser.add_argument("--holdout",type=int,default=400)
    args=parser.parse_args()
    result=run_all(args.out,episodes=args.episodes,holdout=args.holdout)
    print(json.dumps({
        "BEAN_Q_updates":result["real_bean_Q_updates"],
        "training_examples":result["training_cases"],
        "unseen_cases":result["sealed_holdout_cases"],
        "mean_holdout_utility":result["mean_heldout_utility"],
        "incorrect_positive_claims":{k:v["false_tentative"]
                                      for k,v in result["measured_counts"].items()},
        "justified_provisional_claims":{k:v["supported_tentative"]
                                        for k,v in result["measured_counts"].items()},
        "wins_vs_accepting_bold_claims":result["win_vs_uncritical_acceptor_by_seed"],
        "actual_external_facts_authenticated":False,
        "language_model_calls":result["language_model_calls"],
    },indent=2))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
