"""Independent arithmetic audit of public synthetic learning scoreboard.

Does not execute BEAN Core, establish learning, or authenticate the dataset.
Usage: python scripts/audit_digital_learning_manifest.py research/github_brain/manifest.json
"""
import argparse
import json
from pathlib import Path


def audit(manifest):
    data = manifest["digital_learning"]
    families = data["families"]
    if not families:
        raise ValueError("empty evaluation families")
    expected = {"candidate": "candidate_correct_total",
                "passive": "passive_correct_total",
                "grammar_matched": "grammar_matched_correct_total",
                "memory_ablated": "memory_ablated_correct_total"}
    totals = {}
    for name, field in expected.items():
        total = sum(family["correct"][name] for family in families.values())
        if total != data[field]:
            raise ValueError(f"{field}: family sum {total} differs from reported {data[field]}")
        totals[name] = total
    if totals["candidate"] > data["blind_cases_total"]:
        raise ValueError("candidate correct exceeds blind cases")
    for control, field in (("passive", "candidate_minus_passive_correct_total"),
                           ("grammar_matched", "candidate_minus_grammar_matched_correct_total")):
        delta = totals["candidate"] - totals[control]
        if delta != data[field]:
            raise ValueError(f"{field}: expected {delta}, reported {data[field]}")
    return {"generation": manifest["generation"], "blind_cases": data["blind_cases_total"],
            "totals": totals, "candidate_minus_passive": totals["candidate"] - totals["passive"],
            "candidate_minus_grammar_matched": totals["candidate"] - totals["grammar_matched"],
            "independently_audited": data["independently_audited"],
            "memory_specific_advantage_observed": data["memory_specific_advantage_observed"],
            "scope": "arithmetic_consistency_only_not_core_simulation"}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path)
    args = parser.parse_args()
    print(json.dumps(audit(json.loads(args.manifest.read_text(encoding="utf-8"))),
                     indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
