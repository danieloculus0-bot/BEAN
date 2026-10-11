"""Independent no-secret evaluator for BEAN's self-written author repair."""
from __future__ import annotations

import argparse
import ast
import difflib
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

from bean.evaluation.autonomous_selfrepair import (
    SOURCE_COMMIT, TARGET, FREE_ROUTE, current_commit, sha, json_file
)

ORACLE = Path("bean/tests/test_autonomous_selfrepair_oracle.py")


def run_suite(root, *args):
    env = dict(os.environ)
    for name in ("OPENROUTER_API_KEY", "GITHUB_TOKEN", "GH_TOKEN", "BEAN_MODELS_TOKEN"):
        env.pop(name, None)
    env["PYTHONPATH"] = str(root.resolve())
    return subprocess.run(
        [sys.executable, "-m", "pytest", *args, "-q", "--tb=short"],
        cwd=root, env=env, capture_output=True, text=True, timeout=220
    )


def validate(*, root, challenge, candidate_file, receipt_file, validated):
    report = {"schema": "bean.autonomous.self-repair.verdict.v1",
              "result": "not_tested", "source_commit": SOURCE_COMMIT,
              "verifier_secrets": "none"}
    original = None
    created_oracle = False
    try:
        if current_commit(root) != SOURCE_COMMIT:
            raise ValueError("source checkout did not match pinned baseline")
        candidate = json.loads(candidate_file.read_text(encoding="utf-8"))
        required = {
            "schema", "source_commit", "target", "original_sha256",
            "replacement_sha256", "diff_lines", "provider_route",
            "model_served", "base_failed_run", "replacement",
        }
        if set(candidate) != required or candidate["schema"] != "bean.autonomous.self-repair.candidate.v1":
            raise ValueError("candidate receipt does not match exact accepted contract")
        if candidate["source_commit"] != SOURCE_COMMIT or candidate["target"] != TARGET.as_posix():
            raise ValueError("source commit or write path differs")
        if candidate["provider_route"] != FREE_ROUTE:
            raise ValueError("not the required no-cost model route")
        source_path = root / TARGET
        if source_path.is_symlink():
            raise ValueError("source path unexpectedly symlinked")
        original = source_path.read_text(encoding="utf-8")
        if candidate["original_sha256"] != sha(original):
            raise ValueError("candidate was not authored against immutable source")
        replacement = candidate["replacement"]
        if not isinstance(replacement, str) or not replacement.strip():
            raise ValueError("candidate source empty")
        ast.parse(replacement, str(TARGET))
        if replacement == original or candidate["replacement_sha256"] != sha(replacement):
            raise ValueError("candidate unchanged or digest mismatched")
        changed = sum(x.startswith(("+ ", "- ")) for x in
                      difflib.ndiff(original.splitlines(), replacement.splitlines()))
        if not 1 <= changed <= 100 or candidate["diff_lines"] != changed:
            raise ValueError("candidate outside measured edit budget")
        if len(replacement.encode("utf-8")) > 50000:
            raise ValueError("candidate file too large")
        src_oracle = challenge / ORACLE
        local_oracle = root / ORACLE
        if src_oracle.is_symlink() or local_oracle.exists():
            raise ValueError("sealed oracle missing or already exists")
        shutil.copyfile(src_oracle, local_oracle)
        created_oracle = True
        baseline = run_suite(root, ORACLE.as_posix())
        report["baseline_red"] = (
            baseline.returncode != 0
            and "test_failed_model_reply_causes_substantively_different_retry_strategy"
                in (baseline.stderr + baseline.stdout)
            and "FAILED" in (baseline.stderr + baseline.stdout)
        )
        report["baseline_excerpt"] = (baseline.stdout + baseline.stderr)[-1400:]
        if not report["baseline_red"]:
            raise ValueError("independent original source did not reproduce failing acceptance")
        source_path.write_text(replacement, encoding="utf-8")
        tests = run_suite(root, "bean/tests")
        report["all_tests_pass"] = tests.returncode == 0
        report["test_excerpt"] = (tests.stdout + tests.stderr)[-1700:]
        if tests.returncode:
            raise RuntimeError("model's self-fix fails held-out or full Core tests")
        output = validated / TARGET
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(replacement, encoding="utf-8")
        report.update(result="candidate_verified_one_platform",
                      accepted_sha256=sha(replacement),
                      changed_lines=changed)
        return 0
    except Exception as exc:
        report.update(result="candidate_rejected", reason=type(exc).__name__ + ": " + str(exc)[:150])
        return 1
    finally:
        if original is not None:
            (root / TARGET).write_text(original, encoding="utf-8")
        if created_oracle:
            (root / ORACLE).unlink(missing_ok=True)
        json_file(receipt_file, report)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", type=Path, default=Path("_core"))
    ap.add_argument("--challenge", type=Path, default=Path("."))
    ap.add_argument("--candidate", type=Path, default=Path("_selfrepair/candidate.json"))
    ap.add_argument("--receipt", type=Path, default=Path("_verified/verdict.json"))
    ap.add_argument("--validated", type=Path, default=Path("_verified/validated"))
    args = ap.parse_args()
    status = validate(root=args.root, challenge=args.challenge,
                      candidate_file=args.candidate, receipt_file=args.receipt,
                      validated=args.validated)
    print(args.receipt.read_text(encoding="utf-8"))
    return status


if __name__ == "__main__":
    raise SystemExit(main())
