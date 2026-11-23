"""Run an explicitly selected evaluation subprocess and retain observed evidence.

This is an execution adapter, not an independent judge of semantic correctness.
A zero exit code means the supplied evaluator passed, not that learning occurred.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
import subprocess
import time

from bean.optimization.reuse_outcome_ledger import append_reuse_outcome


def evaluate_and_record(database, *, skill, source_file, tests_file, argv,
                        experiment_id, condition, model_id, seed,
                        timeout_seconds=30, cwd=None):
    """Execute an evaluator once, then persist its result, including failures.

    The timeout is an enforced upper bound, not measured model-token usage.
    The caller supplies the evaluator and is responsible for holdout isolation.
    No shell expansion, implicit provider call or model invocation is performed.
    """
    if not isinstance(argv, (list, tuple)) or not argv or any(
        not isinstance(arg, str) or not arg for arg in argv
    ):
        raise ValueError("argv must be a nonempty list of nonempty strings")
    if isinstance(timeout_seconds, bool) or not isinstance(timeout_seconds, (int, float)) or not 0 < timeout_seconds <= 3600:
        raise ValueError("timeout_seconds must be in (0, 3600]")
    if type(seed) is not int or seed < 0:
        raise ValueError("seed must be a nonnegative integer")
    source = Path(source_file).read_bytes()
    tests = Path(tests_file).read_bytes()
    source_sha = hashlib.sha256(source).hexdigest()
    tests_sha = hashlib.sha256(tests).hexdigest()
    start = time.monotonic_ns()
    timed_out = False
    try:
        completed = subprocess.run(
            list(argv), cwd=cwd, capture_output=True, timeout=timeout_seconds,
            check=False,
        )
        returncode = completed.returncode
        stdout, stderr = completed.stdout, completed.stderr
    except subprocess.TimeoutExpired as exc:
        timed_out = True
        returncode = None
        stdout = exc.stdout or b""
        stderr = exc.stderr or b""
    except OSError as exc:
        # A missing evaluator executable is a failed attempt, not lost evidence.
        returncode = None
        stdout = b""
        stderr = str(exc).encode("utf-8", errors="replace")
    elapsed_ms = (time.monotonic_ns() - start) // 1_000_000
    passed = not timed_out and returncode == 0
    receipt = append_reuse_outcome(
        database, skill=skill, source_sha256=source_sha,
        tests_sha256=tests_sha, passed=passed, novel_test_set=True,
        provider_invoked=False, experiment_id=experiment_id,
        condition=condition, model_id=model_id,
        evaluation_budget=int(timeout_seconds * 1000), seed=seed,
    )
    return {
        "passed": passed, "timed_out": timed_out, "returncode": returncode,
        "elapsed_ms": elapsed_ms, "timeout_budget_ms": int(timeout_seconds * 1000),
        "source_sha256": source_sha, "tests_sha256": tests_sha,
        "stdout_sha256": hashlib.sha256(stdout).hexdigest(),
        "stderr_sha256": hashlib.sha256(stderr).hexdigest(),
        "receipt": receipt, "provider_invoked": False,
        "semantic_correctness_verified": False,
    }
