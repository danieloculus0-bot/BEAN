"""BEAN-native Rubik's Cube hotter/colder reward experiment.

Uses legal facelet permutations to measure the minimum number of *individual*
face turns required to place and orient each cubie. This is not a full-cube
solution distance or a solution teacher. Potential-based shaping supplies
intermediate feedback while preserving discounted terminal-return rankings.
The comparison keeps SpongeTD, observed transitions, update count, controller,
and holdout cases fixed. Reference solvers and inverse scrambles are never
available to either policy.
"""
from __future__ import annotations

import argparse
from collections import deque
from functools import lru_cache
import hashlib
import json
import os
from pathlib import Path
import random
from tempfile import TemporaryDirectory

from bean.optimization.sponge_td import SpongeTD
from .rubiks3 import MOVES, PERM, SOLVED, apply, scramble, turn
from .rubiks3_legality import CORNERS, EDGES, validate_legal_cube
from .rubiks3_sponge import _digest, collect_states
from .rubiks3_symmetry import canonical, learn_symmetric
from .rubiks3_curriculum import edges_for
from .rubiks3_value_rollout import policy_solve_value_rollout


def _piece_tables():
    """Exact single-cubie turn distances, computed from legal cube geometry."""
    tables = {}
    for kind, groups in (('corner', CORNERS), ('edge', EDGES)):
        for group in groups:
            colors = tuple(SOLVED[i] for i in group)
            start = tuple(group)
            distance = {start: 0}
            queue = deque([start])
            while queue:
                current = queue.popleft()
                for move in MOVES:
                    nxt = tuple(PERM[move][index] for index in current)
                    if nxt not in distance:
                        distance[nxt] = distance[current] + 1
                        queue.append(nxt)
            if len(distance) != 24:
                raise AssertionError('incomplete single-cubie legal state graph')
            tables[frozenset(colors)] = (colors, distance, kind)
    if len(tables) != 20:
        raise AssertionError('expected 20 distinct movable cubies')
    return tables


PIECE_TABLES = _piece_tables()


@lru_cache(maxsize=100_000)
def piece_distances(state):
    """Return corner and edge distance sums, not a shortest cube solution."""
    validate_legal_cube(state)
    corners = edges = 0
    for group in (*CORNERS, *EDGES):
        colors, distances, kind = PIECE_TABLES[frozenset(state[i] for i in group)]
        positions = tuple(next(i for i in group if state[i] == color)
                          for color in colors)
        value = distances[positions]
        if kind == 'corner':
            corners += value
        else:
            edges += value
    return corners, edges


def temperature(state):
    """Higher means hotter; zero is solved. Not an exact cube distance."""
    return -sum(piece_distances(state)) / 8.0


def hotter_colder(before, after):
    """Positive is hotter, negative is colder, zero is equal temperature."""
    return temperature(after) - temperature(before)


def shaped_reward(before, after, gamma=.9):
    """Potential-based reward, r + gamma*Phi(after) - Phi(before).

    Terminal reward is still +1. Because Phi(solved)=0, discounted shaping
    telescopes to a constant depending only on the starting state. This is
    intentionally different from a raw hotter/colder delta when gamma<1.
    """
    if not 0 <= gamma <= 1:
        raise ValueError('gamma outside [0,1]')
    return (1.0 if after == SOLVED else 0.0) + gamma * temperature(after) - temperature(before)


def learn_temperature(learner, states, *, epochs=8, seed=19):
    """Use exactly the same observed legal edges and replay order as learn_symmetric."""
    if type(epochs) is not int or epochs < 1:
        raise ValueError('epochs must be positive')
    edges = edges_for(states)
    rewards = {(state, action): shaped_reward(state, nxt, learner.gamma)
               for state, action, nxt in edges}
    rng = random.Random(seed)
    for _ in range(epochs):
        rng.shuffle(edges)
        for state, action, nxt in edges:
            learner.learn(state, action, rewards[state, action], nxt, nxt == SOLVED)
    return {'legal_observed_edges': len(edges), 'epochs': epochs,
            'td_updates': learner.steps,
            'reward': 'terminal + discounted cubie-distance potential difference'}


def experiment(*, train_seeds=range(50), test_seeds=range(13000, 13010),
               train_lengths=(2, 3, 4, 5, 6),
               test_lengths=(3, 4, 5, 6, 20), epochs=8, output=None):
    train_seeds, test_seeds = tuple(train_seeds), tuple(test_seeds)
    if (not train_seeds or not test_seeds or
            len(set(train_seeds)) != len(train_seeds) or
            len(set(test_seeds)) != len(test_seeds) or
            set(train_seeds) & set(test_seeds)):
        raise ValueError('nonempty, disjoint, unique seed splits required')
    if not train_lengths or not test_lengths:
        raise ValueError('empty scramble lengths')
    states, episodes = collect_states(train_seeds, train_lengths)
    known = {canonical(state)[0] for state in states}
    with TemporaryDirectory(prefix='bean-cube-temperature-') as tmp:
        baseline = SpongeTD(Path(tmp) / 'terminal.db', actions=MOVES,
                            alpha=1, gamma=.9, epsilon=0, seed=19)
        candidate = SpongeTD(Path(tmp) / 'temperature.db', actions=MOVES,
                             alpha=1, gamma=.9, epsilon=0, seed=19)
        try:
            original = learn_symmetric(baseline, states, epochs=epochs)
            shaped = learn_temperature(candidate, states, epochs=epochs)
            if baseline.steps != candidate.steps:
                raise AssertionError('unmatched TD update budgets')
            frozen = (_digest(baseline.q), _digest(candidate.q))
            cases, excluded, seen = [], [], set()
            for seed in test_seeds:
                for length in test_lengths:
                    recipe = scramble(seed, length)
                    state = apply(SOLVED, recipe)
                    key = canonical(state)[0]
                    reason = ('training_symmetry_overlap' if key in known else
                              'duplicate_holdout_symmetry_class' if key in seen else None)
                    if reason:
                        excluded.append({'seed': seed, 'scramble_length': length,
                                         'scramble_evaluator_only': recipe,
                                         'state': state, 'canonical_state': key,
                                         'reason': reason})
                        continue
                    seen.add(key)
                    baseline_moves, bi = policy_solve_value_rollout(baseline, state)
                    candidate_moves, ci = policy_solve_value_rollout(candidate, state)
                    bok = apply(state, baseline_moves) == SOLVED
                    cok = apply(state, candidate_moves) == SOLVED
                    if bok != bi['solved'] or cok != ci['solved']:
                        raise AssertionError('independent solved-state replay mismatch')
                    cases.append({'seed': seed, 'scramble_length': length,
                                  'scramble_evaluator_only': recipe,
                                  'state': state, 'canonical_state': key,
                                  'starting_temperature': temperature(state),
                                  'baseline_moves': baseline_moves,
                                  'baseline_move_count': len(baseline_moves),
                                  'baseline_solved': bok, 'baseline_failure': bi['failure'],
                                  'candidate_moves': candidate_moves,
                                  'candidate_move_count': len(candidate_moves),
                                  'candidate_solved': cok, 'candidate_failure': ci['failure'],
                                  'candidate_better': cok and not bok,
                                  'candidate_worse': bok and not cok,
                                  'candidate_shorter': bok and cok and len(candidate_moves) < len(baseline_moves),
                                  'optimality_proven': False})
            if frozen != (_digest(baseline.q), _digest(candidate.q)):
                raise AssertionError('evaluation mutated frozen learned weights')
            result = {'schema': 'bean.rubiks3.temperature-shaping.v1',
                      'source_revision': os.environ.get('GITHUB_SHA', 'local_unverified'),
                      'module_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                      'mechanism': 'BEAN SpongeTD terminal reward plus legal-cubie potential shaping',
                      'not_full_cube_distance': True, 'not_general_solver': True,
                      'reference_solver_used': False, 'inverse_scramble_used': False,
                      'policy': 'unchanged two-transition learned-value controller for both arms',
                      'train_seeds': list(train_seeds), 'test_seeds': list(test_seeds),
                      'train_lengths': list(train_lengths), 'test_lengths': list(test_lengths),
                      'training_episodes': episodes,
                      'baseline_training': original, 'candidate_training': shaped,
                      'baseline_q_sha256': frozen[0], 'candidate_q_sha256': frozen[1],
                      'eligible_cases': len(cases), 'excluded_count': len(excluded),
                      'baseline_solved': sum(c['baseline_solved'] for c in cases),
                      'candidate_solved': sum(c['candidate_solved'] for c in cases),
                      'candidate_better': sum(c['candidate_better'] for c in cases),
                      'candidate_worse': sum(c['candidate_worse'] for c in cases),
                      'candidate_shorter': sum(c['candidate_shorter'] for c in cases),
                      'twenty_turn_cases': sum(c['scramble_length'] == 20 for c in cases),
                      'twenty_turn_solved': sum(c['candidate_solved'] for c in cases if c['scramble_length'] == 20),
                      'cases': cases, 'excluded': excluded,
                      'caveat': 'Cubie temperature is not exact distance, and shaped TD does not prove full-cube reasoning.'}
            result['sha256'] = _digest(result)
            if output is not None:
                out = Path(output)
                out.parent.mkdir(parents=True, exist_ok=True)
                out.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
            return result
        finally:
            baseline.close()
            candidate.close()


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--test-seed-start', type=int, default=13000)
    p.add_argument('--test-count', type=int, default=10)
    p.add_argument('--epochs', type=int, default=8)
    p.add_argument('--output', default='cognitive-gauntlet-results/rubiks3-temperature-13000.json')
    args = p.parse_args()
    if args.test_count < 1:
        p.error('test-count must be positive')
    result = experiment(test_seeds=range(args.test_seed_start, args.test_seed_start + args.test_count),
                        epochs=args.epochs, output=args.output)
    print(json.dumps({k: result[k] for k in
                      ('eligible_cases', 'excluded_count', 'baseline_solved',
                       'candidate_solved', 'candidate_better', 'candidate_worse',
                       'twenty_turn_cases', 'twenty_turn_solved', 'sha256')}, indent=2))
