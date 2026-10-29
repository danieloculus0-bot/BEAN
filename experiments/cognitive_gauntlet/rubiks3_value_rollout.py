"""Two-transition learned-value transfer for BEAN's existing SpongeTD cube policy.

No cubejs, inverse scramble, reference search, or solution demonstrations enter
inference. This is shallow model-backed value evaluation over frozen BEAN
SpongeTD Q-values, NOT a general 3x3 solver or a new learned-weight update.
The two-transition value horizon is not a solution-move limit. A failed route
remains a failure; neither the benchmark nor inference substitutes a solver.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory

from bean.optimization.sponge_td import SpongeTD
from .rubiks3 import MOVES, SOLVED, apply, scramble, solve, turn
from .rubiks3_legality import validate_legal_cube
from .rubiks3_sponge import _digest, collect_states
from .rubiks3_symmetry import MOVE_INDEX, canonical, learn_symmetric, policy_solve_symmetric


def _known_action(learner, state, move):
    normalized, faces = canonical(state)
    values = learner.q.get(learner.key(normalized))
    if values is None:
        return 0.0
    return values[MOVE_INDEX[faces[move[0]] + move[1:]]]


def _value(learner, state, remaining, forbidden):
    """Use actual learned Q values as the leaf; no goal-search fallback."""
    if state == SOLVED:
        return 1.0
    if state in forbidden:
        return 0.0
    normalized, _ = canonical(state)
    values = learner.q.get(learner.key(normalized))
    best = max(values) if values is not None else 0.0
    if remaining:
        for move in MOVES:
            nxt = turn(state, move)
            if nxt in forbidden:
                continue
            candidate = (1.0 if nxt == SOLVED else
                         learner.gamma * _value(learner, nxt, remaining - 1,
                                                forbidden | {state}))
            if candidate > best:
                best = candidate
    return best


def policy_solve_value_rollout(learner, start, *, backup_depth=1):
    """Choose moves from frozen learned values and short legal model backups.

    backup_depth=0 is one-step successor value transfer; backup_depth=1
    additionally evaluates one transition beyond each successor. Neither
    setting caps the number of moves BEAN may output to reach SOLVED.
    """
    if type(backup_depth) is not int or backup_depth not in (0, 1):
        raise ValueError('supported learned-value backup depth is 0 or 1')
    validate_legal_cube(start)
    state, path, visited = start, [], set()
    while state != SOLVED:
        if state in visited:
            return path, {'solved': False, 'failure': 'cycle'}
        visited.add(state)
        choices = []
        for action, move in enumerate(MOVES):
            nxt = turn(state, move)
            if nxt in visited:
                continue
            direct = _known_action(learner, state, move)
            backed = (1.0 if nxt == SOLVED else
                      learner.gamma * _value(learner, nxt, backup_depth, visited))
            score = max(direct, backed)
            if score > 0:
                choices.append((score, -action, move, nxt))
        if not choices:
            return path, {'solved': False, 'failure': 'no_positive_learned_value'}
        _, _, move, state = max(choices)
        path.append(move)
    return path, {'solved': True, 'failure': None}


def experiment(*, train_seeds=range(250), test_seeds=range(1000, 1010),
               train_lengths=(2, 3, 4, 5, 6), test_lengths=(3, 4, 5, 6, 20),
               epochs=12, output=None):
    """Matched frozen learned-Q comparison; no test data enters training."""
    train_seeds, test_seeds = tuple(train_seeds), tuple(test_seeds)
    if set(train_seeds) & set(test_seeds):
        raise ValueError('training and holdout seeds overlap')
    if not test_seeds or not test_lengths:
        raise ValueError('empty holdout')
    states, episodes = collect_states(train_seeds, train_lengths)
    known = {canonical(state)[0] for state in states}
    with TemporaryDirectory(prefix='bean-cube-value-') as tmp:
        learner = SpongeTD(Path(tmp) / 'policy.sqlite3', actions=MOVES,
                           alpha=1, gamma=.9, epsilon=0, seed=19)
        try:
            training = learn_symmetric(learner, states, epochs=epochs)
            frozen = _digest(learner.q)
            cases, excluded, seen = [], [], set()
            for seed in test_seeds:
                for length in test_lengths:
                    recipe = scramble(seed, length)
                    state = apply(SOLVED, recipe)
                    normalized, _ = canonical(state)
                    reason = ('training_symmetry_overlap' if normalized in known else
                              'duplicate_holdout_symmetry_class' if normalized in seen else None)
                    if reason:
                        excluded.append({'seed': seed, 'scramble_length': length,
                                         'scramble_evaluator_only': recipe,
                                         'state': state, 'canonical_state': normalized,
                                         'reason': reason})
                        continue
                    seen.add(normalized)
                    baseline, binfo = policy_solve_symmetric(learner, state)
                    candidate, cinfo = policy_solve_value_rollout(learner, state)
                    bok = apply(state, baseline) == SOLVED
                    cok = apply(state, candidate) == SOLVED
                    if bok != binfo['solved'] or cok != cinfo['solved']:
                        raise AssertionError('independent replay disagrees with policy')
                    reference, refinfo = (solve(state, max_depth=6)
                                          if bok or cok else (None, None))
                    cases.append({
                        'seed': seed, 'scramble_length': length,
                        'scramble_evaluator_only': recipe, 'state': state,
                        'canonical_state': normalized,
                        'baseline_moves': baseline, 'baseline_solved': bok,
                        'baseline_failure': binfo['failure'],
                        'candidate_moves': candidate, 'candidate_solved': cok,
                        'candidate_failure': cinfo['failure'],
                        'candidate_better': cok and not bok,
                        'candidate_worse': bok and not cok,
                        'candidate_shorter': bok and cok and len(candidate) < len(baseline),
                        'reference_moves': reference,
                        'reference_optimal_proven': (refinfo['optimal_within_depth']
                                                     if refinfo is not None else None),
                        'candidate_matches_proven_optimum': bool(cok and reference is not None
                            and refinfo['optimal_within_depth']
                            and len(candidate) == len(reference))
                    })
            if frozen != _digest(learner.q):
                raise AssertionError('evaluation mutated frozen learned weights')
            result = {
                'schema': 'bean.rubiks3.learned-value-rollout.v1',
                'evidence': 'seeded synthetic heldout, frozen BEAN SpongeTD Q values',
                'mechanism': 'two-transition legal model backup to frozen learned values',
                'not_a_general_solver': True,
                'not_a_new_weight_update': True,
                'holdout_unit': '24-rotation canonical cube state',
                'source_revision': os.environ.get('GITHUB_SHA', 'local_unverified'),
                'module_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                'training_q_sha256': frozen,
                'train_seeds': list(train_seeds), 'test_seeds': list(test_seeds),
                'train_lengths': list(train_lengths), 'test_lengths': list(test_lengths),
                'training': training, 'training_episodes': episodes,
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
                'caveat': 'Only local value transfer; deep full-cube generalization is unproven.'
            }
            result['sha256'] = _digest(result)
            if output is not None:
                path = Path(output)
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
            return result
        finally:
            learner.close()


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--output', default='cognitive-gauntlet-results/rubiks3-value-rollout.json')
    p.add_argument('--test-seed-start', type=int, default=1000)
    p.add_argument('--test-count', type=int, default=10)
    args = p.parse_args()
    if args.test_count < 1:
        p.error('test-count must be positive')
    result = experiment(test_seeds=range(args.test_seed_start,
                                         args.test_seed_start + args.test_count),
                        output=args.output)
    print(json.dumps({k: result[k] for k in
                      ('eligible_cases', 'excluded_count', 'baseline_solved',
                       'candidate_solved', 'candidate_better', 'candidate_worse',
                       'twenty_turn_cases', 'twenty_turn_solved', 'sha256')}, indent=2))
