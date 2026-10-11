"""Credential-free independent evaluator for BEAN Lab021.

Three domains, fresh holdout seed, and an isolated subprocess for each
untrusted code candidate. The source-authoring model is never shown cases,
oracle implementation, or evaluator tracebacks. The runner is a disposable
CI execution boundary, NOT an OS-grade malware sandbox.
"""
from __future__ import annotations
import argparse
import ast
import copy
import hashlib
import json
import os
from pathlib import Path
import random
import subprocess
import sys
import tempfile

TASK_IDS = ("intervals", "dependencies", "inventory")
SAFE_BUILTINS = {
    "len": len, "range": range, "enumerate": enumerate, "zip": zip,
    "sum": sum, "min": min, "max": max, "abs": abs, "sorted": sorted,
    "set": set, "dict": dict, "list": list, "tuple": tuple, "str": str,
    "int": int, "bool": bool, "any": any, "all": all, "isinstance": isinstance,
    "ValueError": ValueError, "TypeError": TypeError, "KeyError": KeyError,
    "reversed": reversed,
}
BANNED = (
    ast.Import, ast.ImportFrom, ast.ClassDef, ast.AsyncFunctionDef,
    ast.Global, ast.Nonlocal, ast.With, ast.AsyncWith, ast.Await,
    ast.Lambda, ast.Yield, ast.YieldFrom, ast.Try, ast.AsyncFor,
)
# Raise ValueError is allowed by design. The explicit allowed attributes
# exclude introspection, reflection, I/O and subprocess facilities.
METHODS = {
    "get", "items", "keys", "values", "append", "sort", "copy", "setdefault",
    "update", "pop", "add", "remove", "discard", "count", "index",
}


def validate_source(source: str, expected_function: str):
    if len(source) > 12000 or "\0" in source:
        raise ValueError("oversize_or_binary")
    tree = ast.parse(source)
    if not tree.body or any(not isinstance(node, ast.FunctionDef) for node in tree.body):
        raise ValueError("top_level_code_not_allowed")
    if not any(n.name == expected_function for n in tree.body):
        raise ValueError("required_function_missing")
    for node in ast.walk(tree):
        if isinstance(node, BANNED):
            raise ValueError("unsafe_syntax")
        if isinstance(node, (ast.Attribute,)):
            if node.attr not in METHODS:
                raise ValueError("unauthorized_attribute")
        if isinstance(node, ast.Name) and ("__" in node.id or node.id in {
            "open", "eval", "exec", "compile", "globals", "locals",
            "getattr", "setattr", "delattr", "__import__", "breakpoint",
        }):
            raise ValueError("forbidden_identifier")
        if isinstance(node, ast.FunctionDef) and node.decorator_list:
            raise ValueError("function_decorators_forbidden")
    return tree


def reference_intervals(windows):
    cleaned = []
    for v in windows:
        a, b = v
        if b < a:
            raise ValueError("end_before_start")
        if b != a:
            cleaned.append((a, b))
    cleaned.sort()
    out = []
    for a, b in cleaned:
        if out and a <= out[-1][1]:
            out[-1] = (out[-1][0], max(b, out[-1][1]))
        else:
            out.append((a, b))
    return out


def reference_dependencies(graph):
    all_names = set(graph)
    for dep in graph.values():
        all_names.update(dep)
    remaining = {k: set(graph.get(k, [])) for k in all_names}
    order = []
    while remaining:
        ready = sorted(k for k, v in remaining.items() if not v)
        if not ready:
            raise ValueError("cycle")
        name = ready[0]
        order.append(name)
        del remaining[name]
        for deps in remaining.values():
            deps.discard(name)
    return order


def reference_inventory(rows):
    seen = set()
    counts = {}
    for x in rows:
        if not isinstance(x, dict):
            raise ValueError("row_invalid")
        event_id, sku, delta = x.get("event_id"), x.get("sku"), x.get("delta")
        if not isinstance(event_id, str) or not event_id or not isinstance(sku, str) or not sku or type(delta) is not int:
            raise ValueError("field_invalid")
        if event_id in seen:
            continue
        seen.add(event_id)
        counts[sku] = counts.get(sku, 0) + delta
    return {key: counts[key] for key in sorted(counts)}


ORACLES = {
    "intervals": ("merge_time_windows", reference_intervals),
    "dependencies": ("resolve_dependency_order", reference_dependencies),
    "inventory": ("summarize_inventory_movements", reference_inventory),
}


def fixtures(task_id: str, phase: str):
    if phase not in ("development", "holdout"):
        raise ValueError("invalid phase")
    rng = random.Random(21041 if phase == "development" else 91733)
    if task_id == "intervals":
        cases = [
            [], [(1, 3), (3, 5)], [(1, 5), (2, 3)],
            [(0, 0)], [(4, 2)], [(-5, -1), (-1, 0)],
            [[5, 8], [1, 2], [3, 5]], [(2, 2), (4, 4), (8, 10)],
            [(1, 8), (3, 9), (0, 4)],
        ]
        for _ in range(50):
            cases.append([(rng.randrange(-30, 31), rng.randrange(-30, 31))
                          for j in range(rng.randrange(0, 12))])
        return cases
    if task_id == "dependencies":
        cases = [
            {}, {"build": ["test"], "test": []},
            {"A": ["A"]}, {"A": ["B"], "B": ["A"]},
            {"A": ["B", "C"], "D": ["B"]},
            {"z": ["a"], "a": [], "b": []},
            {"X": ["missing"]},
            {"z": [], "a": [], "c": []},
        ]
        alphabet = [f"T{i}" for i in range(8)]
        for _ in range(50):
            n = rng.randrange(1, 9)
            names = alphabet[:n]
            graph = {name: [prereq for prereq in names[:i]
                            if rng.random() < 0.25] for i, name in enumerate(names)}
            if rng.random() < 0.16:
                last = names[-1]
                graph[last].append(last)
            if rng.random() < 0.25:
                graph.pop(rng.choice(names), None)
            cases.append(graph)
        return cases
    if task_id == "inventory":
        cases = [
            [],
            [{"event_id": "a", "sku": "x", "delta": 5},
             {"event_id": "a", "sku": "x", "delta": 100}],
            [{"event_id": "b", "sku": "z", "delta": 1},
             {"event_id": "a", "sku": "a", "delta": -1}],
            [{"event_id": "bad", "sku": "x", "delta": True}],
            [{"event_id": "bad", "sku": "", "delta": 1}],
            [{"event_id": "bad", "sku": "x", "delta": 1.5}],
            [{"event_id": "bad", "sku": "x", "delta": -3},
             {"event_id": "bad", "sku": "x", "delta": 0}],
        ]
        for _ in range(50):
            rows = []
            for j in range(rng.randrange(0, 18)):
                eid = f"e{rng.randrange(0, 15)}"
                rows.append({"event_id": eid, "sku": rng.choice("abcde"),
                             "delta": rng.randrange(-8, 9)})
            if rows and rng.random() < 0.18:
                rows[rng.randrange(len(rows))]["delta"] = True
            cases.append(rows)
        return cases
    raise ValueError("unknown task")


def evaluate_in_worker(task_id: str, src: Path, phase: str) -> dict:
    name, oracle = ORACLES[task_id]
    code = src.read_text(encoding="utf-8")
    tree = validate_source(code, name)
    env = {"__builtins__": SAFE_BUILTINS}
    exec(compile(tree, str(src), "exec"), env, env)
    subject = env[name]
    results = []
    for case in fixtures(task_id, phase):
        expected_failure = None
        try:
            expected = oracle(copy.deepcopy(case))
        except ValueError:
            expected_failure = ValueError
            expected = None
        before = copy.deepcopy(case)
        try:
            actual = subject(case)
            failure = None
        except Exception as exc:
            actual = None
            failure = type(exc)
        matches = (failure is ValueError if expected_failure else
                   failure is None and actual == expected)
        if task_id == "inventory" and failure is None and expected_failure is None:
            matches = matches and isinstance(actual, dict) and list(actual) == sorted(actual)
        matches = matches and case == before
        results.append(bool(matches))
    return {"passed": sum(results), "total": len(results),
            "failure_count": len(results)-sum(results)}


def subprocess_grade(task_id: str, path: Path, phase: str) -> dict:
    with tempfile.TemporaryDirectory(prefix="bean021_") as td:
        src = Path(td) / "candidate.py"
        src.write_bytes(path.read_bytes())
        result = subprocess.run(
            [sys.executable, "-I", "-S", str(Path(__file__).resolve()),
             "--worker", task_id, str(src), phase],
            capture_output=True, text=True, timeout=12,
            cwd=td, env={"PATH": os.environ.get("PATH", ""),
                         "PYTHONIOENCODING": "utf-8"},
        )
    if result.returncode != 0:
        return {"passed": 0, "total": len(fixtures(task_id, phase)),
                "failure_count": len(fixtures(task_id, phase)),
                "status": "rejected_or_crashed"}
    try:
        data = json.loads(result.stdout)
        if type(data["passed"]) is not int or data["passed"] < 0 or data["passed"] > data["total"]:
            raise ValueError("invalid worker counts")
        return {**data, "status": "evaluated"}
    except (KeyError, ValueError, TypeError, json.JSONDecodeError):
        return {"passed": 0, "total": len(fixtures(task_id, phase)),
                "failure_count": len(fixtures(task_id, phase)),
                "status": "invalid_worker_output"}


def grade(artifact_dir: Path, output: Path, *, phase: str,
          revision_dir: Path | None = None) -> dict:
    from bean.evaluation.transfer_tasks import TASKS
    if phase not in ("development", "holdout"):
        raise ValueError("bad phase")
    first = json.loads((artifact_dir / "receipt.json").read_text(encoding="utf-8"))
    second = (json.loads((revision_dir / "receipt.json").read_text(encoding="utf-8"))
              if revision_dir is not None else None)
    if first["schema"] != "bean.autonomy.lab021.generation.v1":
        raise ValueError("untrusted artifact schema")
    if second and second["schema"] != first["schema"]:
        raise ValueError("untrusted revision schema")
    index = {row["task_id"]: row for row in first["tasks"]}
    updated = {row["task_id"]: row for row in second["tasks"]} if second else {}
    results = []
    for task in TASKS:
        def assess(doc, record, directory):
            if not record or record["provider_status"] != "proposal_generated":
                return {"passed": 0, "total": len(fixtures(task.task_id, phase)),
                        "status": "not_tested"}
            if record["model_requested"] != "openrouter/free":
                raise ValueError("free route contract broken")
            path = directory / f"{task.task_id}.py"
            if hashlib.sha256(path.read_bytes()).hexdigest() != record["source_sha256"]:
                raise ValueError("source digest mismatch")
            return subprocess_grade(task.task_id, path, phase)
        primary = assess(first, index.get(task.task_id), artifact_dir)
        new = assess(second, updated.get(task.task_id), revision_dir) if second else None
        # Selection is determined by previous DEVELOPMENT feedback alone.
        # This HOLDOUT must never be used to choose the winning candidate.
        revised_was_generated = bool(second and updated.get(task.task_id, {}).get(
            "provider_status") == "proposal_generated")
        selected = new if revised_was_generated else primary
        with tempfile.TemporaryDirectory(prefix="bean021_baseline_") as td:
            p = Path(td) / "baseline.py"
            p.write_text(task.original, encoding="utf-8")
            baseline = subprocess_grade(task.task_id, p, phase)
        results.append({
            "task_id": task.task_id,
            "passed": primary["passed"], "total": primary["total"],
            "status": primary["status"], "revision": new,
            "baseline_passed": baseline["passed"],
            "selected": "revision" if revised_was_generated else "initial",
            "selected_passed": selected["passed"],
        })
    summary = {
        "schema": "bean.autonomy.lab021.evaluation.v1", "phase": phase,
        "tasks": results,
        "initial_total": sum(x["passed"] for x in results),
        "baseline_total": sum(x["baseline_passed"] for x in results),
        "selected_total": sum(x["selected_passed"] for x in results),
        "possible_total": sum(x["total"] for x in results),
        "revision_total": sum(x["revision"]["passed"] for x in results
                              if x["revision"] is not None),
        "revision_attempts": sum(x["revision"] is not None for x in results),
        "external_provider_requests": first.get("total_requests", 0) +
            (second.get("total_requests", 0) if second else 0),
        "independent_holdout": phase == "holdout",
        "constraints": [
            "Never pass holdout samples to a code-authoring model",
            "Scores are for independent, synthetic algorithmic tasks",
            "No conclusion on general intelligence from these fixtures",
        ],
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return summary


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--initial", type=Path)
    parser.add_argument("--revised", type=Path)
    parser.add_argument("--phase", choices=("development", "holdout"))
    parser.add_argument("--output", type=Path)
    parser.add_argument("--worker", action="store_true")
    parser.add_argument("worker_args", nargs="*")
    args = parser.parse_args()
    if args.worker:
        task_id, source, phase = args.worker_args
        try:
            print(json.dumps(evaluate_in_worker(task_id, Path(source), phase)))
        except Exception:
            raise SystemExit(2)
    else:
        print(json.dumps(grade(args.initial, args.output, phase=args.phase,
                               revision_dir=args.revised), indent=2))


if __name__ == "__main__":
    main()
