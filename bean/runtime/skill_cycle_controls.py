"""Evaluate a retained BEAN skill against frozen source controls on identical tests.

This is a same-test execution comparison, not proof of independently authored
controls, equal generation budgets, or autonomous learning. The evaluator
never invokes a model or mutates the caller's frozen test project.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import tempfile

from bean.optimization.autodev import evaluate, source_digest, target_file, test_digest
from bean.optimization.skill_vault import retrieve


def compare(*, vault, name: str, project, controls: dict[str, str]) -> dict:
    """Evaluate candidate and externally supplied frozen controls under one harness."""
    if not controls or not {"frozen", "no_memory", "grammar_matched", "strong"} <= set(controls):
        raise ValueError("four required control arms missing")
    if set(controls) != {"frozen", "no_memory", "grammar_matched", "strong"}:
        raise ValueError("unexpected control arm")
    root = Path(project)
    if root.is_symlink():
        raise ValueError("symlink evaluation root")
    root = root.resolve(strict=True)
    if any(p.is_symlink() for p in root.rglob("*")):
        raise ValueError("symlink evaluation input")
    item = retrieve(vault=vault, name=name)
    sources = {"candidate": item["source"]}
    for arm, source_path in controls.items():
        path = Path(source_path)
        if path.is_symlink() or not path.is_file():
            raise ValueError("missing or linked control: " + arm)
        sources[arm] = path.read_text(encoding="utf-8")
    manifest = {
        "tests_sha256": test_digest(root / "tests"),
        "arms": {arm: source_digest(src) for arm, src in sorted(sources.items())},
    }
    outcomes = {}
    for arm, source in sources.items():
        with tempfile.TemporaryDirectory(prefix="bean-control-") as temp:
            work = Path(temp) / "project"
            shutil.copytree(root, work, symlinks=False)
            target = work / item["target"]
            target.parent.mkdir(parents=True, exist_ok=True)
            if not target.exists():
                target.write_text("", encoding="utf-8")
            target_file(work, item["target"])
            result = evaluate(work, item["target"], source)
            outcomes[arm] = {
                "passed": bool(result["passed"] and result["test_count"] > 0),
                "test_count": result["test_count"],
                "source_sha256": manifest["arms"][arm],
            }
    candidate = outcomes["candidate"]["passed"]
    strong = outcomes["strong"]["passed"]
    return {
        "schema": "bean.native_skill_controls.v1",
        "skill": name,
        "test_manifest_sha256": hashlib.sha256(
            json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest(),
        "manifest": manifest,
        "outcomes": outcomes,
        "candidate_beats_strong": bool(candidate and not strong),
        "equal_test_harness": True,
        "equal_generation_budget_verified": False,
        "independent_control_provenance_verified": False,
        "model_invoked": False,
        "strong_control_advantage_verified": False,
    }


def main():
    parser = argparse.ArgumentParser(description="BEAN frozen five-arm skill comparison")
    parser.add_argument("--vault", required=True)
    parser.add_argument("--name", required=True)
    parser.add_argument("--project", required=True)
    for arm in ("frozen", "no_memory", "grammar_matched", "strong"):
        parser.add_argument("--" + arm.replace("_", "-"), required=True)
    args = parser.parse_args()
    result = compare(
        vault=args.vault, name=args.name, project=args.project,
        controls={arm: getattr(args, arm)
                  for arm in ("frozen", "no_memory", "grammar_matched", "strong")},
    )
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
