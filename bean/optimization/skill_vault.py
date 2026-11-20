"""Persistent verified skill promotion and fresh-process reuse for Lab019.

Execution uses autodev.evaluate's disposable unittest project, not a Core import.
It is not an operating-system sandbox or evidence of autonomous learning.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
import shutil
from pathlib import Path
import tempfile

from .autodev import Journal, evaluate, source_digest, target_file, test_digest
from .skill_incubator import NAME


def canonical(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def entry_path(vault, name):
    if not isinstance(name, str) or not NAME.fullmatch(name):
        raise ValueError("invalid skill name")
    root = Path(vault)
    if root.is_symlink():
        raise ValueError("symlink vault")
    root.mkdir(parents=True, exist_ok=True)
    return root.resolve() / name


def promote(*, report, output, journal_path, vault):
    """Promote only a digest-matched source with independent holdout evidence."""
    if (report.get("schema") != "bean.skill_incubator.v1"
            or report.get("skill_promotion_ready") is not True
            or report.get("independent_holdout_verified") is not True
            or report.get("validation_scope") != "separate_holdout"):
        raise ValueError("independent holdout required")
    name = report.get("skill_name")
    entry = entry_path(vault, name)
    target = "bean/skills/" + name + ".py"
    if report.get("target") != target:
        raise ValueError("target mismatch")
    sha = report.get("accepted_source")
    if not isinstance(sha, str) or len(sha) != 64 or any(c not in "0123456789abcdef" for c in sha):
        raise ValueError("invalid source digest")
    source_path = Path(output) / "validated" / target
    if source_path.is_symlink() or not source_path.is_file():
        raise ValueError("validated source missing")
    source = source_path.read_text(encoding="utf-8")
    if source_digest(source) != sha:
        raise ValueError("source changed")
    journal = Journal(journal_path)
    try:
        events = journal.events(report["objective"])
        valid = any(e.get("candidate_sha256") == sha
                    and e.get("outcome") == "validated"
                    and e.get("holdout_passed") is True
                    and e.get("tests_sha256") == report.get("tests_sha256")
                    and e.get("holdout_tests_sha256") == report.get("holdout_tests_sha256")
                    for e in events)
        if not valid:
            raise ValueError("verified journal event missing")
        tip = journal.export()["tip"]
    finally:
        journal.close()
    if entry.exists() or entry.is_symlink():
        raise FileExistsError("already promoted")
    receipt = {"schema": "bean.skill_vault.v1", "name": name, "target": target,
               "source_sha256": sha, "objective": report["objective"],
               "training_tests_sha256": report["tests_sha256"],
               "holdout_tests_sha256": report["holdout_tests_sha256"],
               "journal_tip_at_promotion": tip,
               "execution_scope": "disposable_unittest_only"}
    receipt["receipt_sha256"] = hashlib.sha256(canonical(receipt)).hexdigest()
    with tempfile.TemporaryDirectory(dir=entry.parent, prefix=".skill-stage-") as scratch:
        stage = Path(scratch)
        (stage / "skill.py").write_text(source, encoding="utf-8")
        (stage / "receipt.json").write_bytes(canonical(receipt))
        os.rename(stage, entry)
    return receipt


def retrieve(*, vault, name):
    """Verify source and receipt on every retrieval, including after restart."""
    entry = entry_path(vault, name)
    receipt_path, source_path = entry / "receipt.json", entry / "skill.py"
    if entry.is_symlink() or receipt_path.is_symlink() or source_path.is_symlink():
        raise ValueError("linked skill")
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    digest = receipt.pop("receipt_sha256", None)
    if (receipt.get("schema") != "bean.skill_vault.v1"
            or receipt.get("name") != name
            or receipt.get("target") != "bean/skills/" + name + ".py"
            or hashlib.sha256(canonical(receipt)).hexdigest() != digest):
        raise ValueError("invalid receipt")
    source = source_path.read_text(encoding="utf-8")
    if source_digest(source) != receipt["source_sha256"]:
        raise ValueError("altered skill")
    return {**receipt, "receipt_sha256": digest, "source": source}


def reuse(*, vault, name, project):
    """Run retained code on another frozen test project without model invocation."""
    item = retrieve(vault=vault, name=name)
    root = Path(project)
    if root.is_symlink():
        raise ValueError("linked project")
    root = root.resolve(strict=True)
    for p in root.rglob("*"):
        if p.is_symlink():
            raise ValueError("linked test input")
    tests_sha = test_digest(root / "tests")
    # A withheld project may contain tests but no implementation yet.
    # Materialize the retained skill only in a disposable project, never
    # mutate the caller's project or weaken autodev's target validation.
    with tempfile.TemporaryDirectory(prefix="bean-reuse-") as scratch:
        work = Path(scratch) / "project"
        shutil.copytree(root, work, symlinks=False)
        target = work / item["target"]
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.exists():
            target.write_text("", encoding="utf-8")
        target_file(work, item["target"])
        result = evaluate(work, item["target"], item["source"])
    return {"schema": "bean.skill_reuse.v1", "name": name,
            "source_sha256": item["source_sha256"],
            "receipt_sha256": item["receipt_sha256"],
            "reuse_tests_sha256": tests_sha,
            "independent_from_promotion_holdout":
                tests_sha not in (item["training_tests_sha256"], item["holdout_tests_sha256"]),
            "result": result, "passed": result["passed"] and result["test_count"] > 0,
            "provider_invoked": False, "execution_scope": "disposable_unittest_only"}


def main():
    cli = argparse.ArgumentParser(description="BEAN skill promotion and restart reuse")
    sub = cli.add_subparsers(dest="command", required=True)
    p = sub.add_parser("promote")
    p.add_argument("--report", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--journal", type=Path, required=True)
    p.add_argument("--vault", type=Path, required=True)
    p = sub.add_parser("reuse")
    p.add_argument("--vault", type=Path, required=True)
    p.add_argument("--name", required=True)
    p.add_argument("--project", type=Path, required=True)
    args = cli.parse_args()
    result = (promote(report=json.loads(args.report.read_text()), output=args.output,
                      journal_path=args.journal, vault=args.vault)
              if args.command == "promote" else
              reuse(vault=args.vault, name=args.name, project=args.project))
    print(json.dumps(result, indent=2, sort_keys=True))
    if args.command == "reuse" and not result["passed"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
