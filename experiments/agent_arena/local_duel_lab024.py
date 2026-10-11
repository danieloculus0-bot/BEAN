"""Lab024: real BEAN-vs-upstream-Aider iterative coding benchmark on local Ollama.

Three edit rounds per agent and task. Each agent sees only the public
specification, its own previous source, and AGGREGATE development scores.
BEAN keeps an actual hash-chained SQLite feedback journal; Aider is the
untouched installed upstream CLI. Both use the identical locally installed
model. An isolated, networkless Docker container runs developer feedback;
a SEPARATE credential-free job judges model-written files on hidden tests.
No generated program is executed in the Ollama/model-authoring process.
"""
from __future__ import annotations
import argparse
import ast
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
from urllib.error import URLError

from bean.evaluation.lab023_ollama import Ollama, OllamaUnavailable
from bean.optimization.autodev import Journal
from experiments.agent_arena.author import model_written_module, sha, write_json
from experiments.agent_arena.cases import CASES, public_case, manifest
from experiments.agent_arena.judge import test_source

ROUNDS = 3
AGENTS = ("bean", "aider")
SCHEMA = "bean.lab024.ollama-specialist-arena.v1"
# Development tests ARE NOT any of the hidden suite in cases.py.
DEVELOPMENT = {
    "ledger_revisions": '''import unittest
from candidate import replay
class Dev(unittest.TestCase):
    def test_latest(self):
        x=[dict(id="e",revision=0,account="a",delta=4,at="2026-10-10T00:00:00Z"),
           dict(id="e",revision=2,account="a",delta=7,at="2026-10-10T00:00:00Z")]
        self.assertEqual(replay(x,"2026-10-10T01:00:00Z"),{"a":7})
    def test_distinct(self):
        x=[dict(id="x",revision=1,account="a",delta=1,at="2026-10-10T00:00:00Z"),
           dict(id="y",revision=1,account="a",delta=2,at="2026-10-10T00:00:00Z")]
        self.assertEqual(replay(x,"2026-10-10T01:00:00Z"),{"a":3})
    def test_late(self):
        x=[dict(id="x",revision=1,account="a",delta=7,at="2026-10-10T03:00:00Z")]
        self.assertEqual(replay(x,"2026-10-10T01:00:00Z"),{})
if __name__=="__main__": unittest.main()
''',
    "permission_graph": '''import unittest
from candidate import can_access
class Dev(unittest.TestCase):
    def test_direct(self):
        self.assertTrue(can_access("a","read",{},{"a":["read"]},{}))
    def test_parent(self):
        self.assertTrue(can_access("a","read",{"a":["team"]},{"team":["read"]},{}))
    def test_deny(self):
        self.assertFalse(can_access("a","read",{"a":["team"]},{"a":["read"]},{"team":["read"]}))
if __name__=="__main__": unittest.main()
''',
}

def clean_environment():
    """Explicitly permit only the local Ollama endpoint, not credential-bearing env."""
    result = {
        "PATH": os.environ.get("PATH", ""),
        "HOME": os.environ.get("HOME", "/tmp"),
        "OLLAMA_API_BASE": "http://127.0.0.1:11434",
        "OLLAMA_CONTEXT_LENGTH": "8192",
        "AIDER_ANALYTICS": "false", "PYTHONDONTWRITEBYTECODE": "1",
        "NO_COLOR": "1", "PYTHONUNBUFFERED": "1",
    }
    return result


def development_score(source, name, *, runner=subprocess.run):
    """Only development checks in ephemeral offline resource-limited Docker."""
    if name not in DEVELOPMENT:
        raise ValueError("unknown development suite")
    with tempfile.TemporaryDirectory(prefix="bean-lab024-dev-") as temp:
        root = Path(temp)
        root.chmod(0o755)
        (root / "candidate.py").write_bytes(source.encode("utf-8"))
        (root / "test_development.py").write_bytes(DEVELOPMENT[name].encode())
        for path in root.iterdir():
            path.chmod(0o644)
        command = [
            "docker", "run", "--rm", "--network", "none", "--read-only",
            "--cpus", "1", "--memory", "256m", "--pids-limit", "64",
            "--security-opt", "no-new-privileges", "--cap-drop", "ALL",
            "--user", "65534:65534",
            "--mount", "type=bind,source="+str(root)+",target=/study,readonly",
            "--workdir", "/study", "-e", "PYTHONDONTWRITEBYTECODE=1",
            "python:3.12-slim", "python", "-m", "unittest",
            "test_development", "-v",
        ]
        try:
            p = runner(command, capture_output=True, text=True, timeout=35,
                       env=clean_environment())
            output = (p.stdout + "\n" + p.stderr)[-32000:]
            total = re.search(r"Ran (\d+) tests? in", output)
            n = int(total.group(1)) if total else 0
            fail = re.search(r"failures=(\d+)", output)
            err = re.search(r"errors=(\d+)", output)
            skips = re.search(r"skipped=(\d+)", output)
            bad = sum(int(m.group(1)) for m in (fail, err, skips) if m)
            return {"passed": max(0, n - bad), "total": n,
                    "status": "passed" if p.returncode == 0 and n == 3 else "failed",
                    "output_sha256": sha(output),
                    "developer_suite_sha256": sha(DEVELOPMENT[name]),
                    "isolation": "docker-network-none"}
        except (OSError, subprocess.TimeoutExpired) as exc:
            return {"passed": 0, "total": 0, "status": "infrastructure_failure",
                    "reason": type(exc).__name__,
                    "developer_suite_sha256": sha(DEVELOPMENT[name]),
                    "isolation": "docker-network-none"}


def bean_round(client, spec, previous, count, round_num):
    """Use the actual BEAN source-edit validation, not a stored solution."""
    objective = spec["prompt"]
    if previous:
        objective += ("\nPrevious candidate development score: " +
                      str(count["passed"]) + "/" + str(count["total"]) +
                      ". Repair unmet edge cases and retain correct behavior." +
                      "\nOwn previous candidate:\n" + previous)
    prompt = (
        "You are BEAN, an adaptive Python source-repair agent. Write a "
        "COMPLETE updated Python module, ONLY executable Python code. "
        "Preserve the public function name and signature. "
        "Never output markdown or an explanation. You have only the "
        "public requirements and aggregate development feedback. "
        "No external network, shell operations, or additional packages.\n\n"
        "PUBLIC REQUIREMENTS:\n" + objective +
        "\n\nBASE CODE:\n" + spec["source"]
    )
    try:
        raw = client.complete(prompt, tokens=4300, temperature=0.15)
        source, _ = model_written_module(spec["source"], raw)
        return source, {"status": "candidate_drafted_not_tested",
                        "model_requested": client.route,
                        "model_served": [client.route], "request_count": 1}
    except (OllamaUnavailable, ValueError, SyntaxError) as exc:
        return None, {"status": "invalid_candidate",
                      "model_requested": client.route,
                      "model_served": [client.route],
                      "reason": type(exc).__name__, "request_count": 1}


def aider_round(client, spec, previous, count, round_num, *, runner=subprocess.run):
    """Unmodified Aider 0.86.2 uses the same Ollama model and task facts."""
    with tempfile.TemporaryDirectory(prefix="bean-lab024-aider-") as tmp:
        root = Path(tmp)
        candidate_file = root / "candidate.py"
        candidate_file.write_bytes((previous or spec["source"]).encode())
        prompt = spec["prompt"]
        if previous:
            prompt += ("\nPrevious candidate development score: " +
                       str(count["passed"]) + "/" + str(count["total"]) +
                       ". Make a better repair while preserving what worked.")
        (root / "task.txt").write_text(prompt + "\n", encoding="utf-8")
        command = [
            "aider", "--yes", "--no-git", "--no-check-update",
            "--no-auto-commits", "--no-stream", "--no-show-model-warnings",
            "--edit-format", "whole",
            "--model", "ollama_chat/" + client.model,
            "--message-file", "task.txt", "candidate.py",
        ]
        try:
            p = runner(command, cwd=root, env=clean_environment(),
                       capture_output=True, text=True, timeout=230)
            source = candidate_file.read_text(encoding="utf-8")
            if source == (previous or spec["source"]):
                return None, {"status": "no_candidate", "model_requested": client.route,
                              "model_served": [client.route], "exit_code": p.returncode,
                              "tool_log_sha256": sha(p.stdout + p.stderr),
                              "request_count": None}
            changed, _ = model_written_module(spec["source"], source)
            return changed, {"status": "candidate_drafted_not_tested",
                             "model_requested": client.route,
                             "model_served": [client.route],
                             "exit_code": p.returncode,
                             "tool_log_sha256": sha(p.stdout + p.stderr),
                             "request_count": None}
        except (OSError, subprocess.TimeoutExpired, ValueError,
                SyntaxError) as exc:
            return None, {"status": "tool_or_transport_failure",
                          "model_requested": client.route,
                          "model_served": [],
                          "reason": type(exc).__name__,
                          "request_count": None}


def author(root, *, client=None, bean_writer=bean_round, aider_writer=aider_round,
           scorer=development_score):
    root = Path(root)
    if root.exists() and any(root.iterdir()):
        raise ValueError("Use a fresh output directory; old candidates must not mix")
    client = client or Ollama()
    client.preflight()
    root.mkdir(parents=True, exist_ok=True)
    journal = Journal(root / "bean-journal.sqlite")
    items = {}
    try:
        for idx, (name, spec) in enumerate((k, public_case(k)) for k in CASES):
            items[name] = {}
            order = AGENTS if idx % 2 == 0 else AGENTS[::-1]
            for agent in order:
                previous, feedback = None, {"passed": 0, "total": 3}
                attempts = []
                for round_num in range(1, ROUNDS + 1):
                    worker = bean_writer if agent == "bean" else aider_writer
                    source, receipt = worker(client, spec, previous, feedback, round_num)
                    success = source is not None and receipt.get("status") == "candidate_drafted_not_tested"
                    if success:
                        if sha(spec["source"]) == sha(source):
                            raise ValueError("unchanged source cannot be a repair")
                        filename = root / "candidates" / name / agent / ("round"+str(round_num)+".py")
                        filename.parent.mkdir(parents=True, exist_ok=True)
                        filename.write_bytes(source.encode())
                        score = scorer(source, name)
                        if score["status"] == "infrastructure_failure":
                            raise RuntimeError("development sandbox failed")
                        previous, feedback = source, score
                    else:
                        score = {"status": "not_submitted", "passed": 0, "total": 3}
                    result = {**receipt, "round": round_num,
                              "candidate_sha256": sha(source) if success else None,
                              "source_sha256": spec["source_sha256"],
                              "development": score}
                    attempts.append(result)
                    if agent == "bean":
                        journal.append({
                            "objective": name, "iteration": round_num,
                            "outcome": result["status"],
                            "source_sha256": result["candidate_sha256"],
                            "developer_passed": score["passed"],
                            "developer_total": score["total"],
                            "model_requested": client.route,
                            "feedback_only": "aggregate",
                        })
                ranked = [x for x in attempts if x["candidate_sha256"]]
                best = max(ranked, key=lambda x:(x["development"]["passed"], -x["round"])) if ranked else None
                items[name][agent] = {
                    "rounds": attempts, "selected_round": best["round"] if best else None,
                    "selected_sha256": best["candidate_sha256"] if best else None,
                    "selected_development_passes": best["development"]["passed"] if best else 0,
                }
        journal_tip = journal.export()["tip"]
    finally:
        journal.close()
    config = {
        "schema": SCHEMA, "backend": "local_ollama",
        "model_requested": client.route, "aider_version": "0.86.2",
        "rounds_per_agent": ROUNDS, "judge_has_author_credentials": False,
        "public_manifest": {k: manifest()[k] for k in ("case_ids", "case_public_sha256", "oracle_sha256")},
        "journal_tip": journal_tip, "cases": items,
        "no_model_weights_changed": True,
        "development_sandbox": "isolated_offline_docker",
    }
    write_json(root / "manifest.json", config)
    return config


def judge(root, *, grader=test_source):
    root = Path(root)
    doc = json.loads((root / "manifest.json").read_text())
    m = manifest()
    if doc["schema"] != SCHEMA or doc["public_manifest"] != {
        k: m[k] for k in ("case_ids", "case_public_sha256", "oracle_sha256")
    } or set(doc["cases"]) != set(CASES):
        raise ValueError("case suite or public digest mismatch")
    journal = Journal(root / "bean-journal.sqlite")
    try:
        if journal.export()["tip"] != doc["journal_tip"]:
            raise ValueError("BEAN persistent learning receipt mismatch")
        events = journal.events()
        if len(events) != ROUNDS * len(CASES):
            raise ValueError("BEAN feedback journal is incomplete")
    finally:
        journal.close()
    scores = {}
    comparable = True
    for name, spec in CASES.items():
        initial = grader(spec["source"], spec["test"])
        if initial["status"] == "passed" or initial["total_tests"] < 5:
            raise ValueError("original task must fail hidden tests")
        scores[name] = {}
        for agent in AGENTS:
            row = doc["cases"][name][agent]
            if len(row["rounds"]) != ROUNDS:
                raise ValueError("missing agent iterations")
            for i, attempt in enumerate(row["rounds"], 1):
                if attempt["round"] != i or attempt["source_sha256"] != sha(spec["source"]):
                    raise ValueError("invalid round evidence")
                if attempt["model_requested"] != doc["model_requested"]:
                    comparable = False
                path = root / "candidates" / name / agent / ("round" + str(i) + ".py")
                if attempt["candidate_sha256"]:
                    if not path.is_file() or sha(path.read_bytes()) != attempt["candidate_sha256"]:
                        raise ValueError("candidate was modified since author receipt")
                elif path.exists():
                    raise ValueError("unattested generated code")
            n = row["selected_round"]
            if n is None:
                comparable = False
                scores[name][agent] = {"passed_tests": 0, "total_tests": initial["total_tests"],
                                       "status": "no_candidate"}
            else:
                selected = row["rounds"][n - 1]
                if selected["candidate_sha256"] != row["selected_sha256"] or (
                        row["selected_development_passes"] != selected["development"]["passed"]):
                    raise ValueError("selected source evidence mismatch")
                scores[name][agent] = grader(
                    (root / "candidates" / name / agent / ("round"+str(n)+".py")).read_text(),
                    spec["test"])
            if any(x["status"] == "tool_or_transport_failure" for x in row["rounds"]):
                comparable = False
    combined = {}
    for agent in AGENTS:
        combined[agent] = {
            "holdout_passed": sum(scores[k][agent]["passed_tests"] for k in CASES),
            "holdout_total": sum(scores[k][agent]["total_tests"] for k in CASES),
            "tasks_passed": sum(scores[k][agent]["status"] == "passed" for k in CASES),
            "model_route": doc["model_requested"],
        }
    b, a = combined["bean"], combined["aider"]
    bscore = (b["tasks_passed"], b["holdout_passed"])
    ascore = (a["tasks_passed"], a["holdout_passed"])
    label = ("INCONCLUSIVE" if not comparable else
             "BEAN_WIN" if bscore > ascore else
             "AIDER_WIN" if ascore > bscore else "TIE")
    result = {"schema": SCHEMA, "classification": label,
              "scores": combined, "cases": scores,
              "same_requested_model": True,
              "comparable": comparable,
              "rounds_per_agent": ROUNDS,
              "limits": [
                  "Only two synthetic coding tasks; no universal superiority",
                  "Aider may make more than one model request per edit round",
                  "BEAN uses development-score feedback and an external Ollama model",
                  "Public challenge fixtures could exist in model training data",
                  "No model weights were trained",
              ]}
    result["evidence_sha256"] = sha(json.dumps(result, sort_keys=True))
    write_json(root / "verdict.json", result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=("author", "judge"))
    parser.add_argument("--out", type=Path, default=Path("_lab024_arena"))
    parser.add_argument("--model", default=os.environ.get("BEAN_OLLAMA_MODEL",
                                                         "qwen2.5-coder:1.5b"))
    args = parser.parse_args()
    if args.stage == "author":
        result = author(args.out, client=Ollama(model=args.model))
        print(json.dumps({"stage": "author",
                          "model_requested": result["model_requested"],
                          "cases": {k: {a: v["selected_development_passes"]
                                        for a, v in agents.items()}
                                    for k, agents in result["cases"].items()}}, indent=2))
    else:
        result = judge(args.out)
        print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
