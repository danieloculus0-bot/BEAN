"""BEAN Lab019: self-authored code changes, independent tests, persistent history.

The writer generates real Python sources (AST search, Ollama, or OpenRouter),
tries them in disposable copies of a test project, and records every result.
Generated Python is EXECUTED by tests. This is NOT an operating-system sandbox.
Only run model-generated trials on credential-free disposable CI/VM machines.
Production main is never written.
"""
from __future__ import annotations

import argparse
import ast
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import urllib.request

SCHEMA = "bean.autodev.lab019.v1"
TARGET = re.compile(r"^bean/(?:[a-zA-Z0-9_]+/)*[a-zA-Z0-9_]+\.py$")


def canonical(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def digest(data):
    return hashlib.sha256(data).hexdigest()


def source_digest(text):
    return digest(text.encode("utf-8"))


def test_digest(folder):
    files = []
    for p in sorted(folder.rglob("*.py")):
        if p.is_symlink():
            raise ValueError("symlinked tests forbidden")
        files.append([str(p.relative_to(folder)), digest(p.read_bytes())])
    if not files:
        raise ValueError("no independent evaluator tests")
    return digest(canonical(files))


class Journal:
    """Persistent, append-only SQLite SHA256-chain; one writer per journal."""

    def __init__(self, path):
        p = Path(path)
        if p.is_symlink():
            raise ValueError("journal symlink rejected")
        p.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(str(p))
        self.db.row_factory = sqlite3.Row
        self.db.execute("""CREATE TABLE IF NOT EXISTS attempts (
            id INTEGER PRIMARY KEY AUTOINCREMENT, objective TEXT NOT NULL,
            iteration INTEGER NOT NULL, previous_digest TEXT NOT NULL,
            payload TEXT NOT NULL, entry_digest TEXT NOT NULL,
            UNIQUE(objective, iteration))""")
        self.db.commit()
        self.verify()

    def verify(self):
        prior = "GENESIS"
        for row in self.db.execute("SELECT * FROM attempts ORDER BY id"):
            payload = json.loads(row["payload"])
            expected = digest(canonical({"previous": prior, "payload": payload}))
            if expected != row["entry_digest"] or prior != row["previous_digest"]:
                raise ValueError("altered or discontinuous BEAN learning history")
            if payload["objective"] != row["objective"] or payload["iteration"] != row["iteration"]:
                raise ValueError("history metadata was changed")
            prior = expected

    def events(self, objective=None):
        if objective is None:
            rows = self.db.execute("SELECT payload FROM attempts ORDER BY id")
        else:
            rows = self.db.execute("SELECT payload FROM attempts WHERE objective=? ORDER BY iteration",
                                   (objective,))
        return [json.loads(row["payload"]) for row in rows]

    def append(self, event):
        self.verify()
        row = self.db.execute("SELECT entry_digest FROM attempts ORDER BY id DESC LIMIT 1").fetchone()
        previous = row["entry_digest"] if row else "GENESIS"
        entry_hash = digest(canonical({"previous": previous, "payload": event}))
        with self.db:
            self.db.execute("INSERT INTO attempts(objective,iteration,previous_digest,payload,entry_digest)"
                            " VALUES (?,?,?,?,?)", (event["objective"], event["iteration"],
                            previous, canonical(event).decode(), entry_hash))
        return entry_hash

    def export(self):
        self.verify()
        last = self.db.execute("SELECT entry_digest FROM attempts ORDER BY id DESC LIMIT 1").fetchone()
        rows = self.events()
        return {"schema": SCHEMA, "attempts": len(rows), "events": rows,
                "tip": last["entry_digest"] if last else "GENESIS"}

    def close(self):
        self.db.close()


class ASTBruteForce:
    """Finite baseline that actually generates source code, not a hardcoded fix."""

    def __init__(self, original):
        self.variants = []
        integers = [n for n in ast.walk(ast.parse(original))
                    if isinstance(n, ast.Constant) and type(n.value) is int]
        for index, integer in enumerate(integers):
            for value in (integer.value-2, integer.value-1, integer.value+1,
                          integer.value+2, 0, 1, 100):
                if value == integer.value:
                    continue
                tree = ast.parse(original)
                cells = [n for n in ast.walk(tree)
                         if isinstance(n, ast.Constant) and type(n.value) is int]
                cells[index].value = value
                candidate = ast.unparse(ast.fix_missing_locations(tree)) + "\n"
                if candidate not in self.variants and candidate != original:
                    self.variants.append(candidate)

    def propose(self, task, original, history, iteration):
        if iteration >= len(self.variants):
            raise StopIteration("candidate space exhausted")
        return self.variants[iteration]


class ModelWriter:
    """Actual provider-backed complete-source writer; not invoked in fixture CI."""

    def __init__(self, provider, model, *, url=None):
        if provider not in ("ollama", "openrouter"):
            raise ValueError("unknown provider")
        if not re.fullmatch(r"[A-Za-z0-9._:/-]{1,100}", model):
            raise ValueError("invalid model")
        self.provider, self.model = provider, model
        self.url = url or ("http://127.0.0.1:11434/api/generate" if provider == "ollama"
                           else "https://openrouter.ai/api/v1/chat/completions")

    def propose(self, task, original, history, iteration):
        failed = [{"iteration": h["iteration"], "result": h["outcome"],
                   "failure": h.get("failure", "")[:300]}
                  for h in history[-10:]]
        prompt = ("You are BEAN's software author. Return a COMPLETE replacement PYTHON MODULE, "
                  "source only. No test generation or shell commands. Preserve unrelated API "
                  "behavior. A separate evaluator has tests you cannot see. "
                  "Learn from earlier failures and try distinct corrections.\nTask: " + task
                  + "\nRound: " + str(iteration) + "\nHistory: " + json.dumps(failed)
                  + "\nOriginal code:\n" + original)
        if self.provider == "ollama":
            body = {"model": self.model, "prompt": prompt, "stream": False,
                    "options": {"temperature": 0.6, "num_predict": 4096}}
            headers = {"Content-Type": "application/json"}
        else:
            key = os.environ.get("OPENROUTER_API_KEY")
            if not key:
                raise RuntimeError("OPENROUTER_API_KEY not configured")
            body = {"model": self.model, "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.6}
            headers = {"Content-Type": "application/json", "Authorization": "Bearer " + key}
        req = urllib.request.Request(self.url, data=canonical(body),
                                     headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=90) as response:
            reply = json.loads(response.read(600000).decode("utf-8"))
        result = reply["response"] if self.provider == "ollama" else reply["choices"][0]["message"]["content"]
        if not isinstance(result, str) or not result.strip():
            raise ValueError("model returned no replacement code")
        result = result.strip()
        fence = chr(96) * 3
        if result.startswith(fence):
            lines = result.splitlines()
            result = "\n".join(lines[1:-1]).strip()
        if not result or len(result) > 50000:
            raise ValueError("invalid model output")
        return result + "\n"


def target_file(project, relative):
    if not isinstance(relative, str) or not TARGET.fullmatch(relative):
        raise ValueError("target must be a relative Python module under bean")
    if any(x.startswith("__") for x in Path(relative).parts):
        raise ValueError("special Python files excluded")
    root = Path(project)
    if root.is_symlink() or not (root / "tests").is_dir():
        raise ValueError("trusted project requires independent tests")
    target = root.resolve(strict=True) / relative
    if not target.is_file() or target.is_symlink() or not target.resolve().is_relative_to(root.resolve()):
        raise ValueError("target is absent, outside project or symlinked")
    return target


def evaluate(project, target, source, timeout=15):
    """Write actual rewritten Python in a disposable project; execute tests there."""
    ast.parse(source)
    with tempfile.TemporaryDirectory(prefix="bean-candidate-") as scratch:
        work = Path(scratch) / "project"
        shutil.copytree(project, work,
                        ignore=shutil.ignore_patterns(".git", ".venv", "venv", "__pycache__",
                                                       ".pytest_cache"), symlinks=False)
        updated = work / target
        if not updated.is_file() or updated.is_symlink():
            raise ValueError("target missing in isolated project")
        updated.write_text(source, encoding="utf-8")
        # Do not pass API keys/GitHub tokens to generated code.
        env = {"PATH": os.environ.get("PATH", ""), "PYTHONPATH": str(work),
               "PYTHONDONTWRITEBYTECODE": "1", "PYTHONIOENCODING": "utf-8"}
        if os.name == "nt":
            env["SYSTEMROOT"] = os.environ.get("SYSTEMROOT", "")
            env["TEMP"] = os.environ.get("TEMP", scratch)
        try:
            p = subprocess.run([sys.executable, "-m", "unittest", "discover",
                                "-s", "tests", "-v"], cwd=work, env=env,
                               text=True, capture_output=True, timeout=timeout)
            output = (p.stdout + "\n" + p.stderr)[-4000:]
            match = re.search(r"Ran (\d+) tests?", output)
            return {"passed": p.returncode == 0,
                    "test_count": int(match.group(1)) if match else 0,
                    "exit": p.returncode, "excerpt": output[-900:]}
        except subprocess.TimeoutExpired:
            return {"passed": False, "test_count": 0, "exit": 124, "excerpt": "timeout"}


def run_cycle(*, project, target, task, journal_path, output, provider, attempts=25):
    """Search, write, test, remember, resume. Never modify production source."""
    if not 1 <= attempts <= 100 or not 12 <= len(task) <= 4000:
        raise ValueError("invalid trial budget or objective")
    project = Path(project).resolve(strict=True)
    original = target_file(project, target).read_text(encoding="utf-8")
    original_sha, tests_sha = source_digest(original), test_digest(project / "tests")
    objective = digest(canonical({"target": target, "task": task, "original": original_sha,
                                  "tests": tests_sha}))
    baseline = evaluate(project, target, original)
    journal = Journal(journal_path)
    output = Path(output)
    if output.is_symlink():
        raise ValueError("symlink output forbidden")
    output.mkdir(parents=True, exist_ok=True)
    archive = output / "candidates" / objective
    archive.mkdir(parents=True, exist_ok=True)
    try:
        history = journal.events(objective)
        report = {"schema": SCHEMA, "objective": objective,
                  "target": target, "original_sha256": original_sha,
                  "tests_sha256": tests_sha, "baseline": baseline,
                  "provider": type(provider).__name__, "prior_attempts": len(history),
                  "new_attempts": 0, "status": "unresolved", "accepted_source": None}
        if baseline["passed"]:
            report["status"] = "baseline_passed_no_witnessed_defect"
            return report
        previous = next((row for row in history if row["outcome"] == "validated"), None)
        if previous:
            report.update({"status": "previously_validated_in_memory",
                           "accepted_source": previous["candidate_sha256"]})
            return report
        iteration = len(history)
        for _ in range(attempts):
            try:
                source = provider.propose(task, original, history, iteration)
                if not isinstance(source, str) or not source.strip() or len(source) > 50000:
                    raise ValueError("invalid candidate source")
                if source == original:
                    raise ValueError("unchanged candidate")
                ast.parse(source)
                proposal_sha = source_digest(source)
                if proposal_sha in {row.get("candidate_sha256") for row in history}:
                    raise ValueError("candidate already attempted")
                (archive / (proposal_sha + ".py")).write_text(source, encoding="utf-8")
                test = evaluate(project, target, source)
                accepted = test["passed"] and test["test_count"] >= baseline["test_count"]
                event = {"objective": objective, "iteration": iteration,
                         "source_sha256": original_sha, "tests_sha256": tests_sha,
                         "candidate_sha256": proposal_sha,
                         "outcome": "validated" if accepted else "rejected",
                         "test_count": test["test_count"], "exit": test["exit"],
                         "failure": "" if accepted else test["excerpt"],
                         "timestamp": datetime.now(timezone.utc).isoformat()}
            except StopIteration:
                report["status"] = "candidate_space_exhausted"
                break
            except (ValueError, RuntimeError, SyntaxError, TypeError, KeyError) as exc:
                accepted = False
                event = {"objective": objective, "iteration": iteration,
                         "source_sha256": original_sha, "tests_sha256": tests_sha,
                         "candidate_sha256": None, "outcome": "invalid",
                         "test_count": 0, "exit": 1,
                         "failure": (type(exc).__name__ + ": " + str(exc))[:900],
                         "timestamp": datetime.now(timezone.utc).isoformat()}
            journal.append(event)
            history.append(event)
            iteration += 1
            report["new_attempts"] += 1
            if accepted:
                accepted_file = output / "validated" / target
                accepted_file.parent.mkdir(parents=True, exist_ok=True)
                accepted_file.write_text(source, encoding="utf-8")
                report.update({"status": "validated_patch_written",
                               "accepted_source": proposal_sha,
                               "accepted_iteration": event["iteration"],
                               "validated_path": str(accepted_file),
                               "tests_passed": test["test_count"]})
                break
        return report
    finally:
        (output / "journal-export.json").write_text(
            json.dumps(journal.export(), indent=2, sort_keys=True), encoding="utf-8")
        journal.close()


def main():
    cli = argparse.ArgumentParser(description="BEAN persistent autonomous code experiments")
    cli.add_argument("--project", type=Path, required=True)
    cli.add_argument("--target", required=True)
    cli.add_argument("--task", required=True)
    cli.add_argument("--journal", type=Path, required=True)
    cli.add_argument("--output", type=Path, required=True)
    cli.add_argument("--provider", choices=("ast", "ollama", "openrouter"), default="ast")
    cli.add_argument("--model", default="qwen2.5-coder:7b")
    cli.add_argument("--attempts", type=int, default=25)
    args = cli.parse_args()
    original = target_file(args.project, args.target).read_text(encoding="utf-8")
    writer = ASTBruteForce(original) if args.provider == "ast" else ModelWriter(args.provider, args.model)
    result = run_cycle(project=args.project, target=args.target, task=args.task,
                       journal_path=args.journal, output=args.output,
                       provider=writer, attempts=args.attempts)
    (args.output / "report.json").write_text(json.dumps(result, indent=2, sort_keys=True),
                                              encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    if result["status"] not in {"validated_patch_written", "previously_validated_in_memory",
                                "baseline_passed_no_witnessed_defect"}:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
