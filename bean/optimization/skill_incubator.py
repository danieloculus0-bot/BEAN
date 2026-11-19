"""BEAN skill incubation: create an executable skill from a natural-language goal.

Inspired by BabyAGI's skill-creation loop, but reuses BEAN Lab019's
source author, frozen evaluations, SHA journal, and existing memory.
A returned candidate is NOT installed into Core or evidence of AGI.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import shutil
import tempfile

from .autodev import ASTBruteForce, ModelWriter, run_cycle

NAME = re.compile(r"^[a-z][a-z0-9_]{1,63}$")
STUB = '"""Unimplemented BEAN skill. Candidate source must supply the API."""\n'


def incubate_skill(*, project, name, task, journal_path, output, provider,
                   attempts=10, holdout_project=None):
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
    else:
        other = None

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
    return report


def main():
    parser = argparse.ArgumentParser(description="BEAN model-authored skill incubation")
    parser.add_argument("--project", type=Path, required=True)
    parser.add_argument("--holdout-project", type=Path, default=None)
    parser.add_argument("--name", required=True)
    parser.add_argument("--task", required=True)
    parser.add_argument("--journal", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--provider", choices=("ollama", "openrouter"), default="ollama")
    parser.add_argument("--model", default="qwen2.5-coder:7b")
    parser.add_argument("--attempts", type=int, default=10)
    args = parser.parse_args()
    report = incubate_skill(
        project=args.project, holdout_project=args.holdout_project,
        name=args.name, task=args.task, journal_path=args.journal,
        output=args.output, provider=ModelWriter(args.provider, args.model),
        attempts=args.attempts)
    print(json.dumps(report, indent=2, sort_keys=True))
    if not report["skill_promotion_ready"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
