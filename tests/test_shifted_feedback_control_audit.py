"""Audit whether the legacy shifted-case 'shuffled' feedback is truly wrong.

This is a deterministic, evaluator-only negative-control diagnostic. It never
changes BEAN's journal, reward policy, checkpoint, or live Core state.
"""
from bean.evaluation.active_abstraction_benchmark import World
from bean.evaluation.github_digital_cycle import FAMILIES, TRAIN, BUDGET


def shifted_feedback_audit(generations=range(1, 33)):
    """Return collision counts for the existing +1,000,000 case-ID offset."""
    rows = []
    for generation in generations:
        for family_index, family in enumerate(FAMILIES):
            world = World(100000 + generation * 100 + family_index, family)
            probes = (TRAIN if generation == 1 else tuple(
                str(generation * 1000000 + int(pid)) for pid in TRAIN))
            same = sum(
                world.correct_action(case) ==
                world.correct_action(str(int(case) + 1000000))
                for case in probes
            )
            rows.append({
                "generation": generation,
                "family": family,
                "training_cases": len(probes),
                "shifted_truth_collisions": same,
                "collision_fraction": same / len(probes),
                "budget_probes": BUDGET,
            })
    return rows


def test_shifted_feedback_is_not_guaranteed_incorrect():
    rows = shifted_feedback_audit()
    assert len(rows) == 32 * len(FAMILIES)
    assert all(row["training_cases"] == len(TRAIN) for row in rows)
    # A shifted case can have the same correct action. Therefore rewarding
    # its label is not an adversarially wrong-label control.
    assert any(row["shifted_truth_collisions"] > 0 for row in rows)
    assert any(row["shifted_truth_collisions"] < row["training_cases"]
               for row in rows)


if __name__ == "__main__":
    import json
    print(json.dumps({
        "schema": "bean.shifted_feedback_audit.v1",
        "scope": "synthetic_evaluator_only",
        "rows": shifted_feedback_audit(),
        "interpretation": "Shifted-case feedback is not guaranteed wrong; "
                          "do not call it a forced-incorrect-label control.",
    }, sort_keys=True, indent=2))
