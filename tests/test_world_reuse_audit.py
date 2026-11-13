"""Falsification tests for the synthetic-rule reuse audit.

A canonical signature must preserve the World decision function, not merely
match constructor parameter tuples. This does not test BEAN's learning.
"""
import itertools
import random

from research.world_reuse_audit import FAMILIES, world_signature
from bean.evaluation.active_abstraction_benchmark import World


def _decision(family, a, b, polarity, state):
    if family == "channel":
        signal = state[a] * polarity
    elif family == "difference":
        signal = (state[a] - state[b]) * polarity
    else:
        signal = state[a] * state[b] * polarity
    return (signal > 0) - (signal < 0)


def _canonical(family, a, b, polarity):
    if family == "channel":
        return (a, polarity)
    if family == "parity":
        return (min(a, b), max(a, b), polarity)
    return min((a, b, polarity), (b, a, -polarity))


def test_signature_matches_actual_world_constructor():
    for generation in range(1, 101):
        for index, family in enumerate(FAMILIES):
            world = World(100000 + generation * 100 + index, family)
            assert world_signature(generation, index) == _canonical(
                family, world.a, world.b, world.polarity)


def test_canonical_classes_are_behaviorally_equivalent_and_distinct():
    # All 4*3*2 parameterizations, not just sampled generations.
    rng = random.Random(20261113)
    states = [tuple(rng.uniform(-1, 1) for _ in range(4)) for _ in range(256)]
    for family, expected in (("channel", 8), ("difference", 12), ("parity", 12)):
        groups = {}
        for a, b in itertools.permutations(range(4), 2):
            for polarity in (-1, 1):
                key = _canonical(family, a, b, polarity)
                behavior = tuple(_decision(family, a, b, polarity, state)
                                 for state in states)
                if key in groups:
                    assert groups[key] == behavior, (family, key)
                else:
                    groups[key] = behavior
        assert len(groups) == expected
        # Detect accidental collapse of distinct decision rules.
        assert len(set(groups.values())) == expected
