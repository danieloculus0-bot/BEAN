"""Actual local-model code-generation probe, with independently checked held-out cases.

This is an inference probe, NOT a retained skill or proof of learning.
The generated source is never imported into this process.
"""
from __future__ import annotations

import ast
import hashlib
import json
import os
import sqlite3
from pathlib import Path
import subprocess
import sys
import tempfile

from bean.optimization.skill_incubator import ModelWriter


def run_probe(receipt: Path) -> dict:
    """Ask the real local model for code, test in a separate bounded process."""
    writer = ModelWriter("llamacpp", "bean-local")
    task = (
        "Write a Python module with exactly one public function "
        "clamp(value, lower, upper) returning the value limited to the "
        "inclusive bounds. Handle integers, including negatives. "
        "Return source code only."
    )
    original = "def clamp(value, lower, upper):\n    raise NotImplementedError\n"
    outcome = {"schema": "bean.local_skill_probe.v2",
               "provider": "llamacpp", "model": "bean-local",
               "real_model_requested": True,
               "retained_learning_proven": False,
               "cross_domain_transfer_proven": False}
    try:
        source = writer.propose(task, original, [], 0)
        outcome["source_sha256"] = hashlib.sha256(source.encode()).hexdigest()
        ast.parse(source)
        # No generated code is executed in the evaluator process.
        # Separate subprocess with bounded time; this is not an OS sandbox.
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "candidate.py").write_text(source)
            tests = (
                "import runpy\n"
                "clamp = runpy.run_path(\'candidate.py\')[\'clamp\']\n"
                "assert clamp(4, 0, 9) == 4\n"
                "assert clamp(-7, -3, 2) == -3\n"
                "assert clamp(99, -4, 6) == 6\n"
                "assert clamp(-2, -2, -2) == -2\n"
            )
            (root / "heldout.py").write_text(tests)
            try:
                proc = subprocess.run(
                    [sys.executable, "-I", "-B", "heldout.py"],
                    cwd=root, capture_output=True, text=True, timeout=8,
                    env={"PATH": os.environ.get("PATH", ""),
                         "PYTHONPATH": "", "PYTHONDONTWRITEBYTECODE": "1"})
                outcome["heldout_stdout_sha256"] = hashlib.sha256(proc.stdout.encode()).hexdigest()
                outcome["heldout_stderr_sha256"] = hashlib.sha256(proc.stderr.encode()).hexdigest()
                outcome["heldout_exit_code"] = proc.returncode
                outcome["heldout_passed"] = proc.returncode == 0
                outcome["heldout_cases"] = 4
                if proc.returncode == 0:
                    db_path = root / "acquired.sqlite3"
                    with sqlite3.connect(db_path) as db:
                        db.execute("CREATE TABLE skills (name TEXT PRIMARY KEY, source TEXT, sha256 TEXT)")
                        db.execute("INSERT INTO skills VALUES (?, ?, ?)",
                                   ("clamp", source, outcome["source_sha256"]))
                    (root / "candidate.py").unlink()
                    recovery = (
                        "import sqlite3, hashlib, pathlib, sys\\n"
                        "with sqlite3.connect(sys.argv[1]) as db:\\n"
                        "    row = db.execute('SELECT source, sha256 FROM skills WHERE name=?', ('clamp',)).fetchone()\\n"
                        "if not row or hashlib.sha256(row[0].encode()).hexdigest() != row[1]:\\n"
                        "    raise SystemExit(3)\\n"
                        "pathlib.Path('candidate.py').write_text(row[0])\\n"
                    )
                    (root / "recover.py").write_text(recovery)
                    restart = subprocess.run(
                        [sys.executable, "-I", "-B", "recover.py", str(db_path)],
                        cwd=root, capture_output=True, text=True, timeout=8)
                    outcome["restart_exit_code"] = restart.returncode
                    outcome["recovered_source_matches"] = (
                        restart.returncode == 0 and
                        (root / "candidate.py").exists() and
                        hashlib.sha256((root / "candidate.py").read_bytes()).hexdigest()
                        == outcome["source_sha256"])
                    if outcome["recovered_source_matches"]:
                        (root / "heldout.py").write_text(
                            "import runpy\\n"
                            "clamp = runpy.run_path('candidate.py')['clamp']\\n"
                            "assert clamp(0, 0, 0) == 0\\n"
                            "assert clamp(-100, -8, -1) == -8\\n"
                            "assert clamp(17, 12, 15) == 15\\n"
                            "assert clamp(13, 12, 15) == 13\\n")
                        reuse = subprocess.run(
                            [sys.executable, "-I", "-B", "heldout.py"],
                            cwd=root, capture_output=True, text=True, timeout=8)
                        outcome["post_restart_exit_code"] = reuse.returncode
                        outcome["post_restart_distinct_passed"] = reuse.returncode == 0
                    else:
                        outcome["post_restart_distinct_passed"] = False
                    if not outcome["post_restart_distinct_passed"]:
                        outcome["failure_type"] = "retained_reuse_failed"
                if proc.returncode != 0:
                    outcome["failure_type"] = "heldout_assertion_or_runtime"
            except subprocess.TimeoutExpired:
                outcome.update(heldout_passed=False, heldout_cases=4,
                               failure_type="execution_timeout")
    except Exception as exc:
        outcome.update(heldout_passed=False, heldout_cases=0,
                       failure_type=type(exc).__name__)
    receipt.parent.mkdir(parents=True, exist_ok=True)
    receipt.write_text(json.dumps(outcome, sort_keys=True, indent=2) + "\n")
    return outcome


if __name__ == "__main__":
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("local-skill-probe.json")
    result = run_probe(target)
    print(json.dumps(result, sort_keys=True))
    if not (result.get("heldout_passed", False) and result.get("post_restart_distinct_passed", False)):
        sys.exit(1)
