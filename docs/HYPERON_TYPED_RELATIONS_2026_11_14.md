# BEAN typed symbolic composition: Hyperon design adaptation

Research and code date: November 14, 2026.

## External source and licensing

- Design inspiration: [OpenCog Hyperon / MeTTa](https://github.com/trueagi-io/hyperon-experimental) (MIT license, Copyright (c) 2021 SingularityNET Foundation).
- Hyperon's graph-based, typed symbolic relationships and explicit inference motivated the design; this implementation is original BEAN Python. No Hyperon code, binaries, Python dependency, native runtime, or unverified "AGI" capability was imported.
- Existing BEAN `bean/learning/composition.py` already induces two-part rule compositions from evidence-backed examples. This module is complementary, not a replacement or new learning engine.

## Actual BEAN Core behavior

`bean/cognition/typed_relations.py` stores relation observations as `ClaimCategory.RELATIONAL` in the original `ModelStore` world_claims table, with the original supersession/version history, source reference, evidence refs, and symbolic data. No shadow Atomspace/database.

A host or existing runtime inbox can:
- `assert_symbolic_relation` with `subject`, `predicate`, `target`, `source_ref`, `evidence_refs`, optional `polarity` and source `confidence`.
- `query_symbolic_relation` with `subject`, `predicate`, optional `target`, optional `max_hops` (1..4).

Only the explicitly typed relations `is_a`, `part_of`, `located_in` can be composed transitively. `related_to` is deliberately direct-only. No mixing relation predicates or using implicit reverse edges. Paths have original claim IDs, source evidence and minimum reported confidence; nothing is written as a verified derived fact. Cycles are bounded and not inferred as self-facts. Explicit refutations prevent affected links from forming clean proofs.

A genuine BEAN event can include a structured `symbolic_query` object in its `data`. The existing `build_reasoning_context` evaluates it as a read-only inference, includes its underlying claim row IDs in the original context receipt, and adds a bounded proof excerpt to the existing Ollama prompt. Free text alone never creates relations. An invalid query is labeled invalid, not silently guessed.

World truth, source independence, neural weight updates, real-world action completion and consciousness are **not** established by these operations. Results are explicit source-linked hypotheses, not general semantics or a whole Hyperon runtime.

## Tests and limitations

Regression scenarios use neutral synthetic relations. They cover a genuinely derived 2/3-hop proof, direct-only nontransitive relations, no cross-type inference, explicit conflicting evidence, absence vs falsehood, cycles, retained revisions, restart continuity, canonical collision-free tuple identity, resource bounds, real inbox handlers, and actual local-model context injection. Paired Linux/Windows runners execute new tests plus existing world, focused-memory, evidence-revision and reasoning tests.

Further research can evaluate richer MeTTa-style pattern matching, variable unification, contradictions and independent held-out transfer with an unchanged BEAN baseline, without importing runtime dependencies unless they demonstrate measurable benefit.
