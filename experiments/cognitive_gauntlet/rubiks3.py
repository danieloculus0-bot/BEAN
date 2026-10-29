"""Reproducible 3x3 Rubik's Cube bounded optimal-search probe (18 HTM moves).

Rule-only combinatorial search, not an LLM or learned-policy cube solver.
The solver receives only 54 visible facelets, NEVER the scramble recipe.
"""
from __future__ import annotations
from collections import deque
import hashlib
import json
import random

FACES = 'UDFBRL'
NORMAL = {'U':(0,1,0),'D':(0,-1,0),'F':(0,0,1),
          'B':(0,0,-1),'R':(1,0,0),'L':(-1,0,0)}
RIGHT = {'U':(1,0,0),'D':(1,0,0),'F':(1,0,0),
         'B':(-1,0,0),'R':(0,0,-1),'L':(0,0,1)}
DOWN = {'U':(0,0,1),'D':(0,0,-1),'F':(0,-1,0),
        'B':(0,-1,0),'R':(0,-1,0),'L':(0,0,1)}
SOLVED = ''.join(face * 9 for face in FACES)
MOVES = tuple(f + s for f in FACES for s in ('', "'", '2'))


def _add(*vs):
    return tuple(sum(v[i] for v in vs) for i in range(3))


def _scale(v, k):
    return tuple(k * c for c in v)


def _spin(v, axis, sign):
    x, y, z = v
    if axis == 0:
        return (x, -sign*z, sign*y)
    if axis == 1:
        return (sign*z, y, -sign*x)
    return (-sign*y, sign*x, z)


STICKERS = [(_add(NORMAL[f], _scale(RIGHT[f], col-1), _scale(DOWN[f], row-1)), NORMAL[f])
            for f in FACES for row in range(3) for col in range(3)]
INDEX = {v:i for i,v in enumerate(STICKERS)}
assert len(INDEX) == 54


def _quarter(face):
    norm = NORMAL[face]
    axis = next(i for i, v in enumerate(norm) if v)
    sign = -norm[axis]  # clockwise as viewed from outside face
    old_to_new = []
    for pos, outward in STICKERS:
        if pos[axis] == norm[axis]:
            pos, outward = _spin(pos, axis, sign), _spin(outward, axis, sign)
        old_to_new.append(INDEX[(pos, outward)])
    return tuple(old_to_new)


def _compose(a, b):
    return tuple(b[i] for i in a)


PERM = {}
for _face in FACES:
    _one = _quarter(_face)
    PERM[_face] = _one
    PERM[_face+'2'] = _compose(_one, _one)
    PERM[_face+"'"] = _compose(PERM[_face+'2'], _one)


def turn(state, move):
    if len(state) != 54 or move not in PERM:
        raise ValueError('invalid facelet state or move')
    result = [''] * 54
    for old, new in enumerate(PERM[move]):
        result[new] = state[old]
    return ''.join(result)


def apply(state, moves):
    for move in moves:
        state = turn(state, move)
    return state


def invert(moves):
    return [m if m.endswith('2') else (m[:-1] if m.endswith("'") else m+"'") for m in reversed(moves)]


def scramble(seed, length):
    if length < 0 or length > 100:
        raise ValueError('scramble length out of range')
    rng = random.Random(seed)
    out = []
    for _ in range(length):
        valid = [m for m in MOVES if not out or m[0] != out[-1][0]]
        out.append(rng.choice(valid))
    return out


def _bfs(start, depth, cap):
    visited = {start: ()}
    frontier = [start]
    for _ in range(depth):
        new_frontier = []
        for state in frontier:
            path = visited[state]
            for m in MOVES:
                if path and path[-1][0] == m[0]:
                    continue
                nxt = turn(state, m)
                if nxt not in visited:
                    if len(visited) >= cap:
                        return visited, False
                    visited[nxt] = path + (m,)
                    new_frontier.append(nxt)
        frontier = new_frontier
    return visited, True


def solve(state, max_depth=8, max_states=200_000):
    """Return (moves or None, metadata). Optimal only when full search completes."""
    if len(state) != 54 or sorted(state) != sorted(SOLVED):
        raise ValueError('expected 54 legal-color facelets')
    if max_depth < 0 or max_depth > 10 or max_states < 19:
        raise ValueError('unsupported search budget')
    if state == SOLVED:
        return [], {'searched': 1, 'complete': True, 'optimal_within_depth': True}
    from_start, ok1 = _bfs(state, max_depth//2, max_states)
    from_goal, ok2 = _bfs(SOLVED, max_depth-max_depth//2, max_states)
    complete = ok1 and ok2
    common = from_start.keys() & from_goal.keys()
    if common:
        meet = min(common, key=lambda s: (len(from_start[s])+len(from_goal[s]), s))
        result = list(from_start[meet]) + invert(from_goal[meet])
        if apply(state, result) != SOLVED:
            raise AssertionError('search path does not solve cube')
        return result, {'searched':len(from_start)+len(from_goal), 'complete':complete,
                        'optimal_within_depth':complete}
    return None, {'searched':len(from_start)+len(from_goal), 'complete':complete,
                  'optimal_within_depth':False}


def run_cases(seeds=range(20), lengths=(3, 4, 5, 6, 8, 9, 20), max_depth=8):
    cases=[]
    for seed in seeds:
        for length in lengths:
            recipe=scramble(seed, length)
            state=apply(SOLVED,recipe)
            answer, meta=solve(state,max_depth=max_depth)
            row={'seed':seed,'scramble_length':length,'scramble':recipe,
                 'state':state,'solution':answer,'solution_length':None if answer is None else len(answer),
                 'solved':answer is not None,'shorter_than_recipe':answer is not None and len(answer)<length,
                 'nodes':meta['searched'],'search_complete':meta['complete'],
                 'optimal_within_depth':meta['optimal_within_depth']}
            cases.append(row)
    core={'schema':'bean.rubiks3.bounded-search.v1',
          'evidence_type':'deterministic synthetic puzzle experiment',
          'agent':'rule-based bidirectional breadth-first search (NOT trained BEAN cognition)',
          'moves':'18 face turns, half-turn metric; search bound inclusive',
          'scramble_trace':'visible only to task generator and external recipe-length comparator',
          'max_depth':max_depth,'seeds':list(seeds),'cases':cases}
    raw=json.dumps(core,sort_keys=True,separators=(',',':')).encode()
    core['sha256']=hashlib.sha256(raw).hexdigest()
    return core


if __name__=='__main__':
    import argparse
    from pathlib import Path
    p=argparse.ArgumentParser()
    p.add_argument('--output',default='cognitive-gauntlet-results/rubiks3-cases.json')
    p.add_argument('--seeds',type=int,default=8)
    args=p.parse_args()
    result=run_cases(range(args.seeds))
    target=Path(args.output)
    target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'receipt':str(target),'digest':result['sha256'],
                      'cases':len(result['cases']),
                      'solved':sum(c['solved'] for c in result['cases']),
                      'shorter_than_recipe':sum(c['shorter_than_recipe'] for c in result['cases']),
                      'failed':sum(not c['solved'] for c in result['cases'])},indent=2))
