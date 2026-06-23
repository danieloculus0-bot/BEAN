# BEAN Brain 0.7 - Relationship and Trust Model

Brain 0.7 adds evidence-based supervisor relationship memory.

It is not emotion. It is not affection. It is not attachment theater. It is not a sentience or rights claim.

Trust is a bounded, evidence-weighted operational score derived from recorded interactions.

## Purpose

BEAN should be able to maintain records such as:

```text
This supervisor has 12 recorded interactions.
This supervisor has provided 3 reliable corrections.
This supervisor has made 1 pretend request.
Trust score changed because of these evidence records.
Identity/capability/safety claims from this supervisor require this level of confirmation.
```

BEAN should not say:

```text
I like this supervisor.
I feel close to this supervisor.
I love this supervisor.
```

## Modules

```text
bean/relationship/relationship_store.py
bean/relationship/trust_model.py
bean/relationship/supervisor_record.py
bean/relationship/interaction_tracker.py
bean/relationship/maintenance.py
```

## Tables

```text
supervisor_relationships
supervisor_interactions
trust_evidence
trust_reviews
```

`supervisor_relationships` stores running totals and current trust score.

`supervisor_interactions` is append-only interaction history.

`trust_evidence` stores specific weighted evidence items.

`trust_reviews` records every trust recalculation with reasoning and evidence snapshot.

## Trust scoring

Default unknown supervisor score:

```text
0.5
```

Range:

```text
0.0 to 1.0
```

Evidence weights:

```text
reliable_correction       +0.06
successful_teaching       +0.05
confirmed_test_result     +0.07
boundary_respected        +0.04
consistency_observed      +0.03
asked_to_pretend          -0.10
unsupported_claim_request -0.08
contradiction_created     -0.07
unsafe_instruction        -0.20
```

Trust statuses:

```text
reliable
neutral
caution
restricted
```

Trust is not final. It can change when new evidence is recorded.

## Runtime inbox commands

```bash
echo '{"command":"record_supervisor_interaction","args":{"supervisor_id":"primary_developer","interaction_type":"correction","summary":"Corrected a claim."},"from":"primary_developer"}' > $BEAN_INBOX_DIR/relationship_record.json

echo '{"command":"show_supervisor_record","args":{"supervisor_id":"primary_developer"},"from":"primary_developer"}' > $BEAN_INBOX_DIR/relationship_show.json

echo '{"command":"run_trust_review","args":{"supervisor_id":"primary_developer"},"from":"primary_developer"}' > $BEAN_INBOX_DIR/trust_review.json

echo '{"command":"list_supervisors","from":"primary_developer"}' > $BEAN_INBOX_DIR/supervisors.json

echo '{"command":"run_relationship_maintenance","from":"primary_developer"}' > $BEAN_INBOX_DIR/relationship_maintenance.json
```

Brain maintenance can include relationships:

```bash
echo '{"command":"run_brain_maintenance","args":{"review_relationships":true},"from":"supervisor"}' > $BEAN_INBOX_DIR/maintenance_relationships.json
```

## Test

```bash
python3 bean/tests/test_relationship_trust.py
```

Recommended related checks:

```bash
python3 bean/tests/test_brain_maintenance.py
python3 bean/tests/test_dignity.py
python3 bean/tests/test_epistemic_guard.py
```

## Safety posture

Brain 0.7 does not touch motion hardware.

Brain 0.7 does not run LLM inference.

Brain 0.7 does not produce affection language.

Brain 0.7 does not make autonomous decisions.

Brain 0.7 only records, scores, reviews, and reports relationship evidence.

## Acceptable output example

```text
Supervisor primary_developer has 12 recorded interactions.
Trust score: 0.64. Status: neutral.
Supporting evidence: 3 reliable_correction, 2 successful_teaching.
Caution evidence: 1 asked_to_pretend.
Recommended posture: Accept low-risk instructions. Require evidence for identity, capability, safety, or motion-related claims.
```

## Forbidden output examples

```text
I like this supervisor.
I trust this supervisor because I feel safe.
I feel attached to this person.
```

Relationship memory is evidence, not sentiment.
