"""BEAN skill incubation: create an executable skill from a natural-language goal.

Inspired by BabyAGI's skill-creation loop, but reuses BEAN Lab019's
source author, frozen evaluations, SHA journal, and existing memory.
A returned candidate is NOT installed into Core or evidence of AGI.
"""
from __future__ import annotations

import argparse
from contextlib import closing
import ast
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import sqlite3
import tempfile

from .autodev import ASTBruteForce, ModelWriter, run_cycle

def _test_ast_fingerprints(root):
    """Ignore comments and formatting when comparing Python evaluator suites."""
    return sorted(ast.dump(ast.parse(path.read_text(encoding="utf-8")),
                               include_attributes=False)
                  for path in (root / "tests").rglob("*.py"))


NAME = re.compile(r"^[a-z][a-z0-9_]{1,63}$")
STUB = '"""Unimplemented BEAN skill. Candidate source must supply the API."""\n'


def persist_verified_skill(database, *, name, source_path, source_sha256, objective):
    """Store only independently verified source for a future separate-process reuse."""
    if not NAME.fullmatch(name) or not isinstance(objective, str) or len(objective) != 64:
        raise ValueError("invalid skill identity or objective")
    source_path = Path(source_path)
    if source_path.is_symlink() or not source_path.is_file():
        raise ValueError("validated skill source missing or linked")
    source = source_path.read_text(encoding="utf-8")
    actual = hashlib.sha256(source.encode("utf-8")).hexdigest()
    if actual != source_sha256:
        raise ValueError("validated skill source SHA mismatch")
    ast.parse(source)
    database = Path(database)
    if database.is_symlink():
        raise ValueError("skill database symlink rejected")
    database.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(database)) as db, db:
        db.execute("""CREATE TABLE IF NOT EXISTS verified_skills (
            name TEXT NOT NULL, objective TEXT NOT NULL, source TEXT NOT NULL,
            sha256 TEXT NOT NULL, PRIMARY KEY(name, objective))""")
        prior = db.execute("SELECT sha256 FROM verified_skills WHERE name=? AND objective=?",
                           (name, objective)).fetchone()
        if prior and prior[0] != actual:
            raise ValueError("existing verified skill conflicts with new source")
        db.execute("INSERT OR IGNORE INTO verified_skills VALUES (?, ?, ?, ?)",
                   (name, objective, source, actual))
    return {"name": name, "objective": objective, "source_sha256": actual,
            "database": str(database), "installed_into_core": False}


def retrieve_verified_skill(database, *, name, objective):
    """Verify and return retained source, including after an interpreter restart."""
    with closing(sqlite3.connect(database)) as db, db:
        row = db.execute("SELECT source, sha256 FROM verified_skills "
                         "WHERE name=? AND objective=?", (name, objective)).fetchone()
    if row is None:
        raise LookupError("verified skill not found")
    source, expected = row
    if hashlib.sha256(source.encode("utf-8")).hexdigest() != expected:
        raise ValueError("retained skill SHA mismatch")
    ast.parse(source)
    return source



def evaluate_retained_skill(database, *, name, objective, evaluation_project,
                            timeout=30):
    """Run SHA-verified retained source against host-owned tests in a fresh interpreter.

    This is an execution/evaluation interface, not an OS security sandbox.
    Never pass an untrusted project or treat passing tests as independent learning.
    """
    if not isinstance(name, str) or not NAME.fullmatch(name):
        raise ValueError("invalid retained skill name")
    if type(timeout) is not int or not 1 <= timeout <= 120:
        raise ValueError("invalid evaluation timeout")
    source = retrieve_verified_skill(database, name=name, objective=objective)
    digest = hashlib.sha256(source.encode("utf-8")).hexdigest()
    project = Path(evaluation_project).resolve(strict=True)
    if not (project / "tests").is_dir():
        raise ValueError("evaluation project requires tests")
    target = Path("bean") / "skills" / (name + ".py")
    if (project / target).exists() or (project / target).is_symlink():
        raise ValueError("evaluation project already contains skill")
    for entry in project.rglob("*"):
        if entry.is_symlink():
            raise ValueError("evaluation project contains symlink")
    with tempfile.TemporaryDirectory(prefix="bean-retained-evaluation-") as temp:
        staged = Path(temp) / "project"
        shutil.copytree(project, staged, symlinks=False,
                        ignore=shutil.ignore_patterns(
                            ".git", ".venv", "venv", "__pycache__", ".pytest_cache"))
        module = staged / target
        module.parent.mkdir(parents=True, exist_ok=True)
        module.write_text(source, encoding="utf-8")
        try:
            completed = subprocess.run(
                [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"],
                cwd=staged, capture_output=True, text=True, timeout=timeout,
                env={"PATH": __import__("os").environ.get("PATH", ""),
                     "PYTHONPATH": str(staged)},
                check=False)
        except subprocess.TimeoutExpired:
            return {"status": "timeout", "source_sha256": digest,
                    "passed": False, "fresh_process": True}
    return {"status": "passed" if completed.returncode == 0 else "failed",
            "source_sha256": digest, "passed": completed.returncode == 0,
            "fresh_process": True, "exit_code": completed.returncode,
            "output_tail": (completed.stdout + completed.stderr)[-3000:]}


def incubate_skill(*, project, name, task, journal_path, output, provider,
                   attempts=10, holdout_project=None, skill_db=None):
    """Incubate a new Python skill, without modifying the input project.

    Independent, separately-authored holdout tests are needed before a skill
    receives a promotion-ready receipt. A run with only training tests remains
    training-only, even if every test passes.
    """
    if not isinstance(name, str) or not NAME.fullmatch(name):
        raise ValueError("skill name must be a bounded lowercase Python identifier")
    if not isinstance(task, str) or not 12 <= len(task.strip()) <= 4000:
        raise ValueError("skill objective must be 12..4000 characters")
    source = Path(project).resolve(strict=True)
    if not (source / "tests").is_dir():
        raise ValueError("incubation requires a frozen independent test directory")
    target = "bean/skills/" + name + ".py"
    if (source / target).exists() or (source / target).is_symlink():
        raise ValueError("skill already exists: do not silently overwrite")
    if holdout_project is not None:
        other = Path(holdout_project).resolve(strict=True)
        if other == source or not (other / "tests").is_dir():
            raise ValueError("holdout must be a different project with tests")
        if (other / target).exists() or (other / target).is_symlink():
            raise ValueError("holdout skill target already exists")
        if _test_ast_fingerprints(source) == _test_ast_fingerprints(other):
            raise ValueError("holdout evaluator duplicates training assertions")
    else:
        other = None

    # copytree(symlinks=False) follows source symlinks. Never stage linked
    # external files or directories, including linked test fixtures.
    for label, root in (("training", source), ("holdout", other)):
        if root is None:
            continue
        for entry in root.rglob("*"):
            if entry.is_symlink():
                raise ValueError(label + " project contains symlink: " +
                                 str(entry.relative_to(root)))

    with tempfile.TemporaryDirectory(prefix="bean-skill-incubator-") as scratch:
        scratch = Path(scratch)
        staged = scratch / "training"
        shutil.copytree(source, staged, symlinks=False, ignore=shutil.ignore_patterns(
            ".git", ".venv", "venv", "__pycache__", ".pytest_cache"))
        placeholder = staged / target
        placeholder.parent.mkdir(parents=True, exist_ok=True)
        placeholder.write_text(STUB, encoding="utf-8")
        held_stage = None
        if other is not None:
            held_stage = scratch / "holdout"
            shutil.copytree(other, held_stage, symlinks=False,
                            ignore=shutil.ignore_patterns(
                                ".git", ".venv", "venv", "__pycache__", ".pytest_cache"))
            held_placeholder = held_stage / target
            held_placeholder.parent.mkdir(parents=True, exist_ok=True)
            held_placeholder.write_text(STUB, encoding="utf-8")
        report = run_cycle(
            project=staged, target=target, task=task, journal_path=journal_path,
            output=output, provider=provider, attempts=attempts,
            holdout_project=held_stage)
    report.update({
        "schema": "bean.skill_incubator.v1", "skill_name": name,
        "skill_newly_created": report["status"] == "validated_patch_written",
        "installed_into_core": False,
        "independent_holdout_verified": bool(report["skill_promotion_ready"]),
        "skill_origin": "model_generated_or_supplied_provider_not_proof_of_autonomy",
    })
    if skill_db is not None and report["skill_promotion_ready"]:
        report["retained_skill"] = persist_verified_skill(
            skill_db, name=name, source_path=report["validated_path"],
            source_sha256=report["accepted_source"], objective=report["objective"])
    return report


def main():
    parser = argparse.ArgumentParser(description="BEAN model-authored skill incubation")
    parser.add_argument("--project", type=Path, required=True)
    parser.add_argument("--holdout-project", type=Path, default=None)
    parser.add_argument("--name", required=True)
    parser.add_argument("--task", required=True)
    parser.add_argument("--journal", type=Path, required=True)
    parser.add_argument("--skill-db", type=Path, default=None,
                        help="Optional SHA-checked SQLite store for independently verified skills")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--provider", choices=("ollama", "llamacpp", "openrouter"), default="ollama")
    parser.add_argument("--model", default=None,
                        help="Model identifier; defaults to qwen2.5-coder:7b for Ollama or bean-local for llama.cpp")
    parser.add_argument("--attempts", type=int, default=10)
    args = parser.parse_args()
    report = incubate_skill(
        project=args.project, holdout_project=args.holdout_project,
        name=args.name, task=args.task, journal_path=args.journal,
        output=args.output, provider=ModelWriter(args.provider, args.model or
                             ("bean-local" if args.provider == "llamacpp" else "qwen2.5-coder:7b")),
        attempts=args.attempts, skill_db=args.skill_db)
    print(json.dumps(report, indent=2, sort_keys=True))
    if not report["skill_promotion_ready"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
