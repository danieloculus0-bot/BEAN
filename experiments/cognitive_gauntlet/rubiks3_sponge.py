"""BEAN-native 3x3 TD policy pilot, reusing mainline SpongeTD.

The teacher is the legal transition/reward environment, NOT a cube solver or
an inverse scramble. Training observes sampled states, explores every legal
transition between them, and backs up terminal rewards with SpongeTD.learn.
At evaluation, the frozen learned Q table selects moves, with at most one
model transition used to score an unseen state. No generic search, cubejs,
recipe inversion, or arbitrary maximum solution length is used by the policy.
Unreachable policy states are recorded as failures, not rescued by search.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import random
import shutil
import tempfile

from bean.optimization.sponge_td import SpongeTD
from .rubiks3 import MOVES, SOLVED, apply, scramble, solve, turn

SCHEMA = 'bean.rubiks3.sponge-td.v1'


def _digest(obj):
    return hashlib.sha256(json.dumps(obj, sort_keys=True, separators=(',', ':'),
                                     allow_nan=False).encode()).hexdigest()


def collect_states(train_seeds, lengths):
    """Discover legal states through self-play, without computing solutions."""
    states = {SOLVED}
    episodes = []
    for seed in train_seeds:
        for length in lengths:
            recipe = scramble(seed, length)
            state = SOLVED
            for move in recipe:
                state = turn(state, move)
                states.add(state)
            episodes.append({'seed': seed, 'length': length, 'start': state,
                             'exploration_moves': recipe})
    return states, episodes


def learn_policy(learner, states, *, epochs=12, seed=19):
    """Replay all observed legal transitions and reward only reaching SOLVED."""
    if epochs < 1:
        raise ValueError('epochs must be positive')
    transitions = []
    for state in sorted(states):
        if state == SOLVED:
            continue
        for action, move in enumerate(MOVES):
            nxt = turn(state, move)
            if nxt in states:
                transitions.append((state, action, nxt))
    rng = random.Random(seed)
    for _ in range(epochs):
        rng.shuffle(transitions)
        for state, action, nxt in transitions:
            learner.learn(state, action, 1.0 if nxt == SOLVED else 0.0,
                          nxt, nxt == SOLVED)
    return {'sampled_states': len(states), 'legal_sampled_edges': len(transitions),
            'epochs': epochs, 'td_updates': learner.steps,
            'reward': '1 only on transition into SOLVED, otherwise 0'}


def policy_solve(learner, start):
    """Greedy learned Q control, one-step transfer for states unseen in training.

    Stops on missing positive value or repeated state, never at a move-count
    ceiling. Does not modify learner.q or consult a reference solver.
    """
    if len(start) != 54 or sorted(start) != sorted(SOLVED):
        raise ValueError('invalid facelet colors')
    current, path, seen = start, [], set()
    transfer_used = False
    while current != SOLVED:
        if current in seen:
            return path, {'solved': False, 'failure': 'cycle',
                          'one_step_transfer': transfer_used}
        seen.add(current)
        q = learner.q.get(learner.key(current))
        options = []
        for action, move in enumerate(MOVES):
            nxt = turn(current, move)
            if nxt in seen:
                continue
            # Direct learned action values on known states. On unseen states,
            # use one legal model step and a learned successor state value.
            if q is not None:
                value = q[action]
            elif nxt == SOLVED:
                value = 1.0
            else:
                values = learner.q.get(learner.key(nxt))
                value = learner.gamma * max(values) if values else 0.0
            if value > 0:
                options.append((value, action, nxt))
        if not options:
            return path, {'solved': False, 'failure': 'no_positive_learned_action',
                          'one_step_transfer': transfer_used}
        _, action, nxt = max(options, key=lambda row: (row[0], -row[1]))
        transfer_used |= q is None
        path.append(MOVES[action])
        current = nxt
    return path, {'solved': True, 'failure': None,
                  'one_step_transfer': transfer_used}


def experiment(*, train_seeds=range(250), test_seeds=range(1000, 1010),
               train_lengths=(2, 3, 4, 5, 6), test_lengths=(3, 4, 5, 6, 20),
               epochs=12, reference_depth=6, output=None):
    train_seeds, test_seeds = tuple(train_seeds), tuple(test_seeds)
    if set(train_seeds) & set(test_seeds):
        raise ValueError('overlapping training and test seeds')
    if not test_seeds or not test_lengths:
        raise ValueError('empty holdout')
    if not 0 <= reference_depth <= 10:
        raise ValueError('invalid reference depth')
    states, episodes = collect_states(train_seeds, train_lengths)
    with tempfile.TemporaryDirectory(prefix='bean-cube-td-') as tmp:
        learner = SpongeTD(Path(tmp) / 'policy.sqlite3', actions=MOVES,
                           alpha=1.0, gamma=0.9, epsilon=0.0, seed=19)
        try:
            training = learn_policy(learner, states, epochs=epochs)
            before = _digest(learner.q)
            cases, excluded = [], []
            heldout_states = set()
            for seed in test_seeds:
                for length in test_lengths:
                    recipe = scramble(seed, length)
                    state = apply(SOLVED, recipe)
                    # Predeclared split rule: do not score states already seen
                    # during self-play, or duplicated elsewhere in holdout.
                    reason = ('training_state_overlap' if state in states else
                              'duplicate_holdout_state' if state in heldout_states else None)
                    if reason:
                        excluded.append({'seed': seed, 'scramble_length': length,
                                         'scramble_trace_evaluator_only': recipe,
                                         'state': state, 'reason': reason})
                        continue
                    heldout_states.add(state)
                    route, info = policy_solve(learner, state)
                    verified = apply(state, route) == SOLVED
                    if verified != info['solved']:
                        raise AssertionError('policy claim disagrees with independent replay')
                    reference, ref_info = solve(state, max_depth=reference_depth)
                    cases.append({'seed': seed, 'scramble_length': length,
                                  'scramble_trace_evaluator_only': recipe,
                                  'state': state, 'training_state_seen': state in states,
                                  'policy_moves': route, 'policy_move_count': len(route),
                                  'policy_solved': verified, 'failure': info['failure'],
                                  'one_step_transfer': info['one_step_transfer'],
                                  'untrained_policy_solved': state == SOLVED,
                                  'reference_search_moves': reference,
                                  'reference_move_count': len(reference) if reference is not None else None,
                                  'reference_optimal_within_depth': ref_info['optimal_within_depth'],
                                  'policy_matches_proven_optimum': bool(verified and reference is not None
                                      and ref_info['optimal_within_depth'] and len(route) == len(reference)),
                                  'reference_search_complete': ref_info['complete'],
                                  'reference_search_solved': reference is not None,
                                  'reference_search_nodes': ref_info['searched']})
            after = _digest(learner.q)
            if before != after:
                raise AssertionError('evaluation mutated frozen TD policy')
            result = {'schema': SCHEMA,
                      'evidence': 'synthetic deterministic 3x3 states, frozen policy heldout',
                      'policy': 'BEAN SpongeTD learned action-values; no solver answers at inference',
                      'reference': 'unchanged bounded rule search, NOT BEAN learned policy',
                      'not_core_integrated': True,
                      'checkout_revision': os.environ.get('GITHUB_SHA', 'local_unverified'),
                      'module_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                      'train_seeds': list(train_seeds), 'test_seeds': list(test_seeds),
                      'train_lengths': list(train_lengths), 'test_lengths': list(test_lengths),
                      'training': training, 'training_episodes': episodes,
                      'excluded': excluded, 'excluded_count': len(excluded),
                      'policy_q_sha256': after, 'reference_max_depth': reference_depth,
                      'policy_solved': sum(row['policy_solved'] for row in cases),
                      'untrained_policy_solved': sum(row['untrained_policy_solved'] for row in cases),
                      'reference_search_solved': sum(row['reference_search_solved'] for row in cases),
                      'cases': cases,
                      'caveat': 'Sparse tabular values and one-step transfer do not solve arbitrary deep scrambles.'}
            result['sha256'] = _digest(result)
            # Host-attested quality is never an independent correctness proof.
            if output is not None:
                out = Path(output)
                out.parent.mkdir(parents=True, exist_ok=True)
                learner.checkpoint(baseline=result['untrained_policy_solved'],
                                   candidate=result['policy_solved'], samples=len(cases),
                                   evaluation_sha256=result['sha256'])
                learner.close()
                shutil.copy2(Path(tmp) / 'policy.sqlite3', out.with_suffix('.sqlite3'))
                out.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
                return result
            return result
        finally:
            try:
                learner.close()
            except Exception:
                pass


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--output', default='cognitive-gauntlet-results/rubiks3-sponge-td.json')
    args = p.parse_args()
    result = experiment(output=args.output)
    print(json.dumps({k: result[k] for k in
                      ('policy_solved', 'untrained_policy_solved',
                       'reference_search_solved', 'policy_q_sha256', 'sha256')}, indent=2))
