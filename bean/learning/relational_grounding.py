"""Native evidence-linked relational inference.

Original implementation inspired by MeTTa symbolic matching and Omega's
provenance-grounded reasoning. No external engine or copied source.
"""


def _match(term, observed, bindings):
    if term.startswith('?'):
        if term in bindings:
            return bindings[term] == observed
        bindings[term] = observed
        return True
    return term == observed


def infer_relations(*, facts, patterns, conclusion):
    """Join observed triples, instantiate a conclusion and retain evidence IDs.

    Each fact is [subject, predicate, object, evidence_id]; each pattern and
    conclusion is a triple of constants or ?variables. No inferred fact is
    silently written to long-term memory or interpreted as a physical action.
    """
    def validate(row, size):
        if not isinstance(row, list) or len(row) != size or any(
                not isinstance(x, str) or not x or len(x) > 160 for x in row):
            raise ValueError('invalid relation')
    if not isinstance(facts, list) or len(facts) > 128:
        raise ValueError('expected up to 128 facts')
    if not isinstance(patterns, list) or not 1 <= len(patterns) <= 4:
        raise ValueError('expected one to four patterns')
    for fact in facts:
        validate(fact, 4)
        if any(x.startswith('?') for x in fact[:3]):
            raise ValueError('observations must be concrete')
    for pattern in patterns:
        validate(pattern, 3)
    validate(conclusion, 3)
    variables = {term for pattern in patterns for term in pattern if term.startswith('?')}
    if any(term.startswith('?') and term not in variables for term in conclusion):
        raise ValueError('unbound conclusion variable')
    states = [({}, ())]
    for pattern in patterns:
        next_states = []
        for bindings, evidence in states:
            for fact in facts:
                candidate = bindings.copy()
                if all(_match(p, f, candidate) for p, f in zip(pattern, fact[:3])):
                    next_states.append((candidate, evidence + (fact[3],)))
                    if len(next_states) > 4096:
                        raise ValueError('relation search budget exhausted')
        states = next_states
        if not states:
            break
    results = {}
    for bindings, evidence in states:
        triple = tuple(bindings.get(term, term) for term in conclusion)
        proof = tuple(sorted(set(evidence)))
        results.setdefault(triple, set()).add(proof)
    return {'status': 'success' if results else 'unknown',
            'inferences': [{'relation': list(triple), 'evidence_sets': [list(p) for p in sorted(proofs)]}
                           for triple, proofs in sorted(results.items())],
            'count': len(results), 'scope': 'supplied facts and rule only'}
