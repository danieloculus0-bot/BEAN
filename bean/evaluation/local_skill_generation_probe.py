"""Actual local-model code-generation probe, with independently checked held-out cases.

This is an inference probe, NOT a retained skill or proof of learning.
The generated source is never imported into this process.
"""
from __future__ import annotations

import ast
import hashlib
import json
import os
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
    outcome = {"schema": "bean.local_skill_probe.v1",
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
                outcome["failure_type"] = (
                    None if proc.returncode == 0 else "heldout_assertion_or_runtime")
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
    if not result.get("heldout_passed", False):
        sys.exit(1)
