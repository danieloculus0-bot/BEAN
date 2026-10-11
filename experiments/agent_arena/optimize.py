"""BEAN vs Aider, Round 2: optimize their actual 16/16-passing Round 1 code.

The same original task specifications apply, but this round starts from each
agent's *own* frozen, model-written winning source (not a human reference).
Both use the same free model and see the same performance objective, with
independent hidden correctness + stress and timing evaluation held separately.
No author stage executes generated source.
"""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
from experiments.agent_arena import author, cases

ORIGINAL_RUN_ID = 38110050070
OPTIMIZE_GOAL = (
    "\n\nROUND 2 OPTIMIZATION OBJECTIVE: Your supplied source already passed the "
    "original task's correctness tests. Improve its execution performance "
    "on substantial inputs while preserving every externally observable "
    "behavior and API. Avoid changing results, mutation behavior, timezone "
    "eligibility, deny-overrides semantics, or handling of cycles. "
    "Favor efficient asymptotic work and reduce redundant processing. "
    "The independent evaluator will rerun the original 8 hidden tests and "
    "additional unseen deterministic stress/property cases and measure "
    "runtime with repeated same-machine medians. You DO NOT receive those "
    "tests, their results, reference fixes, or scores while editing. "
    "Optimize candidate.py in place. No additional packages."
)

def read_frozen_round1(root):
    root = Path(root)
    frozen = json.loads((root / "author_manifest.json").read_text(encoding="utf-8"))
    expected = cases.manifest()
    for key in ("case_public_sha256", "oracle_sha256", "case_ids"):
        if frozen.get(key) != expected[key]:
            raise ValueError("Round 1 artifact is not the pinned test/case manifest")
    if frozen.get("model_requested") != author.MODEL:
        raise ValueError("Cannot change the baseline model between rounds")
    if set(frozen.get("agents_run", ())) != {"bean", "aider"}:
        raise ValueError("Round 1 did not contain both agents")
    if set(frozen.get("cases_run", ())) != set(cases.CASES):
        raise ValueError("Round 1 missed a preregistered case")
    baseline = {}
    for agent in ("bean", "aider"):
        for name, spec in cases.CASES.items():
            folder = root / "authors" / agent / name
            receipt = json.loads((folder / "receipt.json").read_text(encoding="utf-8"))
            file = folder / "candidate.py"
            if file.is_symlink():
                raise ValueError("source artifact symlink refused")
            content = file.read_text(encoding="utf-8")
            if (receipt.get("status") != "candidate_drafted_not_tested"
                    or receipt.get("candidate_sha256") != author.sha(content)
                    or receipt.get("task_source_sha256") != author.sha(spec["source"])):
                raise ValueError("Original source/receipt SHA mismatch")
            baseline[(agent, name)] = content
    return baseline, frozen

def optimize(root, out, key, *, bean_writer=author.bean_author, aider_writer=author.aider_author):
    baseline, frozen = read_frozen_round1(root)
    out = Path(out)
    manifest = {
        **cases.manifest(),
        "schema": "bean.vs.aider.optimization.author.v1",
        "original_run_id": ORIGINAL_RUN_ID,
        "model_requested": author.MODEL,
        "aider_version": author.AIDER_VERSION,
        "tasks": list(cases.CASES),
        "agents": ["bean", "aider"],
        "initial_sha256": {agent: {name: author.sha(baseline[(agent, name)])
                                    for name in cases.CASES}
                           for agent in ("bean", "aider")},
    }
    for agent in ("bean", "aider"):
        for name in cases.CASES:
            original = baseline[(agent, name)]
            spec = cases.public_case(name)
            spec.update({
                "source": original,
                "source_sha256": author.sha(original),
                "prompt": spec["prompt"] + OPTIMIZE_GOAL,
            })
            receipt, proposal = (
                bean_writer(spec, key) if agent == "bean" else aider_writer(spec, key)
            )
            target = out / "authors" / agent / name
            target.mkdir(parents=True, exist_ok=True)
            if proposal is not None:
                (target / "candidate.py").write_text(proposal, encoding="utf-8")
                receipt["candidate_sha256"] = author.sha(proposal)
            receipt.update(agent=agent, case=name, model_requested=author.MODEL,
                           original_sha256=author.sha(original),
                           objective="optimize_correctness_preserving",
                           original_run_id=ORIGINAL_RUN_ID)
            author.write_json(target / "receipt.json", receipt)
    author.write_json(out / "optimization_manifest.json", manifest)
    return manifest

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--baseline", type=Path, default=Path("_round1"))
    p.add_argument("--out", type=Path, default=Path("_round2"))
    args = p.parse_args()
    result = optimize(args.baseline, args.out,
                      os.environ.get("OPENROUTER_API_KEY", ""))
    print(json.dumps({"schema": result["schema"],
                      "source_run_id": result["original_run_id"],
                      "agents": result["agents"], "tasks": result["tasks"]},
                     sort_keys=True))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
