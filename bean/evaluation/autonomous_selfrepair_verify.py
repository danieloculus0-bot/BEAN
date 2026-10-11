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

ORACLE = Path("experiments/autonomous_selfrepair/test_selfrepair_holdout.py")
LOCAL_ORACLE = Path("bean/tests/test_autonomous_selfrepair_oracle.py")


def run_suite(root, *args):
    env = dict(os.environ)
    for name in ("OPENROUTER_API_KEY", "GITHUB_TOKEN", "GH_TOKEN", "BEAN_MODELS_TOKEN"):
        env.pop(name, None)
    env["PYTHONPATH"] = str(root.resolve())
    return subprocess.run(
        [sys.executable, "-m", "pytest", *args, "-q", "--tb=short"],
        cwd=root, env=env, capture_output=True, text=True, timeout=220
    )


def safe_transport_unchanged(original, replacement):
    """Reject changes to provider routing, credentials or executable imports."""
    old_tree, new_tree = ast.parse(original), ast.parse(replacement)
    def exported(tree):
        return [(getattr(node, "name", "anonymous_" + str(i)), node)
                for i, node in enumerate(tree.body)]
    old_exports, new_exports = exported(old_tree), exported(new_tree)
    if [name for name, _ in old_exports] != [name for name, _ in new_exports]:
        raise ValueError("source changed module structure")
    functions = []
    for (name, old_node), (_, new_node) in zip(old_exports, new_exports):
        if name == "call_model" and isinstance(old_node, ast.FunctionDef) and isinstance(new_node, ast.FunctionDef):
            functions.append((old_node, new_node))
        elif ast.dump(old_node, include_attributes=False) != ast.dump(new_node, include_attributes=False):
            raise ValueError("source changed imports, globals or unrelated code")
    if len(functions) != 1:
        raise ValueError("targeted model-author function missing")
    old_function, new_function = functions[0]
    if ast.dump(old_function.args, include_attributes=False) != ast.dump(new_function.args, include_attributes=False):
        raise ValueError("model-author public signature changed")
    # The model can change how it composes the prompt. The HTTP payload,
    # endpoint, authorization header, provider response parser and result
    # handling remain immutable, even when source tests pass.
    def frozen_tail(function):
        for i, statement in enumerate(function.body):
            if isinstance(statement, ast.Assign) and any(
                    isinstance(target, ast.Name) and target.id == "data"
                    for target in statement.targets):
                return ast.dump(ast.Module(body=function.body[i:], type_ignores=[]),
                                include_attributes=False)
        raise ValueError("model HTTP request pipeline missing")
    if frozen_tail(old_function) != frozen_tail(new_function):
        raise ValueError("provider transport or authentication modified")
    for node in ast.walk(new_function):
        if isinstance(node, (ast.Import, ast.ImportFrom, ast.Global, ast.Nonlocal)):
            raise ValueError("new executable import or global scope forbidden")
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in (
                "exec", "eval", "compile", "open", "__import__"):
            raise ValueError("dynamic execution or file access forbidden")
    return True


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
        if candidate["provider_route"] not in (FREE_ROUTE, "ollama_local"):
            raise ValueError("unrecognized model provider")
        if candidate["provider_route"] == "ollama_local" and not candidate["model_served"].startswith("qwen2.5-coder:"):
            raise ValueError("unrecognized local neural model")
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
        safe_transport_unchanged(original, replacement)
        src_oracle = challenge / ORACLE
        local_oracle = root / LOCAL_ORACLE
        if src_oracle.is_symlink() or local_oracle.exists():
            raise ValueError("sealed oracle missing or already exists")
        shutil.copyfile(src_oracle, local_oracle)
        created_oracle = True
        baseline = run_suite(root, LOCAL_ORACLE.as_posix())
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
            (root / LOCAL_ORACLE).unlink(missing_ok=True)
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
