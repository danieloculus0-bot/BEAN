"""Learn reusable VERIFIED cube-to-goal routes from past outcomes.

Experimental case-based skill memory. Not policy-gradient, DQN, AGI or Core
deployment. Training states and later evaluation states remain explicit.
"""
from __future__ import annotations
from dataclasses import dataclass, field
import hashlib
import json
from .rubiks3 import MOVES, SOLVED, apply, turn, solve, scramble


@dataclass
class RouteMemory:
    """Mutable map of observed cube states to shortest verified remainder."""
    routes: dict[str, tuple[str, ...]] = field(default_factory=dict)
    attempted: int = 0
    accepted: int = 0

    def observe(self, start: str, actions: list[str] | tuple[str, ...]) -> int:
        """Only record a proposed skill after independent replay to SOLVED."""
        self.attempted += 1
        if apply(start, actions) != SOLVED:
            return 0
        self.accepted += 1
        pos = start
        changed = 0
        for i in range(len(actions) + 1):
            suffix = tuple(actions[i:])
            previous = self.routes.get(pos)
            if previous is None or len(suffix) < len(previous):
                self.routes[pos] = suffix
                changed += 1
            if i < len(actions):
                pos = turn(pos, actions[i])
        return changed

    def propose(self, state: str, lookahead: int = 1) -> tuple[str, ...] | None:
        """Recall a verified path or one exploratory move to a known suffix."""
        if lookahead not in (0, 1):
            raise ValueError('only one-step transfer is implemented')
        best = self.routes.get(state)
        if lookahead:
            for action in MOVES:
                tail = self.routes.get(turn(state, action))
                if tail is not None:
                    candidate = (action,) + tail
                    if best is None or len(candidate) < len(best):
                        best = candidate
        if best is not None and apply(state, best) != SOLVED:
            raise AssertionError('corrupt stored skill')
        return best


def experiment(*, train_seeds=range(8), test_seeds=range(20, 28),
               lengths=(3, 4, 5), budget_depth=2):
    train_seeds, test_seeds = tuple(train_seeds), tuple(test_seeds)
    if set(train_seeds) & set(test_seeds):
        raise ValueError('overlapping training and holdout seed')
    if budget_depth not in range(0, 9):
        raise ValueError('baseline depth must be 0..8')
    memory = RouteMemory()
    training=[]
    # Teacher demonstrations solved by the existing bounded search, not a
    # memorized inverse of the random scramble.
    for seed in train_seeds:
        for length in (3, 4):
            recipe = scramble(seed, length)
            state = apply(SOLVED, recipe)
            solution, meta = solve(state, max_depth=8)
            changed = memory.observe(state, solution) if solution is not None else 0
            training.append({'seed':seed,'length':length,'state':state,
                             'solution':solution,'solved':solution is not None,
                             'changed_routes':changed,'teacher_nodes':meta['searched']})
    # All heldout states are distinct from the original training starting
    # states; near-overlap with intermediate skill states is intentionally
    # possible and is the mechanism being measured.
    initial_states = {t['state'] for t in training}
    cases=[]
    for seed in test_seeds:
        for length in lengths:
            recipe=scramble(seed,length)
            state=apply(SOLVED,recipe)
            if state in initial_states:
                raise ValueError('holdout starting state duplicates train state')
            baseline, info = solve(state, max_depth=budget_depth)
            recalled=memory.propose(state,lookahead=1)
            selected=baseline
            selected_source='unchanged_bounded_search' if baseline is not None else 'unsolved'
            if recalled is not None and (selected is None or len(recalled)<len(selected)):
                selected=list(recalled)
                selected_source='trained_case_route'
            cases.append({'seed':seed,'scramble_length':length,'state':state,
                          'scramble_trace':recipe,'baseline':baseline,
                          'baseline_nodes':info['searched'],
                          'learned_memory_route':list(recalled) if recalled is not None else None,
                          'selected':selected,'selected_source':selected_source,
                          'baseline_solved':baseline is not None,
                          'candidate_solved':selected is not None,
                          'candidate_shorter':baseline is not None and
                          selected is not None and len(selected)<len(baseline),
                          'training_receipt_count':len(training)})
    result={'schema':'bean.rubiks3.case-memory.v1',
            'source':'seeded synthetic 3x3 experiment, BEAN gauntlet only',
            'not_a_core_integration':True,
            'training_seed_ids':list(train_seeds),'holdout_seed_ids':list(test_seeds),
            'teacher_training_depth':8,'heldout_baseline_depth':budget_depth,
            'learned_skill_count':len(memory.routes),
            'teacher_successes':memory.accepted,
            'teacher_attempts':memory.attempted,
            'baseline_solved':sum(c['baseline_solved'] for c in cases),
            'candidate_solved':sum(c['candidate_solved'] for c in cases),
            'candidate_shorter':sum(c['candidate_shorter'] for c in cases),
            'training':training,'holdout':cases,
            'caveat':'teacher demonstrations cost extra training compute; no external model or learned weights'};
    raw=json.dumps(result,sort_keys=True,separators=(',',':')).encode()
    result['sha256']=hashlib.sha256(raw).hexdigest()
    return result


if __name__=='__main__':
    import argparse
    from pathlib import Path
    p=argparse.ArgumentParser()
    p.add_argument('--output',default='cognitive-gauntlet-results/rubiks3-memory.json')
    args=p.parse_args()
    result=experiment()
    target=Path(args.output);target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:result[k] for k in
      ('learned_skill_count','baseline_solved','candidate_solved','candidate_shorter','sha256')},indent=2))
