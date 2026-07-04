# Brain 0.13 - Hypothesis Discipline

Purpose: allow BEAN to reason with uncertain possibilities without treating them as facts.

## What it does

- Stores uncertain claims as hypothesis records.
- Labels claim type and evidence level.
- Assigns confidence and action permission.
- Keeps review records.
- Provides a speculative summary for reasoning context.

## Claim categories

```text
observation
memory
inference
hypothesis
speculation
counterfactual
prediction
unknown
```

## Evidence levels

```text
observed
strongly_supported
supported
weakly_supported
speculative
hypothetical
unknown
contradicted
```

## Safety rule

Speculation is allowed as thought. It is not allowed to become fact or action without evidence and review.

## Main modules

```text
bean/speculation/claim_types.py
bean/speculation/hypothesis.py
bean/speculation/hypothesis_store.py
bean/speculation/discipline.py
bean/speculation/speculative_engine.py
```

## Test

```bash
python3 bean/tests/test_speculative_logic.py
```
