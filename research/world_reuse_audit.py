"""Audit repeated synthetic world rules without reading any BEAN checkpoint.

Run: python research/world_reuse_audit.py
This measures fixture diversity, not agent intelligence or transfer.
"""
import json
import random

FAMILIES = ("channel", "difference", "parity")


def world_signature(generation, family_index):
    world_id = 100000 + generation * 100 + family_index
    rng = random.Random(world_id * 179)
    a, b = rng.sample(range(4), 2)
    polarity = rng.choice((-1, 1))
    rng.choice((-1, 0, 1))  # Unused constant drawn by World.__init__.
    family = FAMILIES[family_index]
    if family == "channel":
        return (a, polarity)
    if family == "parity":
        return (min(a, b), max(a, b), polarity)
    # (a-b)*polarity == (b-a)*(-polarity)
    forward = (a, b, polarity)
    reverse = (b, a, -polarity)
    return min(forward, reverse)


def audit(generations=33):
    if not 1 <= generations <= 99999:
        raise ValueError("generations out of range")
    result = {}
    for index, family in enumerate(FAMILIES):
        signatures = [world_signature(g, index) for g in range(1, generations + 1)]
        unique = len(set(signatures))
        result[family] = {
            "generations": generations,
            "unique_effective_rules": unique,
            "repeated_rule_generations": generations - unique,
            "latest_rule_previously_seen": signatures[-1] in signatures[:-1],
        }
    return result


if __name__ == "__main__":
    print(json.dumps(audit(), indent=2, sort_keys=True))
