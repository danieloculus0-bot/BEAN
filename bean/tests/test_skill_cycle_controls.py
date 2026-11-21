"""Native persisted-skill comparison acceptance; fixture is NOT a model."""
from bean.runtime.skill_cycle_runner import execute_phase
from bean.runtime.skill_cycle_controls import compare
from bean.tests.test_skill_cycle_runner import FixtureWriter, project


def test_five_arms_use_same_withheld_project_and_do_not_inflate_advantage(tmp_path):
    projects = {}
    for key, value in (("training", 3), ("holdout", -11), ("novel", 29)):
        path = tmp_path / key
        project(path, value)
        projects[key] = str(path)
    config = {
        "database": str(tmp_path / "core.sqlite"),
        "projects": projects,
        "vault": str(tmp_path / "vault"),
        "journal": str(tmp_path / "journal.sqlite"),
        "output": str(tmp_path / "output"),
        "plan_id": "five-arm-integration",
        "name": "double_value",
        "task": "Create a reusable integer doubling function for signed integers",
        "training": "training",
        "holdout": "holdout",
        "novel": "novel",
    }
    acquired = execute_phase(config, phase="acquire", provider=FixtureWriter())
    assert acquired["status"] == "success"
    controls = {}
    for arm in ("frozen", "no_memory", "grammar_matched", "strong"):
        source = tmp_path / (arm + ".py")
        source.write_text(
            "def solve(value):\n    return value * 2\n"
            if arm == "strong" else "def solve(value):\n    return 0\n"
        )
        controls[arm] = str(source)
    result = compare(vault=config["vault"], name=config["name"],
                     project=projects["novel"], controls=controls)
    assert set(result["outcomes"]) == {
        "candidate", "frozen", "no_memory", "grammar_matched", "strong"
    }
    assert result["outcomes"]["candidate"]["passed"] is True
    assert result["outcomes"]["strong"]["passed"] is True
    assert result["candidate_beats_strong"] is False
    assert result["strong_control_advantage_verified"] is False
    assert result["equal_generation_budget_verified"] is False
    assert result["independent_control_provenance_verified"] is False
    assert len({result["manifest"]["tests_sha256"]}) == 1
