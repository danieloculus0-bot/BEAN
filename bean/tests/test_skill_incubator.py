"""Acceptance tests for BabyAGI-inspired new-skill incubation on BEAN Core."""
from pathlib import Path

import pytest

from bean.optimization.skill_incubator import incubate_skill


class Writer:
    def __init__(self, source):
        self.source = source
        self.calls = 0

    def propose(self, task, original, history, iteration):
        self.calls += 1
        return self.source


GOOD = "def double(value):\n    return value * 2\n"
OVERFIT = "def double(value):\n    return value * 2 if 0 <= value <= 3 else 0\n"
TASK = "Create a reusable doubling function for arbitrary signed integers"


def make_project(root, expressions):
    (root / "tests").mkdir(parents=True)
    (root / "bean" / "skills").mkdir(parents=True)
    (root / "bean" / "__init__.py").write_text("")
    (root / "bean" / "skills" / "__init__.py").write_text("")
    assertions = "\n".join(
        f"    def test_case_{i}(self):\n"
        f"        self.assertEqual(double({arg}), {expected})"
        for i, (arg, expected) in enumerate(expressions)
    )
    (root / "tests" / "test_double.py").write_text(
        "import unittest\n"
        "from bean.skills.double import double\n"
        "class DoublingChecks(unittest.TestCase):\n" + assertions + "\n")
    return root


def setup(tmp_path, provider, with_holdout=True):
    train = make_project(tmp_path / "train", [(2, 4), (3, 6)])
    held = make_project(tmp_path / "heldout", [(7, 14), (-3, -6)])
    return dict(
        project=train, holdout_project=held if with_holdout else None,
        name="double", task=TASK, journal_path=tmp_path / "journal.sqlite",
        output=tmp_path / "artifacts", provider=provider, attempts=2)


def test_real_new_code_passes_two_independent_suites_without_installing(tmp_path):
    writer = Writer(GOOD)
    args = setup(tmp_path, writer)
    result = incubate_skill(**args)
    assert writer.calls == 1
    assert result["status"] == "validated_patch_written"
    assert result["skill_promotion_ready"] is True
    assert result["independent_holdout_verified"] is True
    assert result["installed_into_core"] is False
    assert result["tests_passed"] == 2
    assert result["holdout_tests_passed"] == 2
    assert Path(result["validated_path"]).read_text() == GOOD
    assert not (args["project"] / "bean/skills/double.py").exists()
    assert not (args["holdout_project"] / "bean/skills/double.py").exists()


def test_restart_recovers_missing_skill_artifact_without_reinventing(tmp_path):
    writer = Writer(GOOD)
    args = setup(tmp_path, writer)
    first = incubate_skill(**args)
    path = Path(first["validated_path"])
    path.unlink()
    again = incubate_skill(**args)
    assert writer.calls == 1
    assert again["status"] == "previously_validated_in_memory"
    assert again["recovered_from_archive"] is True
    assert again["skill_promotion_ready"] is True
    assert path.read_text() == GOOD


def test_mutation_of_previous_validated_skill_is_detected(tmp_path):
    writer = Writer(GOOD)
    args = setup(tmp_path, writer)
    first = incubate_skill(**args)
    Path(first["validated_path"]).write_text("def double(x): return 0\n")
    with pytest.raises(ValueError, match="previously validated source has changed"):
        incubate_skill(**args)


def test_training_fit_cannot_override_holdout_failure_or_leak_answer(tmp_path):
    writer = Writer(OVERFIT)
    args = setup(tmp_path, writer)
    result = incubate_skill(**args)
    assert result["status"] == "holdout_rejected"
    assert result["skill_promotion_ready"] is False
    assert result["new_attempts"] == 1
    assert writer.calls == 1
    assert not (args["output"] / "validated/bean/skills/double.py").exists()
    again = incubate_skill(**args)
    assert again["status"] == "holdout_rejected"
    assert writer.calls == 1
    import json
    ledger = json.loads((args["output"] / "journal-export.json").read_text())
    assert ledger["events"][0]["failure"] == "independent_holdout_rejected"
    assert "7" not in ledger["events"][0]["failure"]


def test_training_only_success_is_not_claimed_as_verified_skill(tmp_path):
    args = setup(tmp_path, Writer(GOOD), with_holdout=False)
    result = incubate_skill(**args)
    assert result["status"] == "validated_patch_written"
    assert result["validation_scope"] == "training_only"
    assert result["skill_promotion_ready"] is False
    assert result["independent_holdout_verified"] is False


def test_different_holdout_fingerprint_changes_objective(tmp_path):
    writer = Writer(GOOD)
    args = setup(tmp_path, writer)
    first = incubate_skill(**args)
    held_test = args["holdout_project"] / "tests/test_double.py"
    held_test.write_text(held_test.read_text() + "\n# new frozen evaluation revision\n")
    second = incubate_skill(**args)
    assert first["objective"] != second["objective"]
    assert second["prior_attempts"] == 0


def test_refuses_ambiguous_names_and_existing_skill(tmp_path):
    args = setup(tmp_path, Writer(GOOD))
    for name in ("../double", "__init__", "Double", "a" * 100):
        with pytest.raises(ValueError):
            incubate_skill(**{**args, "name": name})
    existing = args["project"] / "bean/skills/double.py"
    existing.write_text(GOOD)
    with pytest.raises(ValueError, match="already exists"):
        incubate_skill(**args)
