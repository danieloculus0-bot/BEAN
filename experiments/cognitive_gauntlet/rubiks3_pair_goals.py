"""BEAN-native corner/edge joint-goal SpongeTD pilot, not a full cube solver.

Learns a joint action value for each labeled corner/edge pair from legal
self-play transitions. A reward is earned only when BOTH pieces reach their
solved configurations. This tests coordination beyond independent cubie
rewards; no inverse scramble, reference route, cubejs, or generic search is
used for learning or inference. Every failed held-out case is retained.
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
from .rubiks3_legality import validate_legal_cube
from .rubiks3_pieces import piece_features, observed_edges
from .rubiks3_sponge import _digest, collect_states
from .rubiks3_symmetry import canonical, learn_symmetric
from .rubiks3_curriculum import edges_for, replay
from .rubiks3_value_rollout import policy_solve_value_rollout

SCHEMA = 'bean.rubiks3.joint-cubie-sponge.v1'


@lru_cache(maxsize=100_000)
def pair_features(state):
    """All 8x12 corner-edge pairs, with stable identities and legal configurations."""
    pieces = piece_features(state)
    corners = [p for p in pieces if p[0][0] == 'corner']
    edges = [p for p in pieces if p[0][0] == 'edge']
    if len(corners) != 8 or len(edges) != 12:
        raise AssertionError('expected eight corners and twelve edges')
    return tuple(((corner_id, edge_id), (corner_config, edge_config),
                  (corner_dist == 0, edge_dist == 0))
                 for corner_id, corner_config, corner_dist in corners
                 for edge_id, edge_config, edge_dist in edges)


def joint_reward(next_solved):
    """Reward a completed *joint* subgoal, not a lone piece."""
    return 1.0 if next_solved == (True, True) else 0.0


def train_pairs(learner, edges, *, epochs=2, seed=19):
    """Learn from the same observed full-cube edges, never solved-route labels."""
    if type(epochs) is not int or epochs < 1 or not edges:
        raise ValueError('positive epochs and nonempty legal transitions required')
    order = list(edges)
    rng = random.Random(seed)
    for _ in range(epochs):
        rng.shuffle(order)
        for state, action, nxt in order:
            before = pair_features(state)
            after = pair_features(nxt)
            for (pair_id, config, _), (next_id, next_config, solved) in zip(before, after):
                if pair_id != next_id:
                    raise AssertionError('pair identity changed under a legal turn')
                terminal = solved == (True, True)
                learner.learn((pair_id, config), action, joint_reward(solved),
                              (pair_id, next_config), terminal)
    return {'observed_edges': len(edges), 'pairs_per_transition': 96,
            'epochs': epochs, 'td_updates': learner.steps,
            'reward': '1 only when corner and edge are both solved',
            'reference_solver_used': False}


def policy_solve_pairs(learner, start, *, checkpoint=None, work_budget=128):
    """Use learned joint Q to select moves; pause with a resumable receipt.

    work_budget bounds computation *per invocation*, not solution length.
    A paused attempt is NOT a solved or a definitively failed puzzle.
    The checkpoint stores only the initial state and legal route so replay
    reconstructs visited states without trusting serialized derived values.
    """
    validate_legal_cube(start)
    if type(work_budget) is not int or work_budget < 1:
        raise ValueError('work budget must be a positive integer')
    route = []
    state, visited = start, set()
    if checkpoint is not None:
        if (not isinstance(checkpoint, dict) or checkpoint.get('start') != start
                or not isinstance(checkpoint.get('route'), list)):
            raise ValueError('invalid or mismatched checkpoint')
        for move in checkpoint['route']:
            if move not in MOVES or state in visited or state == SOLVED:
                raise ValueError('invalid checkpoint route')
            visited.add(state)
            route.append(move)
            state = turn(state, move)
    for _ in range(work_budget):
        if state == SOLVED:
            return route, {'solved': True, 'failure': None, 'paused': False,
                           'checkpoint': None}
        if state in visited:
            return route, {'solved': False, 'failure': 'cycle', 'paused': False,
                           'checkpoint': None}
        visited.add(state)
        features = pair_features(state)
        rows = [learner.q.get(learner.key((pair_id, config)))
                for pair_id, config, _ in features]
        if not any(row is not None for row in rows):
            return route, {'solved': False, 'failure': 'no_joint_values',
                           'paused': False, 'checkpoint': None}
        choices = []
        for action, move in enumerate(MOVES):
            score = sum(row[action] for row in rows if row is not None) / 96.0
            if score <= 0:
                continue
            nxt = turn(state, move)
            if nxt not in visited:
                choices.append((score, -action, move, nxt))
        if not choices:
            return route, {'solved': False,
                           'failure': 'no_positive_unvisited_joint_action',
                           'paused': False, 'checkpoint': None}
        _, _, move, state = max(choices)
        route.append(move)
    if state == SOLVED:
        return route, {'solved': True, 'failure': None, 'paused': False,
                       'checkpoint': None}
    return route, {'solved': False, 'failure': 'paused_compute_budget',
                   'paused': True, 'checkpoint': {'start': start, 'route': route}}


def experiment(*, train_seeds=range(16), test_seeds=range(22000, 22010),
               train_lengths=(2, 3, 4, 5, 6),
               test_lengths=(3, 4, 5, 6, 20), epochs=2, output=None):
    train_seeds, test_seeds = tuple(train_seeds), tuple(test_seeds)
    if (not train_seeds or not test_seeds or
            len(set(train_seeds)) != len(train_seeds) or
            len(set(test_seeds)) != len(test_seeds) or
            set(train_seeds) & set(test_seeds)):
        raise ValueError('nonempty disjoint unique train/test seeds required')
    if not train_lengths or not test_lengths or type(epochs) is not int or epochs < 1:
        raise ValueError('invalid training or evaluation configuration')
    states, episodes = collect_states(train_seeds, train_lengths)
    known = {canonical(state)[0] for state in states}
    edges = observed_edges(states)
    with TemporaryDirectory(prefix='bean-cube-pairs-') as tmp:
        baseline = SpongeTD(Path(tmp) / 'baseline.db', actions=MOVES,
                            alpha=1, gamma=.9, epsilon=0, seed=19)
        candidate = SpongeTD(Path(tmp) / 'joint.db', actions=MOVES,
                             alpha=1, gamma=.9, epsilon=0, seed=19)
        try:
            base_train = learn_symmetric(baseline, states, epochs=epochs)
            pair_train = train_pairs(candidate, edges, epochs=epochs)
            extra = candidate.steps - baseline.steps
            if extra < 0:
                raise AssertionError('baseline exceeds joint training update budget')
            replay(baseline, edges_for(states), extra, seed=31)
            if baseline.steps != candidate.steps:
                raise AssertionError('unequal SpongeTD update counts')
            frozen = (_digest(baseline.q), _digest(candidate.q))
            cases, excluded, seen = [], [], set()
            for seed in test_seeds:
                for length in test_lengths:
                    recipe = scramble(seed, length)
                    state = apply(SOLVED, recipe)
                    key = canonical(state)[0]
                    reason = ('training_rotation_overlap' if key in known else
                              'duplicate_holdout_rotation_class' if key in seen else None)
                    if reason:
                        excluded.append({'seed': seed, 'scramble_length': length,
                                         'scramble_evaluator_only': recipe,
                                         'state': state, 'canonical_state': key,
                                         'reason': reason})
                        continue
                    seen.add(key)
                    bm, bi = policy_solve_value_rollout(baseline, state)
                    cm, ci = policy_solve_pairs(candidate, state)
                    bok, cok = apply(state, bm) == SOLVED, apply(state, cm) == SOLVED
                    if bok != bi['solved'] or cok != ci['solved']:
                        raise AssertionError('independent solved-state replay disagrees')
                    covered = sum(candidate.key((pair_id, config)) in candidate.q
                                  for pair_id, config, _ in pair_features(state))
                    cases.append({
                        'seed': seed, 'scramble_length': length,
                        'scramble_evaluator_only': recipe, 'state': state,
                        'canonical_state': key, 'joint_features_covered': covered,
                        'baseline_moves': bm, 'baseline_move_count': len(bm),
                        'baseline_solved': bok, 'baseline_failure': bi['failure'],
                        'candidate_moves': cm, 'candidate_move_count': len(cm),
                        'candidate_solved': cok, 'candidate_failure': ci['failure'],
                        'candidate_paused': ci['paused'],
                        'candidate_pause_checkpoint': ci['checkpoint'],
                        'candidate_better': cok and not bok,
                        'candidate_worse': bok and not cok,
                        'candidate_shorter': bok and cok and len(cm) < len(bm),
                        'optimality_proven': False})
            if frozen != (_digest(baseline.q), _digest(candidate.q)):
                raise AssertionError('holdout modified frozen learned Q values')
            result = {
                'schema': SCHEMA,
                'source_revision': os.environ.get('GITHUB_SHA', 'local_unverified'),
                'module_sha256': hashlib.sha256(Path(__file__).read_text(encoding='utf-8').encode('utf-8')).hexdigest(),
                'mechanism': 'BEAN SpongeTD joint corner-edge goal action values',
                'reference_solver_used': False, 'inverse_scramble_used': False,
                'not_general_solver': True, 'optimality_unproven': True,
                'train_seeds': list(train_seeds), 'test_seeds': list(test_seeds),
                'train_lengths': list(train_lengths), 'test_lengths': list(test_lengths),
                'training_episodes': episodes, 'baseline_training': base_train,
                'joint_training': pair_train, 'matched_extra_baseline_updates': extra,
                'td_updates_per_arm': candidate.steps,
                'baseline_q_sha256': frozen[0], 'candidate_q_sha256': frozen[1],
                'training_canonical_states': len(known),
                'eligible_cases': len(cases), 'excluded_count': len(excluded),
                'baseline_solved': sum(c['baseline_solved'] for c in cases),
                'candidate_solved': sum(c['candidate_solved'] for c in cases),
                'candidate_paused': sum(c['candidate_paused'] for c in cases),
                'policy_work_budget_per_invocation': 128,
                'candidate_better': sum(c['candidate_better'] for c in cases),
                'candidate_worse': sum(c['candidate_worse'] for c in cases),
                'candidate_shorter': sum(c['candidate_shorter'] for c in cases),
                'twenty_turn_cases': sum(c['scramble_length'] == 20 for c in cases),
                'twenty_turn_solved': sum(c['candidate_solved'] for c in cases if c['scramble_length'] == 20),
                'excluded': excluded, 'cases': cases,
                'caveat': 'Joint two-piece goals still need not coordinate all 20 pieces; no full-cube or shortest-route guarantee.'
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
    parser.add_argument('--test-seed-start', type=int, default=22000)
    parser.add_argument('--test-count', type=int, default=10)
    parser.add_argument('--output', default='cognitive-gauntlet-results/rubiks3-pairs-22000.json')
    args = parser.parse_args()
    if args.test_count < 1:
        parser.error('test-count must be positive')
    result = experiment(test_seeds=range(args.test_seed_start,
                                         args.test_seed_start + args.test_count),
                        output=args.output)
    print(json.dumps({k: result[k] for k in
                      ('eligible_cases', 'excluded_count', 'baseline_solved',
                       'candidate_solved', 'candidate_better', 'candidate_worse',
                       'twenty_turn_cases', 'twenty_turn_solved', 'candidate_paused', 'sha256')}, indent=2))
