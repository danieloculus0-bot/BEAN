"""BEAN-native learned joint-goal rescue of an unchanged full-state policy.

The unchanged full-state SpongeTD policy acts first. Only when its learned
values provide no positive action may a separate BEAN-learned joint-cubie
policy propose a legal move. This is an algorithm-inspired BEAN-only test,
not a generic cube solver, external solver, inverse scramble or AGI claim.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory

from bean.optimization.sponge_td import SpongeTD
from .rubiks3 import MOVES, SOLVED, apply, scramble, turn
from .rubiks3_legality import validate_legal_cube
from .rubiks3_pair_goals import pair_features, train_pairs
from .rubiks3_pieces import observed_edges
from .rubiks3_sponge import _digest, collect_states
from .rubiks3_symmetry import canonical, learn_symmetric
from .rubiks3_curriculum import edges_for, replay
from .rubiks3_value_rollout import (
    _known_action, _value, policy_solve_value_rollout,
)

SCHEMA = 'bean.rubiks3.joint-rescue.v1'


def policy_solve_joint_rescue(full, joint, start, *, checkpoint=None, work_budget=128):
    """Resume frozen BEAN policy inference in bounded compute slices.

    No total solution-move limit exists. A paused checkpoint binds the start,
    complete legal route, and BOTH Q digests. Full-state action choice exactly
    matches the unchanged value-rollout controller until it would stop.
    """
    validate_legal_cube(start)
    if type(work_budget) is not int or work_budget < 1:
        raise ValueError('positive integer work budget required')
    full_hash, joint_hash = _digest(full.q), _digest(joint.q)
    route, visited, state = [], set(), start
    full_steps = joint_steps = 0
    if checkpoint is not None:
        if (not isinstance(checkpoint, dict)
                or checkpoint.get('start') != start
                or checkpoint.get('full_q_sha256') != full_hash
                or checkpoint.get('joint_q_sha256') != joint_hash
                or not isinstance(checkpoint.get('route'), list)):
            raise ValueError('stale or malformed policy checkpoint')
        for move in checkpoint['route']:
            if move not in MOVES or state in visited or state == SOLVED:
                raise ValueError('invalid checkpoint route')
            visited.add(state)
            route.append(move)
            state = turn(state, move)
        full_steps = checkpoint.get('full_steps')
        joint_steps = checkpoint.get('joint_steps')
        if (type(full_steps) is not int or full_steps < 0
                or type(joint_steps) is not int or joint_steps < 0
                or full_steps + joint_steps != len(route)):
            raise ValueError('invalid checkpoint action counts')

    def finish(solved, failure=None, paused=False):
        next_checkpoint = ({
            'start': start, 'route': list(route),
            'full_q_sha256': full_hash, 'joint_q_sha256': joint_hash,
            'full_steps': full_steps, 'joint_steps': joint_steps,
        } if paused else None)
        return route, {'solved': solved, 'failure': failure, 'paused': paused,
                       'checkpoint': next_checkpoint,
                       'full_steps': full_steps, 'joint_steps': joint_steps}

    for _ in range(work_budget):
        if state == SOLVED:
            return finish(True)
        if state in visited:
            return finish(False, 'cycle')
        visited.add(state)
        choices = []
        for action, move in enumerate(MOVES):
            nxt = turn(state, move)
            if nxt in visited:
                continue
            direct = _known_action(full, state, move)
            backed = (1.0 if nxt == SOLVED else
                      full.gamma * _value(full, nxt, 1, visited))
            score = max(direct, backed)
            if score > 0:
                choices.append((score, -action, move, nxt))
        if choices:
            _, _, move, state = max(choices)
            full_steps += 1
            route.append(move)
            continue

        # BEAN's separately trained joint-cubie Q is a rescue policy only.
        features = pair_features(state)
        rows = [joint.q.get(joint.key((pair_id, config)))
                for pair_id, config, _ in features]
        if not any(row is not None for row in rows):
            return finish(False, 'no_joint_values_after_full_stall')
        rescue = []
        for action, move in enumerate(MOVES):
            nxt = turn(state, move)
            if nxt in visited:
                continue
            score = sum(row[action] for row in rows if row is not None) / 96.0
            if score > 0:
                rescue.append((score, -action, move, nxt))
        if not rescue:
            return finish(False, 'no_positive_joint_rescue')
        _, _, move, state = max(rescue)
        joint_steps += 1
        route.append(move)
    if state == SOLVED:
        return finish(True)
    return finish(False, 'paused_compute_budget', True)


def experiment(*, train_seeds=range(16), test_seeds=range(26000, 26010),
               train_lengths=(2, 3, 4, 5, 6),
               test_lengths=(3, 4, 5, 6, 20), epochs=2, output=None,
               work_budget=24):
    train_seeds, test_seeds = tuple(train_seeds), tuple(test_seeds)
    if (not train_seeds or not test_seeds
            or len(set(train_seeds)) != len(train_seeds)
            or len(set(test_seeds)) != len(test_seeds)
            or set(train_seeds) & set(test_seeds)):
        raise ValueError('training and holdout seeds must be nonempty, unique, disjoint')
    if not train_lengths or not test_lengths or type(epochs) is not int or epochs < 1:
        raise ValueError('invalid training configuration')
    states, episodes = collect_states(train_seeds, train_lengths)
    known = {canonical(s)[0] for s in states}
    edges = observed_edges(states)
    with TemporaryDirectory(prefix='bean-cube-joint-rescue-') as tmp:
        initial = SpongeTD(Path(tmp) / 'initial.db', actions=MOVES,
                           alpha=1, gamma=.9, epsilon=0, seed=19)
        matched = SpongeTD(Path(tmp) / 'matched.db', actions=MOVES,
                           alpha=1, gamma=.9, epsilon=0, seed=19)
        joint = SpongeTD(Path(tmp) / 'joint.db', actions=MOVES,
                         alpha=1, gamma=.9, epsilon=0, seed=19)
        try:
            full_training = learn_symmetric(initial, states, epochs=epochs)
            learn_symmetric(matched, states, epochs=epochs)
            if _digest(initial.q) != _digest(matched.q):
                raise AssertionError('different initial full-state Q tables')
            joint_training = train_pairs(joint, edges, epochs=epochs)
            replay(matched, edges_for(states), joint.steps, seed=31)
            if matched.steps != initial.steps + joint.steps:
                raise AssertionError('unequal matched training update budgets')
            frozen = (_digest(initial.q), _digest(matched.q), _digest(joint.q))
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
                    bm, bi = policy_solve_value_rollout(initial, state)
                    mm, mi = policy_solve_value_rollout(matched, state)
                    cm, ci = policy_solve_joint_rescue(
                        initial, joint, state, work_budget=work_budget)
                    bok, mok, cok = (apply(state, moves) == SOLVED
                                      for moves in (bm, mm, cm))
                    if (bok != bi['solved'] or mok != mi['solved']
                            or cok != ci['solved']):
                        raise AssertionError('independent replay disagrees with policy')
                    if bok and (not cok or cm != bm):
                        raise AssertionError('joint rescue changed a successful initial policy')
                    cases.append({
                        'seed': seed, 'scramble_length': length,
                        'scramble_evaluator_only': recipe, 'state': state,
                        'canonical_state': key,
                        'initial_moves': bm, 'initial_move_count': len(bm),
                        'initial_solved': bok, 'initial_failure': bi['failure'],
                        'matched_moves': mm, 'matched_move_count': len(mm),
                        'matched_solved': mok, 'matched_failure': mi['failure'],
                        'candidate_moves': cm, 'candidate_move_count': len(cm),
                        'candidate_solved': cok, 'candidate_failure': ci['failure'],
                        'candidate_paused': ci['paused'],
                        'candidate_checkpoint': ci['checkpoint'],
                        'candidate_full_steps': ci['full_steps'],
                        'candidate_joint_steps': ci['joint_steps'],
                        'candidate_better_than_initial': cok and not bok,
                        'candidate_worse_than_initial': bok and not cok,
                        'candidate_better_than_matched': cok and not mok,
                        'candidate_worse_than_matched': mok and not cok,
                        'optimality_proven': False,
                    })
            if frozen != (_digest(initial.q), _digest(matched.q), _digest(joint.q)):
                raise AssertionError('evaluation mutated frozen BEAN Q tables')
            result = {
                'schema': SCHEMA,
                'source_revision': os.environ.get('GITHUB_SHA', 'local_unverified'),
                'module_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                'mechanism': 'unchanged BEAN full-state policy with joint-Q rescue only on stall',
                'reference_solver_used': False, 'inverse_scramble_used': False,
                'not_general_solver': True, 'optimality_unproven': True,
                'train_seeds': list(train_seeds), 'test_seeds': list(test_seeds),
                'train_lengths': list(train_lengths), 'test_lengths': list(test_lengths),
                'training_episodes': episodes, 'full_training': full_training,
                'joint_training': joint_training,
                'initial_td_updates': initial.steps,
                'candidate_total_td_updates': initial.steps + joint.steps,
                'matched_td_updates': matched.steps,
                'training_canonical_states': len(known),
                'initial_q_sha256': frozen[0], 'matched_q_sha256': frozen[1],
                'joint_q_sha256': frozen[2],
                'eligible_cases': len(cases), 'excluded_count': len(excluded),
                'initial_solved': sum(c['initial_solved'] for c in cases),
                'matched_solved': sum(c['matched_solved'] for c in cases),
                'candidate_solved': sum(c['candidate_solved'] for c in cases),
                'candidate_paused': sum(c['candidate_paused'] for c in cases),
                'candidate_joint_actions': sum(c['candidate_joint_steps'] for c in cases),
                'candidate_better_than_initial': sum(c['candidate_better_than_initial'] for c in cases),
                'candidate_worse_than_initial': sum(c['candidate_worse_than_initial'] for c in cases),
                'candidate_better_than_matched': sum(c['candidate_better_than_matched'] for c in cases),
                'candidate_worse_than_matched': sum(c['candidate_worse_than_matched'] for c in cases),
                'twenty_turn_cases': sum(c['scramble_length'] == 20 for c in cases),
                'twenty_turn_solved': sum(c['candidate_solved'] for c in cases
                                          if c['scramble_length'] == 20),
                'work_budget_per_invocation': work_budget,
                'excluded': excluded, 'cases': cases,
                'caveat': 'Rescue can pause; frozen joint Q is not a learned full-cube solver.'
            }
            result['sha256'] = _digest(result)
            if output is not None:
                path = Path(output)
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
            return result
        finally:
            initial.close()
            matched.close()
            joint.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--test-seed-start', type=int, default=26000)
    parser.add_argument('--test-count', type=int, default=10)
    parser.add_argument('--work-budget', type=int, default=24)
    parser.add_argument('--output', default='cognitive-gauntlet-results/rubiks3-rescue-26000.json')
    args = parser.parse_args()
    if args.test_count < 1:
        parser.error('test-count must be positive')
    result = experiment(test_seeds=range(args.test_seed_start,
                                         args.test_seed_start + args.test_count),
                        output=args.output, work_budget=args.work_budget)
    print(json.dumps({k: result[k] for k in
                      ('eligible_cases', 'excluded_count', 'initial_solved',
                       'matched_solved', 'candidate_solved', 'candidate_paused',
                       'candidate_joint_actions', 'twenty_turn_cases',
                       'twenty_turn_solved', 'sha256')}, indent=2))
