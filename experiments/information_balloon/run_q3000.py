"""Execute exactly 3,000 real BEAN Q-controlled reversible compression trials."""
from __future__ import annotations
import argparse
import gzip
import hashlib
import json
import os
from pathlib import Path
import platform
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from bean.optimization.information_balloon import canonical,unpack
from bean.optimization.information_balloon_q import run_learning
from bean.optimization.learning_quota import quota
import base64


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--out-dir",type=Path,required=True)
    p.add_argument("--episodes",type=int,default=3000)
    p.add_argument("--eval-cases",type=int,default=120)
    p.add_argument("--verified-fixes-json",type=Path,default=None,
                   help="Independent evaluator-signed BEAN-only bugfix receipts")
    options=p.parse_args()
    fixes=(json.loads(options.verified_fixes_json.read_text(encoding="utf-8"))
           if options.verified_fixes_json else [])
    verifier_hex=os.environ.get("BEAN_INDEPENDENT_QUOTA_HMAC_HEX","")
    verifier_key=bytes.fromhex(verifier_hex) if verifier_hex else None
    initial=quota(target=options.episodes,q_episodes=0,
                  repair_receipts=fixes,evaluator_key=verifier_key)
    actual_episodes=initial["remaining"]
    if not actual_episodes:
        raise ValueError("all quota units earned by signed BEAN fixes; no Q trials necessary")
    options.out_dir.mkdir(parents=True,exist_ok=True)
    report,trials=run_learning(
        options.out_dir/"bean-balloon-q.sqlite",
        episodes=actual_episodes,eval_cases=options.eval_cases)
    report["research_quota"]=quota(
        target=options.episodes,q_episodes=report["q_updates"],
        repair_receipts=fixes,evaluator_key=verifier_key)
    if report["research_quota"]["remaining"] != 0:
        raise AssertionError("Q trials plus signed BEAN repairs did not complete quota")
    source_lines=[]
    for row in trials:
        source=base64.b64decode(row["source_b64"],validate=True)
        archive=base64.b64decode(row["package_b64"],validate=True)
        if unpack(archive)!=source:
            raise AssertionError("cold evidence reconstruction failed")
        source_lines.append(canonical(row)+b"\n")
    raw=b"".join(source_lines)
    packed=gzip.compress(raw,compresslevel=9,mtime=0)
    if gzip.decompress(packed)!=raw or len(trials)!=actual_episodes:
        raise AssertionError("evidence archive lost a source or trial")
    (options.out_dir/"trials_with_original_and_package.jsonl.gz").write_bytes(packed)
    report["cold_archive"]={
        "trial_rows":len(trials),
        "source_bytes":len(raw),
        "package_bytes":len(packed),
        "source_sha256":hashlib.sha256(raw).hexdigest(),
        "package_sha256":hashlib.sha256(packed).hexdigest(),
        "all_roundtrips_exact":True}
    report["worker"]={"system":platform.system(),
                      "python":platform.python_version(),
                      "revision":os.environ.get("GITHUB_SHA","local_unpinned")}
    (options.out_dir/"summary.json").write_bytes(
        json.dumps(report,sort_keys=True,indent=2).encode()+b"\n")
    print(json.dumps({
        "compression_trials":report["real_compression_evaluations"],
        "quota":report["research_quota"],
        "BEAN_q_updates":report["q_updates"],
        "ledger":report["ledger_verification"],
        "validation_progress":[{
            "episode":x["episode"],
            "q_policy_mean_reward":x["validation"]["mean_reward"]["bean"],
            "standard_mean_reward":x["validation"]["mean_reward"]["standard"]}
            for x in report["checkpoints"]],
        "holdout":report["independent_holdout"],
        "cold_archive":report["cold_archive"]},indent=2))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
