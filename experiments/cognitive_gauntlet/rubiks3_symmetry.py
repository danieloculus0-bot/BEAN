"""Experimental rotation-equivariant SpongeTD cube policy.

Train from BEAN's own legal self-play states and terminal rewards, NOT from
scramble inverses or reference-solver answers. Proper global cube rotations
canonicalize state/action pairs so one learned Q-value transfers to 24 physical
orientations. Inference remains a greedy learned policy with a one-step value
lookahead, not a search for an answer. Exact replay and failures are recorded.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import tempfile

from bean.optimization.sponge_td import SpongeTD
from .rubiks3 import FACES, INDEX, MOVES, NORMAL, SOLVED, STICKERS, apply, scramble, solve, turn, _spin
from .rubiks3_sponge import _digest, collect_states, learn_policy, policy_solve

MOVE_INDEX = {m: i for i, m in enumerate(MOVES)}
NORMAL_FACE = {v: f for f, v in NORMAL.items()}


def _rotations():
    identity = ((1, 0, 0), (0, 1, 0), (0, 0, 1))
    queue = [identity]
    seen = {identity}
    for basis in queue:
        for axis in range(3):
            nxt = tuple(_spin(v, axis, 1) for v in basis)
            if nxt not in seen:
                seen.add(nxt)
                queue.append(nxt)
    if len(queue) != 24:
        raise AssertionError('expected 24 proper cube rotations')
    return queue


def _rotate(v, basis):
    return tuple(sum(v[k] * basis[k][i] for k in range(3)) for i in range(3))


def _transforms():
    result = []
    for basis in _rotations():
        positions = tuple(INDEX[(_rotate(p, basis), _rotate(n, basis))]
                          for p, n in STICKERS)
        faces = {f: NORMAL_FACE[_rotate(NORMAL[f], basis)] for f in FACES}
        result.append((positions, faces))
    return tuple(result)

TRANSFORMS = _transforms()


def transform(state, rotation):
    positions, faces = TRANSFORMS[rotation]
    output = [''] * 54
    for old, new in enumerate(positions):
        output[new] = faces[state[old]]
    return ''.join(output)


def canonical(state):
    """Return lexicographically canonical 54-facelet state and move-face map."""
    if len(state) != 54 or sorted(state) != sorted(SOLVED):
        raise ValueError('invalid cube facelets')
    best = None
    best_faces = None
    for rotation, (_, faces) in enumerate(TRANSFORMS):
        candidate = transform(state, rotation)
        if best is None or candidate < best:
            best, best_faces = candidate, faces
    return best, best_faces


def learn_symmetric(learner, states, *, epochs=12, seed=19):
    """TD updates over the observed canonical transition graph only."""
    import random
    if epochs < 1:
        raise ValueError('epochs must be positive')
    known = {canonical(s)[0] for s in states}
    transitions = []
    for state in sorted(known):
        if state == SOLVED:
            continue
        for action, move in enumerate(MOVES):
            nxt = canonical(turn(state, move))[0]
            if nxt in known:
                transitions.append((state, action, nxt))
    rng = random.Random(seed)
    for _ in range(epochs):
        rng.shuffle(transitions)
        for state, action, nxt in transitions:
            learner.learn(state, action, 1.0 if nxt == SOLVED else 0.0,
                          nxt, nxt == SOLVED)
    return {'sampled_states': len(states), 'canonical_states': len(known),
            'legal_canonical_edges': len(transitions), 'epochs': epochs,
            'td_updates': learner.steps,
            'reward': '1 only on reaching SOLVED, 0 otherwise'}


def policy_solve_symmetric(learner, start):
    """Greedy learned canonical Q-values; never consumes scramble or solution."""
    canonical(start)  # validate input before any policy action
    state, path, visited = start, [], set()
    transfer_used = False
    while state != SOLVED:
        if state in visited:
            return path, {'solved': False, 'failure': 'cycle',
                          'one_step_transfer': transfer_used}
        visited.add(state)
        current, face_map = canonical(state)
        q = learner.q.get(learner.key(current))
        options = []
        for action, move in enumerate(MOVES):
            nxt = turn(state, move)
            if nxt in visited:
                continue
            if q is not None:
                mapped = face_map[move[0]] + move[1:]
                value = q[MOVE_INDEX[mapped]]
            elif nxt == SOLVED:
                value = 1.0
            else:
                successor, _ = canonical(nxt)
                values = learner.q.get(learner.key(successor))
                value = learner.gamma * max(values) if values else 0.0
            if value > 0:
                options.append((value, action, nxt))
        if not options:
            return path, {'solved': False, 'failure': 'no_positive_learned_action',
                          'one_step_transfer': transfer_used}
        _, action, nxt = max(options, key=lambda row: (row[0], -row[1]))
        transfer_used |= q is None
        path.append(MOVES[action])
        state = nxt
    return path, {'solved': True, 'failure': None,
                  'one_step_transfer': transfer_used}


def experiment(*, train_seeds=range(250), test_seeds=range(1000, 1010),
               train_lengths=(2, 3, 4, 5, 6), test_lengths=(3, 4, 5, 6, 20),
               epochs=12, output=None):
    """Frozen paired holdout, unchanged TD versus symmetry TD, with raw cases."""
    train_seeds, test_seeds = tuple(train_seeds), tuple(test_seeds)
    if set(train_seeds) & set(test_seeds):
        raise ValueError('training and holdout seeds overlap')
    states, episodes = collect_states(train_seeds, train_lengths)
    known = {canonical(s)[0] for s in states}
    with tempfile.TemporaryDirectory(prefix='bean-cube-symmetry-') as tmp:
        baseline = SpongeTD(Path(tmp)/'baseline.db', actions=MOVES,
                            alpha=1, gamma=.9, epsilon=0, seed=19)
        candidate = SpongeTD(Path(tmp)/'candidate.db', actions=MOVES,
                             alpha=1, gamma=.9, epsilon=0, seed=19)
        untrained = SpongeTD(Path(tmp)/'untrained.db', actions=MOVES,
                             alpha=1, gamma=.9, epsilon=0, seed=19)
        try:
            base_training = learn_policy(baseline, states, epochs=epochs)
            candidate_training = learn_symmetric(candidate, states, epochs=epochs)
            before = (_digest(baseline.q), _digest(candidate.q))
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
                                         'state': state, 'canonical_state': normalized, 'reason': reason})
                        continue
                    seen.add(normalized)
                    untrained_moves, untrained_info = policy_solve_symmetric(untrained, state)
                    base_moves, base_info = policy_solve(baseline, state)
                    moves, info = policy_solve_symmetric(candidate, state)
                    base_ok = apply(state, base_moves) == SOLVED
                    ok = apply(state, moves) == SOLVED
                    untrained_ok = apply(state, untrained_moves) == SOLVED
                    if (base_ok != base_info['solved'] or ok != info['solved']
                            or untrained_ok != untrained_info['solved']):
                        raise AssertionError('policy result differs from independent replay')
                    reference, ref_info = (solve(state, max_depth=6)
                                           if ok or base_ok else (None, None))
                    cases.append({'seed': seed, 'scramble_length': length,
                                  'scramble_evaluator_only': recipe, 'state': state,
                                  'canonical_state': normalized,
                                  'untrained_moves': untrained_moves,
                                  'untrained_solved': untrained_ok,
                                  'baseline_moves': base_moves, 'baseline_solved': base_ok,
                                  'baseline_failure': base_info['failure'],
                                  'candidate_moves': moves, 'candidate_solved': ok,
                                  'candidate_failure': info['failure'],
                                  'candidate_one_step_transfer': info['one_step_transfer'],
                                  'candidate_better': ok and not base_ok,
                                  'candidate_worse': base_ok and not ok,
                                  'candidate_shorter': ok and base_ok and len(moves) < len(base_moves),
                                  'reference_moves': reference,
                                  'reference_proven_optimal': (ref_info['optimal_within_depth']
                                                               if ref_info is not None else None),
                                  'candidate_matches_proven_optimum': bool(ok and reference is not None
                                      and ref_info['optimal_within_depth'] and len(moves) == len(reference))})
            after = (_digest(baseline.q), _digest(candidate.q))
            if before != after:
                raise AssertionError('frozen policies mutated during holdout')
            result = {'schema': 'bean.rubiks3.sponge-td-symmetry.v2',
                      'evidence': 'synthetic legal 3x3, frozen heldout policy comparison',
                      'mechanism': '24 global rotations share SpongeTD Q values; no solution teacher',
                      'holdout_independence_unit': 'canonical state under 24 proper cube rotations',
                      'checkout_revision': os.environ.get('GITHUB_SHA', 'local_unverified'),
                      'module_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                      'train_seeds': list(train_seeds), 'test_seeds': list(test_seeds),
                      'train_lengths': list(train_lengths), 'test_lengths': list(test_lengths),
                      'training_episodes': episodes,
                      'baseline_training': base_training,
                      'candidate_training': candidate_training,
                      'baseline_q_sha256': after[0], 'candidate_q_sha256': after[1],
                      'eligible_cases': len(cases), 'excluded_count': len(excluded),
                      'twenty_turn_cases': sum(c['scramble_length'] == 20 for c in cases),
                      'twenty_turn_solved': sum(c['candidate_solved'] for c in cases
                                                if c['scramble_length'] == 20),
                      'untrained_solved': sum(c['untrained_solved'] for c in cases),
                      'baseline_solved': sum(c['baseline_solved'] for c in cases),
                      'candidate_solved': sum(c['candidate_solved'] for c in cases),
                      'candidate_better': sum(c['candidate_better'] for c in cases),
                      'candidate_worse': sum(c['candidate_worse'] for c in cases),
                      'candidate_shorter': sum(c['candidate_shorter'] for c in cases),
                      'candidate_matches_proven_optimum': sum(
                          c['candidate_matches_proven_optimum'] for c in cases),
                      'excluded': excluded, 'cases': cases,
                      'caveat': 'Sparse tabular TD is not a general full-cube solver.'}
            result['sha256'] = _digest(result)
            if output is not None:
                path = Path(output)
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8')
            return result
        finally:
            baseline.close()
            candidate.close()
            untrained.close()


if __name__ == '__main__':
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument('--output', default='cognitive-gauntlet-results/rubiks3-symmetry.json')
    p.add_argument('--test-seed-start', type=int, default=1000)
    p.add_argument('--test-count', type=int, default=10)
    args = p.parse_args()
    if args.test_count < 1:
        p.error('test-count must be positive')
    result = experiment(test_seeds=range(args.test_seed_start,
                                         args.test_seed_start + args.test_count),
                        output=args.output)
    print(json.dumps({k: result[k] for k in
                      ('eligible_cases', 'excluded_count', 'twenty_turn_cases', 'twenty_turn_solved',
                       'untrained_solved', 'baseline_solved', 'candidate_solved', 'candidate_better',
                       'candidate_worse', 'candidate_shorter', 'sha256')}, indent=2))
