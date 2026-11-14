"""Typed relational reasoning over BEAN's existing canonical world claims.

Hyperon/MeTTa-inspired idea: typed relation atoms with explicit inference rules.
Original BEAN Python, no Hyperon source copied or second Atomspace/database.

Only these three relations may be composed transitively: is_a, part_of,
located_in. "related_to" is deliberately non-transitive. A derived path
is a hypothesis supported by *caller-supplied* source references, never
independently authenticated world truth.
"""
from __future__ import annotations

from collections import defaultdict, deque
from hashlib import sha256
import json
import re

from ..memory.store import get_store
from ..world.claim import ClaimCategory, ClaimSource, make_claim
from ..world.model_store import ModelStore

SCHEMA = "bean.typed_relation.v1"
PREDICATES = frozenset(("is_a", "part_of", "located_in", "related_to"))
TRANSITIVE = frozenset(("is_a", "part_of", "located_in"))
_SYMBOL = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,99}\Z")


def _symbol(value, name):
    if not isinstance(value, str) or not _SYMBOL.fullmatch(value):
        raise ValueError(f"{name} must be a bounded symbolic identifier")
    return value


def _predicate(value):
    if value not in PREDICATES:
        raise ValueError("unsupported typed relation")
    return value


def _key(subject, predicate, target, polarity):
    # Canonical component hashing prevents ambiguous dotted-atom keys, e.g.
    # ("a.b", "c") versus ("a", "b.c"). The full typed tuple is stored in
    # the existing claim's JSON value and never discarded.
    terms = json.dumps([subject, predicate, target, polarity],
                       separators=(",", ":"), ensure_ascii=False)
    return "symbolic." + sha256(terms.encode("utf-8")).hexdigest()


class TypedRelations:
    """Query and revise relational atoms within BEAN's existing world model."""

    def __init__(self):
        self.store = ModelStore()

    def observe(self, *, subject, predicate, target, polarity="support",
                source_ref, evidence_refs, confidence=0.5):
        """Persist a source-labelled proposition, not an inferred fact.

        The original world_model's key-supersession logic retains prior versions.
        Explicit refutations coexist with support and block claimed certainty.
        """
        subject = _symbol(subject, "subject")
        predicate = _predicate(predicate)
        target = _symbol(target, "target")
        if subject == target:
            raise ValueError("self-loop relations must be evaluated separately")
        if polarity not in ("support", "refute"):
            raise ValueError("polarity must be support or refute")
        source_ref = _symbol(source_ref, "source_ref")
        if not isinstance(evidence_refs, (tuple, list)) or not 1 <= len(evidence_refs) <= 8:
            raise ValueError("1..8 evidence references required")
        refs = [_symbol(ref, "evidence_ref") for ref in evidence_refs]
        if len(set(refs)) != len(refs):
            raise ValueError("duplicate evidence references do not add credit")
        if type(confidence) not in (int, float) or not 0 <= confidence <= 1:
            raise ValueError("confidence must be between zero and one")
        payload = {
            "schema": SCHEMA, "subject": subject, "predicate": predicate,
            "target": target, "polarity": polarity,
            "claim_truth_verified": False,
        }
        claim = make_claim(
            _key(subject, predicate, target, polarity),
            f"{subject} {predicate} {target} ({polarity}; source-reported)",
            ClaimCategory.RELATIONAL, ClaimSource.SUPERVISOR,
            float(confidence), value=payload,
            source_ref=source_ref, evidence=refs,
        )
        self.store.save(claim)
        return {
            "status": "recorded", "claim_id": claim.claim_id,
            "relation": payload, "source_ref": source_ref,
            "source_evidence_refs": refs,
            "world_truth_verified": False,
        }

    def query(self, *, subject, predicate, target=None, max_hops=3,
              max_records=512, max_results=12):
        """Return directly supported or composed paths with evidence receipts.

        Does not treat a missing path as false. Conflicting direct source
        claims remain contested; a refuted edge cannot support any new path.
        Querying never writes learned facts, rewards, or artificial evidence.
        """
        subject = _symbol(subject, "subject")
        predicate = _predicate(predicate)
        if target is not None:
            target = _symbol(target, "target")
        if type(max_hops) is not int or not 1 <= max_hops <= 4:
            raise ValueError("max_hops must be 1..4")
        if type(max_records) is not int or not 1 <= max_records <= 2048:
            raise ValueError("max_records must be 1..2048")
        if type(max_results) is not int or not 1 <= max_results <= 20:
            raise ValueError("max_results must be 1..20")
        db = get_store()
        rows = db.fetchall(
            "SELECT id,claim_id,key,value,confidence,source_ref,evidence "
            "FROM world_claims WHERE active=1 AND category='relational' "
            "AND key LIKE 'symbolic.%' ORDER BY id LIMIT ?",
            (max_records + 1,),
        )
        base = {
            "schema": "bean.symbolic.query.v1",
            "subject": subject, "predicate": predicate, "target": target,
            "rule": "homogeneous_transitive_v1" if predicate in TRANSITIVE
                    else "direct_only_v1",
            "world_truth_verified": False,
            "source_independence_authenticated": False,
            "model_weights_changed": False,
            "actions_authorized": False,
        }
        if len(rows) > max_records:
            return {**base, "status": "incomplete_graph",
                    "results": [], "records_scanned": max_records,
                    "truncated": True}
        pairs = defaultdict(dict)
        for row in rows:
            try:
                data = json.loads(row["value"] or "null")
                refs = json.loads(row["evidence"] or "[]")
            except (TypeError, ValueError):
                continue
            if not isinstance(data, dict) or set(data) != {
                    "schema", "subject", "predicate", "target", "polarity",
                    "claim_truth_verified"
            } or data.get("schema") != SCHEMA:
                continue
            if data.get("predicate") != predicate or data.get("polarity") not in ("support", "refute"):
                continue
            src, dst, polarity = data["subject"], data["target"], data["polarity"]
            if (not isinstance(src, str) or not isinstance(dst, str)
                    or _key(src, predicate, dst, polarity) != row["key"]):
                continue
            if not isinstance(refs, list):
                refs = []
            pairs[(src, dst)][polarity] = {
                "source_row_id": row["id"], "claim_id": row["claim_id"],
                "source_ref": row["source_ref"],
                "evidence_refs": [x for x in refs if isinstance(x, str)][:8],
                "subject": src, "predicate": predicate, "target": dst,
                "confidence": row["confidence"], "polarity": polarity,
            }
        adjacency = defaultdict(list)
        for (src, dst), polarity in pairs.items():
            if "support" in polarity and "refute" not in polarity:
                adjacency[src].append(polarity["support"])
        for values in adjacency.values():
            values.sort(key=lambda r: (r["target"], r["claim_id"]))

        effective_hops = max_hops if predicate in TRANSITIVE else 1
        queue = deque([(subject, (), frozenset((subject,)))])
        paths = {}
        expansions = 0
        while queue:
            node, proof, visited = queue.popleft()
            if len(proof) >= effective_hops:
                continue
            for edge in adjacency[node]:
                expansions += 1
                if expansions > 2048:
                    return {**base, "status": "incomplete_search", "results": [],
                            "records_scanned": len(rows), "truncated": True}
                nxt = edge["target"]
                if nxt in visited:
                    continue
                new_proof = (*proof, edge)
                paths.setdefault(nxt, new_proof)
                if len(new_proof) < effective_hops:
                    queue.append((nxt, new_proof, visited | {nxt}))

        if target is not None:
            # Explicit direct refutation is not mathematical proof of negation;
            # it is evidence that contradicts or challenges the proposed path.
            refute = pairs.get((subject, target), {}).get("refute")
            proof = paths.get(target)
            if proof and refute:
                state = "contested"
            elif refute:
                state = "refuted_unverified"
            elif proof:
                state = "direct_unverified" if len(proof) == 1 else "inferred_unverified"
            else:
                state = "unknown"
            results = ([self._result(target, proof, refute, state)]
                       if (proof or refute) else [])
            return {**base, "status": state, "results": results,
                    "records_scanned": len(rows), "truncated": False}
        results = []
        for node, proof in sorted(paths.items(), key=lambda item: (len(item[1]), item[0])):
            refute = pairs.get((subject, node), {}).get("refute")
            state = ("contested" if refute else "direct_unverified"
                     if len(proof) == 1 else "inferred_unverified")
            results.append(self._result(node, proof, refute, state))
        return {
            **base, "status": "hypotheses_only" if results else "unknown",
            "results": results[:max_results], "records_scanned": len(rows),
            "truncated": len(results) > max_results,
        }

    @staticmethod
    def _result(target, proof, counterevidence, state):
        steps = list(proof or [])
        return {
            "target": target, "status": state,
            "inferred": len(steps) > 1,
            "hops": len(steps),
            "proof": steps,
            "counterevidence": counterevidence,
            "evidence_claim_ids": [step["claim_id"] for step in steps],
            "evidence_row_ids": [step["source_row_id"] for step in steps],
            "minimum_source_confidence": (
                min(step["confidence"] for step in steps) if steps else None),
            "independent_validation": False,
        }
