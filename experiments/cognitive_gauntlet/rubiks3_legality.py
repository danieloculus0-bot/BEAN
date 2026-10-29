"""Physical 3x3 reachability checks for BEAN's facelet-state cube benchmark.

A balanced 54-character color string is not necessarily a legal cube.
Reject impossible center arrangements, duplicate/missing cubies, single twists,
single flips, and odd swaps. This is a task-integrity validator, NOT a solver.
"""
from __future__ import annotations

from collections import defaultdict

from .rubiks3 import SOLVED, STICKERS


def _det(a, b, c):
    return ((a[1] * b[2] - a[2] * b[1]) * c[0]
            + (a[2] * b[0] - a[0] * b[2]) * c[1]
            + (a[0] * b[1] - a[1] * b[0]) * c[2])


def _groups():
    by_position = defaultdict(list)
    for index, (position, _) in enumerate(STICKERS):
        by_position[position].append(index)
    centers, edges, corners = [], [], []
    for indices in by_position.values():
        if len(indices) == 1:
            centers.append(indices[0])
        elif len(indices) == 2:
            # First sticker is on U/D for top/bottom edges, F/B otherwise.
            axis = 1 if any(STICKERS[i][1][1] for i in indices) else 2
            first = next(i for i in indices if STICKERS[i][1][axis])
            edges.append((first, next(i for i in indices if i != first)))
        elif len(indices) == 3:
            first = next(i for i in indices if STICKERS[i][1][1])
            others = [i for i in indices if i != first]
            if _det(*(STICKERS[i][1] for i in (first, *others))) < 0:
                others.reverse()
            corners.append((first, *others))
        else:
            raise AssertionError('invalid facelet geometry')
    if (len(centers), len(edges), len(corners)) != (6, 12, 8):
        raise AssertionError('expected six centers, twelve edges, eight corners')
    return tuple(centers), tuple(edges), tuple(corners)


CENTERS, EDGES, CORNERS = _groups()
EDGE_IDENTITIES = {frozenset(SOLVED[i] for i in indices): number
                   for number, indices in enumerate(EDGES)}
CORNER_IDENTITIES = {frozenset(SOLVED[i] for i in indices): number
                     for number, indices in enumerate(CORNERS)}


def _parity(permutation):
    return sum(a > b for i, a in enumerate(permutation)
               for b in permutation[i + 1:]) % 2


def validate_legal_cube(state):
    """Raise ValueError if a facelet string cannot be reached by legal turns.

    Validity is independent of the scramble recipe and requires no search.
    Only standard fixed-center 3x3 facelet states are accepted.
    """
    if not isinstance(state, str) or len(state) != 54 or sorted(state) != sorted(SOLVED):
        raise ValueError('invalid 3x3 facelet colors')
    if any(state[i] != SOLVED[i] for i in CENTERS):
        raise ValueError('impossible 3x3 center arrangement')

    corner_perm = []
    corner_twist = 0
    for indices in CORNERS:
        identity = frozenset(state[i] for i in indices)
        if identity not in CORNER_IDENTITIES:
            raise ValueError('impossible 3x3 corner identity')
        corner_perm.append(CORNER_IDENTITIES[identity])
        corner_twist += next(j for j, i in enumerate(indices) if state[i] in 'UD')
    if len(set(corner_perm)) != 8:
        raise ValueError('duplicate 3x3 corner piece')
    if corner_twist % 3:
        raise ValueError('impossible 3x3 corner twist')

    edge_perm = []
    edge_flip = 0
    for indices in EDGES:
        identity = frozenset(state[i] for i in indices)
        if identity not in EDGE_IDENTITIES:
            raise ValueError('impossible 3x3 edge identity')
        edge_perm.append(EDGE_IDENTITIES[identity])
        reference_color = (next((c for c in identity if c in 'UD'), None)
                           or next(c for c in identity if c in 'FB'))
        edge_flip += state[indices[0]] != reference_color
    if len(set(edge_perm)) != 12:
        raise ValueError('duplicate 3x3 edge piece')
    if edge_flip % 2:
        raise ValueError('impossible 3x3 edge flip')
    if _parity(corner_perm) != _parity(edge_perm):
        raise ValueError('impossible 3x3 permutation parity')
