# Brain 0.13 - Speculative Logic and Hypothesis Discipline

Brain 0.13 gives BEAN a way to reason about uncertain, theoretical, hypothetical, emotional, social, mechanical, and future possibilities without recording speculation as fact.

Core rule:

> Speculation is allowed. Pretending speculation is fact is forbidden.

## Claim types

- observation
- memory
- inference
- hypothesis
- speculation
- counterfactual
- prediction
- unknown

## Evidence levels

- observed
- strongly_supported
- supported
- weakly_supported
- speculative
- hypothetical
- unknown
- contradicted

## Action permissions

- thought_only
- may_ask_question
- may_observe
- may_recommend
- requires_supervisor_review
- forbidden_for_action

Hypotheses, speculation, counterfactuals, predictions, and unknown claims default to `forbidden_for_action`.

## Storage

Brain 0.13 creates package-local SQLite tables:

- `speculative_hypotheses`
- `speculative_evidence_links`
- `speculative_reviews`

Records are not deleted. They may be updated, superseded, resolved, contradicted, or archived.

## Integration

The reasoning context builder includes a `speculative_summary` block with open hypotheses, unresolved speculative claims, contradicted hypotheses, recently strengthened hypotheses, and counts by status.

Reasoning proposals may reference hypothesis IDs. Speculative claims do not overwrite memory or world facts.

## Safety invariants

- No speculative claim can execute action.
- No speculative claim becomes an observation.
- Counterfactuals cannot become memory facts.
- Predictions cannot become outcomes without evidence.
- Unsupported certainty is rejected for unsupported speculative claims.
- Fake sentience and fake emotion language are rejected.
- Runtime proof remains motion-disabled.

## Main files

- `bean/speculation/claim_types.py`
- `bean/speculation/hypothesis.py`
- `bean/speculation/evidence.py`
- `bean/speculation/hypothesis_store.py`
- `bean/speculation/discipline.py`
- `bean/speculation/speculative_engine.py`
- `bean/speculation/maintenance.py`
- `bean/tests/test_speculative_logic.py`
