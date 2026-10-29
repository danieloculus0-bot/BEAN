"""BEAN-native cubie-subgoal transfer pilot, not a full 3x3 solver.

A single existing SpongeTD learner shares its Q table across 20 labeled
cubie configurations (24 states each). Rewards come from observed legal
self-play transitions and local cubie progress, never solution demonstrations.
At inference BEAN aggregates learned per-piece action values on an unseen
whole-cube state. No reference solver, scramble inverse or generic search.
"""
from __future__ import annotations

import argparse
from functools import lru_cache
import hashlib
import json
import os
from pathlib import Path
import random
from tempfile import TemporaryDirectory

from bean.optimization.sponge_td import SpongeTD
from .rubiks3 import MOVES, SOLVED, apply, scramble, turn
from .rubiks3_legality import CORNERS, EDGES, validate_legal_cube
from .rubiks3_temperature import PIECE_TABLES
from .rubiks3_sponge import _digest, collect_states
from .rubiks3_symmetry import canonical, learn_symmetric
from .rubiks3_curriculum import edges_for, replay
from .rubiks3_value_rollout import policy_solve_value_rollout


@lru_cache(maxsize=100_000)
def piece_features(state):
    """Stable identity/configuration/distance tuples for all twenty cubies."""
    validate_legal_cube(state)
    features = []
    for group in (*CORNERS, *EDGES):
        colors, distances, kind = PIECE_TABLES[frozenset(state[i] for i in group)]
        positions = tuple(next(i for i in group if state[i] == color)
                          for color in colors)
        identity = (kind, ''.join(sorted(colors)))
        features.append((identity, positions, distances[positions]))
    features.sort(key=lambda item: item[0])
    if len(features) != 20 or len({item[0] for item in features}) != 20:
        raise AssertionError('invalid piece factorization')
    return tuple(features)


def local_reward(before, after):
    """Observed subgoal feedback, including a penalty for undoing a solved cubie."""
    if before == 0 and after == 0:
        return 0.0
    if after == 0:
        return 1.0
    if before == 0:
        return -0.2
    return 0.05 if after < before else -0.05 if after > before else -0.01


def observed_edges(states):
    """Only transitions between observed legal self-play states."""
    known = set(states)
    edges = []
    for state in sorted(known):
        if state == SOLVED:
            continue
        for action, move in enumerate(MOVES):
            nxt = turn(state, move)
            if nxt in known:
                edges.append((state, action, nxt))
    return edges


def train_pieces(learner, edges, *, epochs=3, seed=19):
    if type(epochs) is not int or epochs < 1 or not edges:
        raise ValueError('nonempty observed edges and positive epochs required')
    rng = random.Random(seed)
    order = list(edges)
    for _ in range(epochs):
        rng.shuffle(order)
        for state, action, nxt in order:
            before, after = piece_features(state), piece_features(nxt)
            for (identity, config, distance), (next_id, next_config, next_distance) in zip(before, after):
                if identity != next_id:
                    raise AssertionError('cubie identity changed under a legal turn')
                learner.learn((identity, config), action,
                              local_reward(distance, next_distance),
                              (identity, next_config), next_distance == 0)
    return {'observed_edges': len(edges), 'epochs': epochs,
            'piece_td_updates': learner.steps,
            'feedback': 'per-cubie solved subgoal and local hotter/colder',
            'reference_solver_used': False}


def policy_solve_pieces(learner, start):
    """Greedy aggregation of BEAN's learned piece Q; stop on repeated state.

    No move-count limit, no whole-cube search, and no handcrafted distance
    tie-break. If the policy has no preference, report failure honestly.
    """
    validate_legal_cube(start)
    state, route, visited = start, [], set()
    while state != SOLVED:
        if state in visited:
            return route, {'solved': False, 'failure': 'cycle'}
        visited.add(state)
        features = piece_features(state)
        q_rows = [learner.q.get(learner.key((identity, config)))
                  for identity, config, _ in features]
        if not any(row is not None for row in q_rows):
            return route, {'solved': False, 'failure': 'no_piece_values'}
        scores = [sum(row[action] for row in q_rows if row is not None) / 20.0
                  for action in range(len(MOVES))]
        if max(scores) - min(scores) < 1e-12:
            return route, {'solved': False, 'failure': 'no_learned_preference'}
        action = max(range(len(MOVES)), key=lambda i: (scores[i], -i))
        state = turn(state, MOVES[action])
        route.append(MOVES[action])
        if state in visited and state != SOLVED:
            return route, {'solved': False, 'failure': 'cycle'}
    return route, {'solved': True, 'failure': None}


def experiment(*, train_seeds=range(20), test_seeds=range(18000, 18010),
               train_lengths=(2, 3, 4, 5, 6), test_lengths=(3, 4, 5, 6, 20),
               epochs=3, output=None):
    train_seeds, test_seeds = tuple(train_seeds), tuple(test_seeds)
    if (not train_seeds or not test_seeds or
            len(set(train_seeds)) != len(train_seeds) or
            len(set(test_seeds)) != len(test_seeds) or
            set(train_seeds) & set(test_seeds)):
        raise ValueError('training and holdout seeds must be unique and disjoint')
    if not train_lengths or not test_lengths:
        raise ValueError('empty scramble lengths')
    states, episodes = collect_states(train_seeds, train_lengths)
    known = {canonical(state)[0] for state in states}
    raw_edges = observed_edges(states)
    with TemporaryDirectory(prefix='bean-cube-pieces-') as tmp:
        baseline = SpongeTD(Path(tmp) / 'baseline.db', actions=MOVES,
                            alpha=1, gamma=.9, epsilon=0, seed=19)
        candidate = SpongeTD(Path(tmp) / 'pieces.db', actions=MOVES,
                             alpha=1, gamma=.9, epsilon=0, seed=19)
        try:
            initial = learn_symmetric(baseline, states, epochs=epochs)
            trained = train_pieces(candidate, raw_edges, epochs=epochs)
            if baseline.steps > candidate.steps:
                raise AssertionError('unexpected larger baseline update budget')
            extra = candidate.steps - baseline.steps
            replay(baseline, edges_for(states), extra, seed=31)
            if baseline.steps != candidate.steps:
                raise AssertionError('unmatched SpongeTD update budgets')
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
                    base_moves, bi = policy_solve_value_rollout(baseline, state)
                    piece_moves, pi = policy_solve_pieces(candidate, state)
                    base_ok = apply(state, base_moves) == SOLVED
                    piece_ok = apply(state, piece_moves) == SOLVED
                    if base_ok != bi['solved'] or piece_ok != pi['solved']:
                        raise AssertionError('independent cube replay disagrees with policy')
                    features = piece_features(state)
                    covered = sum(candidate.key((identity, config)) in candidate.q
                                  for identity, config, _ in features)
                    cases.append({
                        'seed': seed, 'scramble_length': length,
                        'scramble_evaluator_only': recipe, 'state': state,
                        'canonical_state': key, 'piece_features_covered': covered,
                        'baseline_moves': base_moves, 'baseline_move_count': len(base_moves),
                        'baseline_solved': base_ok, 'baseline_failure': bi['failure'],
                        'candidate_moves': piece_moves, 'candidate_move_count': len(piece_moves),
                        'candidate_solved': piece_ok, 'candidate_failure': pi['failure'],
                        'candidate_better': piece_ok and not base_ok,
                        'candidate_worse': base_ok and not piece_ok,
                        'candidate_shorter': base_ok and piece_ok and len(piece_moves) < len(base_moves),
                        'optimality_proven': False})
            if frozen != (_digest(baseline.q), _digest(candidate.q)):
                raise AssertionError('evaluation mutated frozen learned Q')
            result = {
                'schema': 'bean.rubiks3.piece-subgoal.v1',
                'source_revision': os.environ.get('GITHUB_SHA', 'local_unverified'),
                'module_sha256': hashlib.sha256(Path(__file__).read_text(encoding='utf-8').encode('utf-8')).hexdigest(),
                'mechanism': 'BEAN SpongeTD per-cubie learned action values aggregated for full cube',
                'reference_solver_used': False, 'inverse_scramble_used': False,
                'not_general_solver': True, 'optimality_unproven': True,
                'train_seeds': list(train_seeds), 'test_seeds': list(test_seeds),
                'train_lengths': list(train_lengths), 'test_lengths': list(test_lengths),
                'training_episodes': episodes, 'baseline_initial_training': initial,
                'candidate_training': trained, 'matched_extra_baseline_updates': extra,
                'td_updates_per_arm': candidate.steps, 'baseline_q_sha256': frozen[0],
                'candidate_q_sha256': frozen[1], 'training_canonical_states': len(known),
                'eligible_cases': len(cases), 'excluded_count': len(excluded),
                'baseline_solved': sum(c['baseline_solved'] for c in cases),
                'candidate_solved': sum(c['candidate_solved'] for c in cases),
                'candidate_better': sum(c['candidate_better'] for c in cases),
                'candidate_worse': sum(c['candidate_worse'] for c in cases),
                'candidate_shorter': sum(c['candidate_shorter'] for c in cases),
                'twenty_turn_cases': sum(c['scramble_length'] == 20 for c in cases),
                'twenty_turn_solved': sum(c['candidate_solved'] for c in cases
                                          if c['scramble_length'] == 20),
                'excluded': excluded, 'cases': cases,
                'caveat': 'Independent cubie subgoals can conflict; this does not establish coordinated full-cube planning.'
            }
            result['sha256'] = _digest(result)
            if output is not None:
                path = Path(output)
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
            return result
        finally:
            baseline.close()
            candidate.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--test-seed-start', type=int, default=18000)
    parser.add_argument('--test-count', type=int, default=10)
    parser.add_argument('--output', default='cognitive-gauntlet-results/rubiks3-pieces-18000.json')
    args = parser.parse_args()
    if args.test_count < 1:
        parser.error('test-count must be positive')
    result = experiment(test_seeds=range(args.test_seed_start,
                                         args.test_seed_start + args.test_count),
                        output=args.output)
    print(json.dumps({k: result[k] for k in
                      ('eligible_cases', 'excluded_count', 'baseline_solved',
                       'candidate_solved', 'candidate_better', 'candidate_worse',
                       'twenty_turn_cases', 'twenty_turn_solved', 'sha256')}, indent=2))
