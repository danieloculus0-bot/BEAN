"""BEAN Lab020: repeated live-free LLM proposals against actual Core source.

An independent evaluator (separate credential-free job) owns all tests.
The model reads the current production source, a task description, and only
bounded numerical feedback from earlier tests.  No test source is in prompt.
This is iterative *inference*, not proof of model weight updates or intelligence.
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
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROUTE = "openrouter/free"
TASK = ("Fix BEAN Core's actual ImprovementOpportunity identity collision bug. "
        "rank_improvements must reject duplicates even when identifiers differ "
        "only in surrounding whitespace or Unicode case-folding (for example "
        "'Patch-A' versus ' patch-a ', and 'Straße' versus 'STRASSE'). "
        "Keep original identifier text in valid returned RankedOpportunity "
        "objects, preserve score calculation, validation, ranking, APIs and "
        "all existing legitimate behavior. Return the complete Python module.")
TARGET = "bean/optimization/selection.py"
SCHEMA = "bean.llm-growth.lab020.v1"
HERE = Path(__file__).resolve().parent


def packed(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def digest(data):
    return hashlib.sha256(data).hexdigest()


def normalise(source):
    if not isinstance(source, str) or not source.strip():
        raise ValueError("model returned no text")
    source = source.strip()
    fence = chr(96) * 3
    if fence in source:
        parts = source.split(fence, 2)
        if len(parts) < 3:
            raise ValueError("unclosed code block")
        source = parts[1].strip()
        if source.lower().startswith("python\n"):
            source = source.split("\n", 1)[1].strip()
    if len(source) > 30000:
        raise ValueError("model source too long")
    tree = ast.parse(source)
    if not any(isinstance(n, ast.FunctionDef) and n.name == "rank_improvements"
               for n in tree.body):
        raise ValueError("rank_improvements definition missing")
    return source + "\n"


def checked_history(path):
    if not path:
        return {"schema": SCHEMA, "entries": [], "tip": "GENESIS"}
    record = json.loads(Path(path).read_text(encoding="utf-8"))
    if set(record) != {"schema", "entries", "tip"} or record["schema"] != SCHEMA:
        raise ValueError("historical schema mismatch")
    previous = "GENESIS"
    if not isinstance(record["entries"], list) or len(record["entries"]) > 3:
        raise ValueError("unexpected history length")
    for e in record["entries"]:
        if not isinstance(e, dict) or set(e) != {
            "iteration", "candidate_sha", "outcome", "passed", "total",
            "previous", "entry_sha", "source_sha", "test_sha",
        }:
            raise ValueError("history entry incomplete")
        unsigned = {k: v for k, v in e.items() if k != "entry_sha"}
        if e["previous"] != previous or digest(packed(unsigned)) != e["entry_sha"]:
            raise ValueError("history integrity mismatch")
        previous = e["entry_sha"]
    if record["tip"] != previous:
        raise ValueError("history tip mismatch")
    return record


def request_model(key, source, history, iteration, *, request_fn=urlopen):
    summaries = [{"iteration": x["iteration"], "outcome": x["outcome"],
                  "passed": x["passed"], "total": x["total"],
                  "candidate_sha": x["candidate_sha"]} for x in history["entries"]]
    prompt = (TASK + "\n\nIteration " + str(iteration) +
              ". Previous independent-test scores (no test code): " +
              json.dumps(summaries, sort_keys=True) +
              "\n\nCurrent unchanged original BEAN module:\n" + source)
    body = {"model": ROUTE,
            "messages": [{"role": "system",
                          "content": "You are BEAN's software developer. Return only a complete Python source file. Do not claim tests have passed; an independent evaluator will decide."},
                         {"role": "user", "content": prompt}],
            "temperature": .45, "max_tokens": 3000, "stream": False}
    request = Request(
        "https://openrouter.ai/api/v1/chat/completions",
        data=packed(body), method="POST",
        headers={"Authorization": "Bearer " + key, "Content-Type": "application/json",
                 "X-Title": "BEAN Iterative Free Code Research"},
    )
    with request_fn(request, timeout=100) as r:
        result = json.loads(r.read(600000).decode("utf-8"))
    choice = (result.get("choices") or [{}])[0]
    answer = (choice.get("message") or {}).get("content")
    meta = {"model_served": str(result.get("model", "unknown"))[:140],
            "finish_reason": str(choice.get("finish_reason", "unknown"))[:40],
            "response_chars": len(answer) if isinstance(answer, str) else 0}
    return normalise(answer), meta


def generate(*, source_path, prior_history, iteration, out, key=None, request_fn=urlopen):
    if iteration not in (0, 1, 2):
        raise ValueError("maximum of three free-model requests")
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    source_bytes = Path(source_path).read_bytes()
    source = source_bytes.decode("utf-8")
    history = checked_history(prior_history)
    if len(history["entries"]) != iteration:
        raise ValueError("history round mismatch")
    receipt = {"schema": SCHEMA, "round": iteration, "requested": ROUTE,
               "source_sha": digest(source_bytes), "history_tip": history["tip"],
               "status": "unavailable", "requested_count": 0,
               "candidate_sha": None, "model_served": None}
    provided = key if key is not None else os.environ.get("OPENROUTER_API_KEY")
    if not provided:
        receipt["reason"] = "GitHub secret absent"
    else:
        receipt["requested_count"] = 1
        try:
            candidate, meta = request_model(provided, source, history, iteration,
                                            request_fn=request_fn)
            data = candidate.encode("utf-8")
            (out / "proposal.py").write_bytes(data)
            receipt.update({"status": "generated", "candidate_sha": digest(data),
                            **meta})
        except HTTPError as exc:
            receipt["reason"] = "OpenRouter HTTP " + str(exc.code)
        except (URLError, OSError, TimeoutError) as exc:
            receipt["reason"] = "connection " + type(exc).__name__
        except (ValueError, TypeError, KeyError, SyntaxError, IndexError) as exc:
            receipt["status"] = "invalid_model_output"
            receipt["reason"] = type(exc).__name__
    (out / "receipt.json").write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return receipt


def score_candidate(source, *, test_source, timeout=18):
    """Independent subprocess: no model key, no arbitrary repo permissions."""
    with tempfile.TemporaryDirectory(prefix="bean-lab020-") as tmp:
        root = Path(tmp)
        module = root / TARGET
        module.parent.mkdir(parents=True)
        module.write_bytes(source.encode("utf-8"))
        (root / "bean" / "__init__.py").write_text("")
        (root / "bean" / "optimization" / "__init__.py").write_text("")
        tests = root / "tests"
        tests.mkdir()
        shutil.copyfile(test_source, tests / "test_identity_contract.py")
        env = {"PYTHONPATH": str(root), "PYTHONDONTWRITEBYTECODE": "1",
               "PYTHONIOENCODING": "utf-8", "PATH": os.getenv("PATH", "")}
        if os.name == "nt":
            env["SYSTEMROOT"] = os.environ.get("SYSTEMROOT", "")
        try:
            p = subprocess.run([sys.executable, "-m", "unittest", "discover",
                                "-s", "tests", "-v"], cwd=root, env=env,
                               timeout=timeout, capture_output=True, text=True)
            output = (p.stdout + "\n" + p.stderr)
            count = re.search(r"Ran (\d+) tests?", output)
            failures = re.search(r"FAILED \(([^)]*)\)", output)
            return {"passed": p.returncode == 0 and count is not None,
                    "passed_tests": int(count.group(1)) - len(re.findall(
                        r"^test_.*\s+\.\.\.\s+(?:FAIL|ERROR)", output, re.M)),
                    "total": int(count.group(1)) if count else 0,
                    "exit": p.returncode,
                    "failure_kinds": str(failures.group(1))[:90] if failures else None}
        except subprocess.TimeoutExpired:
            return {"passed": False, "passed_tests": 0, "total": 0,
                    "exit": 124, "failure_kinds": "timeout"}


def validate(*, source_path, test_source, proposal_dir, prior_history, iteration, out):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    source_bytes = Path(source_path).read_bytes()
    source = source_bytes.decode("utf-8")
    history = checked_history(prior_history)
    if len(history["entries"]) != iteration:
        raise ValueError("history round mismatch")
    test_sha = digest(Path(test_source).read_bytes())
    src_sha = digest(source_bytes)
    baseline = score_candidate(source, test_source=test_source)
    receipt = json.loads((Path(proposal_dir) / "receipt.json").read_text())
    if receipt["source_sha"] != src_sha or receipt["history_tip"] != history["tip"]:
        raise ValueError("generator source/history does not match evaluator")
    candidate_sha = receipt["candidate_sha"]
    scored = {"passed": False, "passed_tests": 0, "total": baseline["total"],
              "failure_kinds": "missing proposal"}
    if receipt["status"] == "generated":
        file = Path(proposal_dir) / "proposal.py"
        source_bytes = file.read_bytes()
        if digest(source_bytes) != candidate_sha:
            raise ValueError("proposal fingerprint mismatch")
        scored = score_candidate(source_bytes.decode("utf-8"), test_source=test_source)
    outcome = ("validated" if scored["passed"] and baseline["total"] >= 7
               and not baseline["passed"] else "rejected")
    entry = {"iteration": iteration, "candidate_sha": candidate_sha,
             "outcome": outcome, "passed": scored["passed_tests"],
             "total": scored["total"], "previous": history["tip"],
             "source_sha": src_sha, "test_sha": test_sha}
    entry["entry_sha"] = digest(packed(entry))
    next_history = {"schema": SCHEMA, "entries": history["entries"] + [entry],
                    "tip": entry["entry_sha"]}
    (out / "history.json").write_text(
        json.dumps(next_history, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    feedback = {"schema": SCHEMA, "round": iteration,
                "model": receipt.get("model_served"),
                "status": receipt["status"], "candidate_sha": candidate_sha,
                "baseline": baseline, "test": scored, "outcome": outcome,
                "history_tip": next_history["tip"], "test_sha": test_sha}
    (out / "feedback.json").write_text(
        json.dumps(feedback, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return feedback


def ast_baseline(*, source_path, test_source, out, max_attempts=25):
    from bean.optimization.autodev import ASTBruteForce
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    source = Path(source_path).read_text(encoding="utf-8")
    baseline = score_candidate(source, test_source=test_source)
    writer = ASTBruteForce(source)
    results = []
    for i, candidate in enumerate(writer.variants[:max_attempts]):
        score = score_candidate(candidate, test_source=test_source)
        results.append({"iteration": i, "sha": digest(candidate.encode("utf-8")),
                        "passed": score["passed"], "score": score["passed_tests"],
                        "total": score["total"]})
        if score["passed"]:
            break
    report = {"schema": SCHEMA, "generator": "ASTBruteForce",
              "baseline": baseline, "attempts": len(results),
              "source_candidate_count": len(writer.variants),
              "success": bool(results and results[-1]["passed"]), "results": results}
    (out / "ast-report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return report


def main():
    parser = argparse.ArgumentParser()
    subs = parser.add_subparsers(dest="action", required=True)
    g = subs.add_parser("generate")
    v = subs.add_parser("validate")
    a = subs.add_parser("ast")
    for p in (g, v, a):
        p.add_argument("--source", type=Path, default=Path(TARGET))
        p.add_argument("--out", type=Path, required=True)
    for p in (g, v):
        p.add_argument("--round", type=int, required=True)
        p.add_argument("--history", type=Path, default=None)
    for p in (v, a):
        p.add_argument("--tests", type=Path, default=HERE / "test_selection_identity.py")
    v.add_argument("--proposal", type=Path, required=True)
    a.add_argument("--attempts", type=int, default=25)
    args = parser.parse_args()
    if args.action == "generate":
        report = generate(source_path=args.source, prior_history=args.history,
                          iteration=args.round, out=args.out)
    elif args.action == "validate":
        report = validate(source_path=args.source, test_source=args.tests,
                          proposal_dir=args.proposal, prior_history=args.history,
                          iteration=args.round, out=args.out)
        if "GITHUB_OUTPUT" in os.environ:
            with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as f:
                f.write("accepted=" + ("true" if report["outcome"] == "validated" else "false") + "\n")
                f.write("more=" + ("true" if args.round < 2 and report["status"] in ("generated", "invalid_model_output") else "false") + "\n")
    else:
        report = ast_baseline(source_path=args.source, test_source=args.tests,
                              out=args.out, max_attempts=args.attempts)
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
