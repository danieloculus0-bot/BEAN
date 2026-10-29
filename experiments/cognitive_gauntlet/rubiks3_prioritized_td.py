"""Prioritized Bellman-residual replay for BEAN's native 3x3 SpongeTD learner.

The candidate and unchanged random-replay baseline start with identical learned
Q tables, use the SAME observed legal transition graph, and receive the SAME
number of TD updates. Only replay ordering differs. The priority signal is
computed from BEAN's own current Q values, terminal reward and legal transitions.
No cube solver, inverse scramble, reference route or holdout label teaches it.

This is an experimental learning-order comparison, not a general cube solver.
"""
from __future__ import annotations

import argparse
import hashlib
import heapq
import json
import os
import random
from pathlib import Path
from tempfile import TemporaryDirectory

from bean.optimization.sponge_td import SpongeTD
from .rubiks3 import MOVES, SOLVED, apply, scramble
from .rubiks3_sponge import _digest, collect_states
from .rubiks3_symmetry import canonical, learn_symmetric
from .rubiks3_curriculum import edges_for, replay
from .rubiks3_value_rollout import policy_solve_value_rollout


def residual(learner, edge):
    """Absolute Bellman error, without creating unseen Q-table entries."""
    state, action, nxt = edge
    values = learner.q.get(learner.key(state))
    current = values[action] if values is not None else 0.0
    next_values = learner.q.get(learner.key(nxt))
    future = 0.0 if nxt == SOLVED else max(next_values) if next_values else 0.0
    target = (1.0 if nxt == SOLVED else 0.0) + learner.gamma * future
    return abs(target - current)


def prioritized_replay(learner, edges, updates, *, seed=31, tolerance=1e-12):
    """Back up surprising legal transitions, then fill the matched TD budget.

    Predecessors are reprioritized when a state's best Q value changes.
    No route to SOLVED is supplied. If Bellman residuals vanish, remaining
    budgeted updates are ordinary seeded replay, explicitly counted as filler.
    """
    if type(updates) is not int or updates < 0 or (updates and not edges):
        raise ValueError('invalid TD update budget')
    if not (0 < tolerance < 1):
        raise ValueError('invalid residual tolerance')
    parents = {}
    for i, (state, action, nxt) in enumerate(edges):
        parents.setdefault(nxt, []).append(i)
    versions = [0] * len(edges)
    heap = []

    def schedule(i):
        versions[i] += 1
        priority = residual(learner, edges[i])
        if priority > tolerance:
            heapq.heappush(heap, (-priority, i, versions[i]))

    for i in range(len(edges)):
        schedule(i)
    useful = 0
    while heap and useful < updates:
        _, i, version = heapq.heappop(heap)
        if version != versions[i] or residual(learner, edges[i]) <= tolerance:
            continue
        state, action, nxt = edges[i]
        old = learner.q.get(learner.key(state))
        old_best = max(old) if old is not None else 0.0
        learner.learn(state, action, 1.0 if nxt == SOLVED else 0.0,
                      nxt, nxt == SOLVED)
        useful += 1
        # For fractional learning rates a single backup leaves a nonzero
        # Bellman residual. Requeue the updated edge until it converges or
        # the matched update budget is exhausted. Alpha=1 stays unchanged.
        schedule(i)
        new_best = max(learner.q[learner.key(state)])
        if abs(new_best - old_best) > tolerance:
            for parent in parents.get(state, ()):
                schedule(parent)
    filler = updates - useful
    rng = random.Random(seed)
    for _ in range(filler):
        state, action, nxt = edges[rng.randrange(len(edges))]
        learner.learn(state, action, 1.0 if nxt == SOLVED else 0.0,
                      nxt, nxt == SOLVED)
    return {'prioritized_updates': useful, 'matched_budget_filler_updates': filler,
            'total_updates': updates, 'observed_edges': len(edges),
            'priority': 'absolute Bellman residual, terminal reward only'}


def experiment(*, train_seeds=range(50), test_seeds=range(7000, 7010),
               train_lengths=(2, 3, 4, 5, 6),
               test_lengths=(3, 4, 5, 6, 20),
               epochs=8, extra_updates=4000, output=None):
    train_seeds, test_seeds = tuple(train_seeds), tuple(test_seeds)
    if (not train_seeds or not test_seeds or
            len(set(train_seeds)) != len(train_seeds) or
            len(set(test_seeds)) != len(test_seeds) or
            set(train_seeds) & set(test_seeds)):
        raise ValueError('training and holdout seeds must be disjoint and unique')
    if not train_lengths or not test_lengths or type(epochs) is not int or epochs < 1:
        raise ValueError('invalid experiment configuration')
    if type(extra_updates) is not int or extra_updates < 0:
        raise ValueError('invalid update count')

    states, episodes = collect_states(train_seeds, train_lengths)
    known = {canonical(state)[0] for state in states}
    edges = edges_for(states)
    with TemporaryDirectory(prefix='bean-cube-priority-') as tmp:
        baseline = SpongeTD(Path(tmp) / 'baseline.db', actions=MOVES,
                            alpha=1, gamma=.9, epsilon=0, seed=19)
        candidate = SpongeTD(Path(tmp) / 'candidate.db', actions=MOVES,
                             alpha=1, gamma=.9, epsilon=0, seed=19)
        try:
            training = learn_symmetric(baseline, states, epochs=epochs)
            learn_symmetric(candidate, states, epochs=epochs)
            initial = _digest(baseline.q)
            if initial != _digest(candidate.q):
                raise AssertionError('paired learners did not start identically')
            replay(baseline, edges, extra_updates, seed=31)
            priority = prioritized_replay(candidate, edges, extra_updates, seed=31)
            if baseline.steps != candidate.steps:
                raise AssertionError('unequal TD update counts')
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
                    bm, bi = policy_solve_value_rollout(baseline, state)
                    cm, ci = policy_solve_value_rollout(candidate, state)
                    bok, cok = apply(state, bm) == SOLVED, apply(state, cm) == SOLVED
                    if bok != bi['solved'] or cok != ci['solved']:
                        raise AssertionError('independent replay disagrees with policy')
                    cases.append({'seed': seed, 'scramble_length': length,
                                  'scramble_evaluator_only': recipe, 'state': state,
                                  'canonical_state': key,
                                  'baseline_moves': bm, 'baseline_move_count': len(bm),
                                  'baseline_solved': bok, 'baseline_failure': bi['failure'],
                                  'candidate_moves': cm, 'candidate_move_count': len(cm),
                                  'candidate_solved': cok, 'candidate_failure': ci['failure'],
                                  'candidate_better': cok and not bok,
                                  'candidate_worse': bok and not cok,
                                  'candidate_shorter': bok and cok and len(cm) < len(bm),
                                  'optimality_proven': False})
            if frozen != (_digest(baseline.q), _digest(candidate.q)):
                raise AssertionError('holdout mutated frozen learned Q values')
            result = {
                'schema': 'bean.rubiks3.prioritized-td.v1',
                'source_revision': os.environ.get('GITHUB_SHA', 'local_unverified'),
                'module_sha256': hashlib.sha256(
                    Path(__file__).read_text(encoding='utf-8').encode('utf-8')).hexdigest(),
                'mechanism': 'BEAN SpongeTD Bellman-residual replay of observed legal edges',
                'reference_solver_used': False, 'inverse_scramble_used': False,
                'training_state_source': 'legal self-play, no solution demonstrations',
                'policy': 'frozen BEAN Q values with identical two-transition value controller',
                'not_general_solver': True, 'optimality_unproven': True,
                'train_seeds': list(train_seeds), 'test_seeds': list(test_seeds),
                'train_lengths': list(train_lengths), 'test_lengths': list(test_lengths),
                'initial_training': training, 'training_episodes': episodes,
                'initial_q_sha256': initial,
                'observed_canonical_states': len(known),
                'observed_edges': len(edges), 'extra_td_updates_per_arm': extra_updates,
                'baseline_td_steps': baseline.steps, 'candidate_td_steps': candidate.steps,
                'priority_training': priority,
                'baseline_q_sha256': frozen[0], 'candidate_q_sha256': frozen[1],
                'eligible_cases': len(cases), 'excluded_count': len(excluded),
                'baseline_solved': sum(c['baseline_solved'] for c in cases),
                'candidate_solved': sum(c['candidate_solved'] for c in cases),
                'candidate_better': sum(c['candidate_better'] for c in cases),
                'candidate_worse': sum(c['candidate_worse'] for c in cases),
                'candidate_shorter': sum(c['candidate_shorter'] for c in cases),
                'twenty_turn_cases': sum(c['scramble_length'] == 20 for c in cases),
                'twenty_turn_solved': sum(c['candidate_solved'] for c in cases
                                          if c['scramble_length'] == 20),
                'cases': cases, 'excluded': excluded,
                'caveat': 'A learned backup schedule is not a general 3x3 solving policy; no shortest-route proof.'
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
    parser.add_argument('--test-seed-start', type=int, default=7000)
    parser.add_argument('--test-count', type=int, default=10)
    parser.add_argument('--epochs', type=int, default=8)
    parser.add_argument('--extra-updates', type=int, default=4000)
    parser.add_argument('--output', default='cognitive-gauntlet-results/rubiks3-prioritized-td.json')
    args = parser.parse_args()
    if args.test_count < 1:
        parser.error('test-count must be positive')
    report = experiment(test_seeds=range(args.test_seed_start,
                                         args.test_seed_start + args.test_count),
                        epochs=args.epochs, extra_updates=args.extra_updates,
                        output=args.output)
    print(json.dumps({k: report[k] for k in
                      ('eligible_cases', 'excluded_count', 'baseline_solved',
                       'candidate_solved', 'candidate_better', 'candidate_worse',
                       'twenty_turn_cases', 'twenty_turn_solved', 'sha256')}, indent=2))
