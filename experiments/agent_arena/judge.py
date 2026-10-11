"""Credential-free independent BEAN vs Aider benchmark judge.

The judge checks that the starting fixture is truly red, then executes each
model-produced module against withheld tests in an isolated test directory.
A green *author* job never counts as a win. Both agents are scored on the
same cases, tests, pass fraction and environment. Agent failures are retained.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile

from experiments.agent_arena.cases import CASES, manifest

AGENTS = ("bean", "aider")


def sha(text):
    return hashlib.sha256(
        text.encode("utf-8") if isinstance(text, str) else text
    ).hexdigest()


def test_source(code, suite, *, timeout=30):
    """Execute a *tested candidate*, never on the credential-bearing author."""
    with tempfile.TemporaryDirectory(prefix="bean-arena-judge-") as t:
        root = Path(t)
        (root / "candidate.py").write_text(code, encoding="utf-8")
        (root / "test_holdout.py").write_text(suite, encoding="utf-8")
        env = dict(os.environ)
        for key in ("OPENROUTER_API_KEY", "GITHUB_TOKEN", "GH_TOKEN",
                    "AIDER_OPENAI_API_KEY", "BEAN_MODELS_TOKEN"):
            env.pop(key, None)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        try:
            proc = subprocess.run(
                [sys.executable, "-m", "unittest", "test_holdout", "-v"],
                cwd=root, env=env, capture_output=True, text=True,
                timeout=timeout,
            )
            output = proc.stdout + "\n" + proc.stderr
            total_match = re.search(r"Ran (\d+) tests? in", output)
            total = int(total_match.group(1)) if total_match else 0
            fails = re.search(r"failures=(\d+)", output)
            errors = re.search(r"errors=(\d+)", output)
            skipped = re.search(r"skipped=(\d+)", output)
            broken = (int(fails.group(1)) if fails else 0) + (
                int(errors.group(1)) if errors else 0
            ) + (int(skipped.group(1)) if skipped else 0)
            passed = max(0, total - broken)
            return {
                "status": "passed" if proc.returncode == 0 and total > 0
                          else "failed",
                "passed_tests": passed,
                "total_tests": total,
                "exit_code": proc.returncode,
                "test_output_sha256": sha(output),
                "failure_summary": [
                    line[:190] for line in output.splitlines()
                    if (line.startswith("FAIL: ") or line.startswith("ERROR: ")
                        or line.startswith("FAILED ") or line.startswith("Ran "))
                ][:15],
            }
        except subprocess.TimeoutExpired:
            return {"status": "timed_out", "passed_tests": 0,
                    "total_tests": 0, "failure_summary": ["timeout"]}


def evaluate(root):
    root = Path(root)
    expected = manifest()
    authored = json.loads((root / "author_manifest.json").read_text(encoding="utf-8"))
    for field in ("case_ids", "case_public_sha256", "oracle_sha256"):
        if authored.get(field) != expected.get(field):
            raise ValueError("author/evaluator manifest mismatch: " + field)
    if set(authored.get("agents_run", [])) != set(AGENTS):
        raise ValueError("both agents must participate")
    if set(authored.get("cases_run", [])) != set(CASES):
        raise ValueError("all announced cases must participate")

    result = {"schema": "bean.vs.aider.verdict.v1",
              "model_requested": authored["model_requested"],
              "aider_version": authored["aider_version"],
              "cases": {}, "agents": {}, "baseline": {},
              "classification": "INCONCLUSIVE", "notes": []}
    baseline_red = True
    for case, spec in CASES.items():
        baseline = test_source(spec["source"], spec["test"])
        result["baseline"][case] = baseline
        if baseline["status"] == "passed" or baseline["total_tests"] < 5:
            baseline_red = False
            result["notes"].append("Baseline not demonstrably red for " + case)
        scores = {}
        for agent in AGENTS:
            folder = root / "authors" / agent / case
            receipt = json.loads((folder / "receipt.json").read_text(encoding="utf-8"))
            target = folder / "candidate.py"
            verdict = {
                "author_status": receipt["status"],
                "agent": agent, "model_requested": receipt["model_requested"],
                "wall_seconds": receipt.get("wall_seconds"),
                "candidate_sha256": None,
                "status": "not_submitted",
                "passed_tests": 0,
                "total_tests": baseline["total_tests"],
                "usage": receipt.get("usage", {}),
            }
            if receipt["task_source_sha256"] != sha(spec["source"]):
                raise ValueError("original task source was changed during authoring")
            if receipt["status"] == "candidate_drafted_not_tested":
                if not target.exists():
                    raise ValueError("declared author candidate missing")
                code = target.read_text(encoding="utf-8")
                if sha(code) != receipt.get("candidate_sha256"):
                    raise ValueError("candidate digest does not match author receipt")
                verdict.update(test_source(code, spec["test"]))
                verdict["candidate_sha256"] = sha(code)
            elif target.exists():
                raise ValueError("non-candidate writer unexpectedly emitted executable source")
            scores[agent] = verdict
        result["cases"][case] = scores
    for agent in AGENTS:
        total_pass = sum(result["cases"][c][agent]["passed_tests"] for c in CASES)
        total_tests = sum(result["cases"][c][agent]["total_tests"] for c in CASES)
        tasks_passed = sum(result["cases"][c][agent]["status"] == "passed"
                           for c in CASES)
        result["agents"][agent] = {
            "passed_tests": total_pass, "total_tests": total_tests,
            "tasks_passed": tasks_passed, "tasks_total": len(CASES),
            "score_percent": round(100*total_pass/total_tests, 2) if total_tests else 0,
        }
    # Distinguish a failed opponent / provider tool launch from a true loss.
    aider_infra_failed = any(
        result["cases"][c]["aider"]["author_status"] == "tool_or_transport_failure"
        for c in CASES
    )
    provider_failed = any(
        result["cases"][c][a]["author_status"] == "provider_failure"
        for c in CASES for a in AGENTS
    )
    same_model_config = all(
        result["cases"][c][a]["model_requested"] == result["model_requested"]
        for c in CASES for a in AGENTS
    )
    if not baseline_red or aider_infra_failed or provider_failed or not same_model_config:
        result["classification"] = "INCONCLUSIVE"
        result["notes"].append(
            "Test baseline, provider availability, or fair tool/model setup not established."
        )
    else:
        b = result["agents"]["bean"]
        a = result["agents"]["aider"]
        bscore = (b["tasks_passed"], b["passed_tests"])
        ascore = (a["tasks_passed"], a["passed_tests"])
        result["classification"] = (
            "BEAN_WIN" if bscore > ascore else
            "AIDER_WIN" if ascore > bscore else "TIE"
        )
    result["notes"].append(
        "Pilot with two synthetic tasks; not a general superiority claim. "
        "Both requested the same explicit model but provider-side route "
        "identity and exact LLM call counts for Aider were not independently audited."
    )
    evidence = json.dumps(result, sort_keys=True, separators=(",", ":")).encode()
    result["evidence_sha256"] = sha(evidence)
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--artifacts", type=Path, default=Path("_agent_arena"))
    p.add_argument("--output", type=Path, default=Path("_arena_verdict/verdict.json"))
    args = p.parse_args()
    verdict = evaluate(args.artifacts)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(verdict, indent=2, sort_keys=True) + "\n",
                           encoding="utf-8")
    print(json.dumps(verdict, indent=2, sort_keys=True))
    return 0 if verdict["classification"] != "INCONCLUSIVE" else 2


if __name__ == "__main__":
    raise SystemExit(main())
