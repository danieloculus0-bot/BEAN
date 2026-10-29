"""Independent receipt replay for BEAN-native joint-cubie rescue.

This verifier never loads SpongeTD weights, calls a reference solver, or
invokes the candidate policy. It independently replays every saved legal
route and checks all aggregate success/failure and pause claims.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from .rubiks3 import MOVES, SOLVED, apply, scramble
from .rubiks3_legality import validate_legal_cube
from .rubiks3_symmetry import canonical

SCHEMA = 'bean.rubiks3.joint-rescue.v1'


def verify_receipt(path):
    record = json.loads(Path(path).read_text(encoding='utf-8'))
    if record.get('schema') != SCHEMA:
        raise ValueError('wrong receipt schema')
    claimed_digest = record.get('sha256')
    core = {k: v for k, v in record.items() if k != 'sha256'}
    raw = json.dumps(core, sort_keys=True, separators=(',', ':'),
                     allow_nan=False).encode()
    if hashlib.sha256(raw).hexdigest() != claimed_digest:
        raise ValueError('receipt digest mismatch')
    cases, excluded = record['cases'], record['excluded']
    expected = len(record['test_seeds']) * len(record['test_lengths'])
    if len(cases) + len(excluded) != expected:
        raise ValueError('lost heldout cases or exclusions')
    if len({(row['seed'], row['scramble_length'])
            for row in cases + excluded}) != expected:
        raise ValueError('duplicate or missing seed/length combination')
    scored_classes = set()
    for row in cases + excluded:
        recipe = scramble(row['seed'], row['scramble_length'])
        state = apply(SOLVED, recipe)
        if (recipe != row['scramble_evaluator_only']
                or state != row['state']
                or canonical(state)[0] != row['canonical_state']):
            raise ValueError('scramble or state provenance mismatch')
        validate_legal_cube(state)
    for row in cases:
        if row['canonical_state'] in scored_classes:
            raise ValueError('duplicate scored rotation class')
        scored_classes.add(row['canonical_state'])
        for prefix in ('initial', 'matched', 'candidate'):
            moves = row[prefix + '_moves']
            if (not isinstance(moves, list) or any(move not in MOVES for move in moves)
                    or len(moves) != row[prefix + '_move_count']):
                raise ValueError('invalid recorded moves')
            if (apply(row['state'], moves) == SOLVED) != row[prefix + '_solved']:
                raise ValueError('solved-state replay mismatch')
        if row['initial_solved'] and (
                not row['candidate_solved']
                or row['initial_moves'] != row['candidate_moves']):
            raise ValueError('successful initial route was changed')
        if (row['candidate_full_steps'] + row['candidate_joint_steps']
                != row['candidate_move_count']):
            raise ValueError('candidate action provenance mismatch')
        paused = row['candidate_paused']
        cp = row['candidate_checkpoint']
        if paused:
            if (row['candidate_solved'] or row['candidate_failure'] != 'paused_compute_budget'
                    or not isinstance(cp, dict) or cp.get('start') != row['state']
                    or cp.get('route') != row['candidate_moves']
                    or cp.get('full_q_sha256') != record['initial_q_sha256']
                    or cp.get('joint_q_sha256') != record['joint_q_sha256']
                    or cp.get('full_steps') != row['candidate_full_steps']
                    or cp.get('joint_steps') != row['candidate_joint_steps']):
                raise ValueError('invalid pause checkpoint')
        elif cp is not None:
            raise ValueError('unexpected checkpoint on terminal case')
        if row['candidate_better_than_initial'] != (
                row['candidate_solved'] and not row['initial_solved']):
            raise ValueError('initial improvement flag mismatch')
        if row['candidate_worse_than_initial'] != (
                row['initial_solved'] and not row['candidate_solved']):
            raise ValueError('initial regression flag mismatch')
        if row['candidate_better_than_matched'] != (
                row['candidate_solved'] and not row['matched_solved']):
            raise ValueError('matched improvement flag mismatch')
        if row['candidate_worse_than_matched'] != (
                row['matched_solved'] and not row['candidate_solved']):
            raise ValueError('matched regression flag mismatch')
    counts = {
        'eligible_cases': len(cases),
        'excluded_count': len(excluded),
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
    }
    for key, value in counts.items():
        if record[key] != value:
            raise ValueError('incorrect aggregate: ' + key)
    if record['candidate_total_td_updates'] != record['matched_td_updates']:
        raise ValueError('unmatched training updates')
    return {'verified': True, 'receipt_sha256': claimed_digest,
            'source_revision': record['source_revision'], **counts}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('receipts', nargs='+', type=Path)
    args = parser.parse_args()
    for receipt in args.receipts:
        print(json.dumps({'path': str(receipt), **verify_receipt(receipt)},
                         sort_keys=True))
