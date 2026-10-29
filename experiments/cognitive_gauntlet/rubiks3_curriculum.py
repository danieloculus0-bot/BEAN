"""Validation-directed additional self-play for BEAN's existing cube SpongeTD.

The unchanged and expanded policies have equal TD update budgets. Only legal
transitions and terminal reward teach BEAN. Validation failures choose fresh
self-play exploration depths; held-out states never influence training.
Neither inference arm receives a solver answer or inverse scramble.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
import random
from pathlib import Path
from tempfile import TemporaryDirectory

from bean.optimization.sponge_td import SpongeTD
from .rubiks3 import MOVES, SOLVED, apply, scramble, turn
from .rubiks3_sponge import _digest, collect_states
from .rubiks3_symmetry import canonical, learn_symmetric
from .rubiks3_value_rollout import policy_solve_value_rollout


def curriculum_lengths(validation, ceiling=10):
    """The ceiling limits training exploration, never solution move count."""
    if type(ceiling) is not int or ceiling < 2:
        raise ValueError('invalid training exploration ceiling')
    return tuple(sorted({min(ceiling, c['scramble_length'] + 1)
                         for c in validation if not c['solved']}))


def edges_for(states):
    known = {canonical(s)[0] for s in states}
    edges = []
    for state in sorted(known):
        if state == SOLVED:
            continue
        for index, move in enumerate(MOVES):
            nxt = canonical(turn(state, move))[0]
            if nxt in known:
                edges.append((state, index, nxt))
    return edges


def replay(learner, edges, updates, seed=31):
    if type(updates) is not int or updates < 0 or (updates and not edges):
        raise ValueError('invalid matched TD budget')
    rng = random.Random(seed)
    for _ in range(updates):
        state, action, nxt = edges[rng.randrange(len(edges))]
        learner.learn(state, action, 1.0 if nxt == SOLVED else 0.0,
                      nxt, nxt == SOLVED)


def experiment(*, train_seeds=range(50), validation_seeds=range(600, 606),
               expansion_seeds=range(300, 325), test_seeds=range(1000, 1010),
               train_lengths=(2, 3, 4, 5, 6),
               validation_lengths=(3, 4, 5, 6, 20),
               test_lengths=(3, 4, 5, 6, 20), epochs=8,
               extra_updates=4000, output=None):
    splits = {'train': tuple(train_seeds), 'validation': tuple(validation_seeds),
              'expansion': tuple(expansion_seeds), 'test': tuple(test_seeds)}
    if (any(not s or len(set(s)) != len(s) for s in splits.values()) or
            len(set().union(*[set(s) for s in splits.values()])) !=
            sum(map(len, splits.values()))):
        raise ValueError('seed splits must be nonempty and disjoint')
    if not all((train_lengths, validation_lengths, test_lengths)):
        raise ValueError('empty length set')
    if type(epochs) is not int or epochs < 1:
        raise ValueError('epochs must be positive')
    initial, episodes = collect_states(splits['train'], train_lengths)
    initial_classes = {canonical(s)[0] for s in initial}
    with TemporaryDirectory(prefix='bean-cube-curriculum-') as tmp:
        base = SpongeTD(Path(tmp) / 'baseline.db', actions=MOVES,
                        alpha=1, gamma=.9, epsilon=0, seed=19)
        candidate = SpongeTD(Path(tmp) / 'candidate.db', actions=MOVES,
                             alpha=1, gamma=.9, epsilon=0, seed=19)
        try:
            train_receipt = learn_symmetric(base, initial, epochs=epochs)
            learn_symmetric(candidate, initial, epochs=epochs)
            if _digest(base.q) != _digest(candidate.q):
                raise AssertionError('initial TD weights differ')
            validation, val_excluded, val_seen = [], [], set()
            for seed in splits['validation']:
                for length in validation_lengths:
                    recipe = scramble(seed, length)
                    state = apply(SOLVED, recipe)
                    key = canonical(state)[0]
                    moves, info = policy_solve_value_rollout(base, state)
                    ok = apply(state, moves) == SOLVED
                    if ok != info['solved']:
                        raise AssertionError('validation replay mismatch')
                    row = {'seed': seed, 'scramble_length': length,
                           'scramble_evaluator_only': recipe, 'state': state,
                           'canonical_state': key, 'moves': moves,
                           'solved': ok, 'failure': info['failure']}
                    reason = ('training_overlap' if key in initial_classes else
                              'duplicate_validation' if key in val_seen else None)
                    if reason:
                        val_excluded.append({**row, 'reason': reason})
                    else:
                        val_seen.add(key)
                        validation.append(row)
            lengths = curriculum_lengths(validation)
            extra, extra_episodes = (collect_states(splits['expansion'], lengths)
                                     if lengths else ({SOLVED}, []))
            expanded = initial | extra
            known = {canonical(s)[0] for s in expanded}
            baseline_edges, candidate_edges = edges_for(initial), edges_for(expanded)
            replay(base, baseline_edges, extra_updates)
            replay(candidate, candidate_edges, extra_updates)
            frozen = (_digest(base.q), _digest(candidate.q))
            cases, excluded, seen = [], [], set()
            for seed in splits['test']:
                for length in test_lengths:
                    recipe = scramble(seed, length)
                    state = apply(SOLVED, recipe)
                    key = canonical(state)[0]
                    reason = ('training_overlap' if key in known else
                              'validation_overlap' if key in val_seen else
                              'duplicate_holdout' if key in seen else None)
                    if reason:
                        excluded.append({'seed': seed, 'scramble_length': length,
                                         'scramble_evaluator_only': recipe,
                                         'state': state, 'canonical_state': key,
                                         'reason': reason})
                        continue
                    seen.add(key)
                    bm, bi = policy_solve_value_rollout(base, state)
                    cm, ci = policy_solve_value_rollout(candidate, state)
                    bok, cok = apply(state, bm) == SOLVED, apply(state, cm) == SOLVED
                    if bok != bi['solved'] or cok != ci['solved']:
                        raise AssertionError('holdout replay mismatch')
                    cases.append({'seed': seed, 'scramble_length': length,
                                  'scramble_evaluator_only': recipe, 'state': state,
                                  'canonical_state': key,
                                  'baseline_moves': bm, 'baseline_solved': bok,
                                  'baseline_failure': bi['failure'],
                                  'candidate_moves': cm, 'candidate_solved': cok,
                                  'candidate_failure': ci['failure'],
                                  'candidate_better': cok and not bok,
                                  'candidate_worse': bok and not cok,
                                  'candidate_shorter': bok and cok and len(cm) < len(bm),
                                  'optimality_proven': False})
            if frozen != (_digest(base.q), _digest(candidate.q)):
                raise AssertionError('evaluation changed frozen TD weights')
            result = {'schema': 'bean.rubiks3.validation-curriculum.v1',
                      'source_revision': os.environ.get('GITHUB_SHA', 'local_unverified'),
                      'module_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                      'mechanism': 'validation-directed legal self-play, SpongeTD terminal reward',
                      'not_general_solver': True, 'optimality_unproven': True,
                      'split_seeds': {k: list(v) for k, v in splits.items()},
                      'train_lengths': list(train_lengths),
                      'validation_lengths': list(validation_lengths),
                      'test_lengths': list(test_lengths),
                      'chosen_exploration_lengths': list(lengths),
                      'initial_training': train_receipt, 'initial_episodes': episodes,
                      'extra_episodes': extra_episodes,
                      'initial_canonical_states': len(initial_classes),
                      'expanded_canonical_states': len(known),
                      'baseline_edges': len(baseline_edges),
                      'candidate_edges': len(candidate_edges),
                      'matched_extra_td_updates': extra_updates,
                      'baseline_td_steps': base.steps, 'candidate_td_steps': candidate.steps,
                      'baseline_q_sha256': frozen[0], 'candidate_q_sha256': frozen[1],
                      'validation': validation, 'validation_excluded': val_excluded,
                      'cases': cases, 'excluded': excluded,
                      'eligible_cases': len(cases), 'excluded_count': len(excluded),
                      'baseline_solved': sum(c['baseline_solved'] for c in cases),
                      'candidate_solved': sum(c['candidate_solved'] for c in cases),
                      'candidate_better': sum(c['candidate_better'] for c in cases),
                      'candidate_worse': sum(c['candidate_worse'] for c in cases),
                      'twenty_turn_cases': sum(c['scramble_length'] == 20 for c in cases),
                      'twenty_turn_solved': sum(c['candidate_solved'] for c in cases
                                                if c['scramble_length'] == 20),
                      'caveat': 'Equal TD updates do not equalize experience diversity or collection cost.'}
            result['sha256'] = _digest(result)
            if output is not None:
                path = Path(output)
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
            return result
        finally:
            base.close()
            candidate.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output',
                        default='cognitive-gauntlet-results/rubiks3-curriculum.json')
    args = parser.parse_args()
    report = experiment(output=args.output)
    print(json.dumps({key: report[key] for key in
                      ('eligible_cases', 'excluded_count', 'chosen_exploration_lengths',
                       'baseline_solved', 'candidate_solved', 'candidate_better',
                       'candidate_worse', 'twenty_turn_cases', 'twenty_turn_solved',
                       'sha256')}, indent=2))
