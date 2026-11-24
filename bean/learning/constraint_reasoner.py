"""Finite-domain reasoning with MRV, forward checking and bounded backtracking.

Original implementation of standard CSP search ideas (AIMA; OR-Tools constraint
programming). No upstream code copied, no executable expressions or dependencies.
"""
from collections import defaultdict
from operator import eq, ne, lt, le, gt, ge

_OPS = {"eq": eq, "ne": ne, "lt": lt, "le": le, "gt": gt, "ge": ge}


def solve_constraints(*, domains, constraints, node_limit=20000):
    """Return up to two solutions, distinguish unique, ambiguous, unsat, unknown."""
    if not isinstance(domains, dict) or not 1 <= len(domains) <= 32:
        raise ValueError("Expected 1..32 finite domains")
    if type(node_limit) is not int or not 1 <= node_limit <= 100000:
        raise ValueError("Invalid search budget")
    if not isinstance(constraints, list) or len(constraints) > 256:
        raise ValueError("Expected at most 256 constraints")
    values = {}
    for name, items in domains.items():
        if not isinstance(name, str) or not 1 <= len(name) <= 80:
            raise ValueError("Invalid variable name")
        if not isinstance(items, list) or not 1 <= len(items) <= 64:
            raise ValueError("Expected 1..64 domain values")
        if not all((type(v) is int and abs(v) <= 10**9) or
                   (type(v) is str and len(v) <= 80) for v in items):
            raise ValueError("Only bounded integers or strings are supported")
        if len({type(v) for v in items}) != 1 or len(set(items)) != len(items):
            raise ValueError("Domain values must be homogeneous and distinct")
        values[name] = tuple(items)
    pairs = defaultdict(list)
    for row in constraints:
        if not isinstance(row, dict) or set(row) != {"left", "op", "right"}:
            raise ValueError("Use left, op, right variable names")
        a, op, b = row["left"], row["op"], row["right"]
        if not all(isinstance(x, str) for x in (a, op, b)) or a not in values or b not in values or op not in _OPS:
            raise ValueError("Unknown variable or relation")
        if type(domains[a][0]) is not type(domains[b][0]):
            raise ValueError("Incompatible relation types")
        fn = _OPS[op]
        if a == b:
            values[a] = tuple(v for v in values[a] if fn(v, v))
        else:
            pairs[a, b].append(fn)
            pairs[b, a].append(lambda x, y, fn=fn: fn(y, x))
    neighbors = defaultdict(set)
    for a, b in pairs:
        neighbors[a].add(b)
    solutions = []
    nodes = 0
    exhausted = False

    def search(remaining, assignment):
        nonlocal nodes, exhausted
        if len(solutions) >= 2 or exhausted:
            return
        if not remaining:
            solutions.append(dict(assignment))
            return
        if any(not domain for domain in remaining.values()):
            return
        name = min(remaining, key=lambda n: (len(remaining[n]), -len(neighbors[n] & remaining.keys()), n))
        for value in remaining[name]:
            if nodes >= node_limit:
                exhausted = True
                return
            nodes += 1
            next_domains = {n: d for n, d in remaining.items() if n != name}
            for other in neighbors[name] & next_domains.keys():
                next_domains[other] = tuple(v for v in next_domains[other]
                                            if all(fn(value, v) for fn in pairs[name, other]))
            search(next_domains, {**assignment, name: value})
            if exhausted or len(solutions) >= 2:
                return

    search(values, {})
    verdict = ("ambiguous" if len(solutions) > 1 else "unknown" if exhausted else
               "unique" if solutions else "unsatisfiable")
    return {"status": "unknown" if exhausted else "success", "verdict": verdict,
            "solutions": solutions, "nodes": nodes, "budget_exhausted": exhausted,
            "independent_validation": False}
