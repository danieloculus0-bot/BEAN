# BEAN counsel and knowledge sufficiency policy
October 25, 2026. Implemented on BEAN Python Core integration branch.

## Purpose

Intelligence need not mean independently reinventing every answer. Before
spending provider inference or attempting to improve a reliable method, BEAN
can select an adequate existing answer, defer when the evidence is insufficient,
or explore when no supported answer is known. This is deterministic arbitration
over *host-supplied* candidate descriptions, not independent semantic expertise
verification, calibrated AGI, or automatic information retrieval.

A suitable source must be claimed current, in scope, checked, adequate for the
actual task, and at least medium-confidence. An expert must additionally be
claimed qualified. High-stakes choices require corroboration. If the host
reports contradictory evidence, BEAN defers. Equally graded same-kind candidate
answers with differing text also trigger review, though different wording is
not proof of semantic contradiction. Strong alternatives are not penalized for
being old or uncomplicated.

Source flags, confidence, qualifications, and corroboration are **unverified
host attestations**. SHA-256 proves journal continuity, not external truth.
Neither source provenance nor an expert's identity is authenticated by this
policy. Judgment records contain the reason codes and evidence references
that justify the recommendation.

## Commands and ownership

Normal Python Core startup already registers the one
`NativeReasoningService` and its inbox handlers. The new
`reasoning_judge` command calls `NativeReasoningService.judge` directly.
`reasoning_reason` also accepts an optional `candidates` list. With adequate
counsel, it returns the existing answer without model invocation; with a
defer decision, it returns no answer; with an explore decision, it continues
through the pre-existing selected-strategy reasoning path, which requires
a configured real provider and a previously measured selection. There is no
fabricated fallback or separate judgment database.

Example Python usage:

```python
from bean.learning import NativeReasoningService

bean = NativeReasoningService("bean_reasoning_lessons.sqlite3")
try:
    decision = bean.judge(
        domain="quality", task_ref="drawing-check", query="Which method?",
        candidates=[{
            "kind": "established",
            "answer": "Apply the approved inspection procedure",
            "source_ref": "qms:procedure-rev-3",
            "evidence_refs": ["host:approved-revision"],
            "adequate": True, "in_scope": True, "current": True,
            "source_checked": True, "qualified": False,
            "corroborated": True, "confidence": "high",
        }],
    )
    # decision["decision"] is "adopt"; answer is reused, not generated.
finally:
    bean.close()
```

Supported kinds: `established`, `expert`, `self`.
Supported stakes: `low`, `normal`, `high`.
Decision values: `adopt`, `defer`, `explore`.

`reasoning_judgment_feedback` stores a `supported`, `refuted`, or
`inconclusive` host-observed judgment outcome by its exact receipt ID with
evidence refs; repeat-identical feedback is idempotent. Both positive and
negative outcomes survive SQLite restart in BEAN's existing SHA journal.
These events can inform later tested calibration, but do **not** currently
automatically update source trust or model weights.

## Test

```bash
python -m unittest bean.tests.test_judgment -v
python -m unittest bean.tests.test_core_reasoning_integration -v
```

No independent expert identity or correctness evaluator is part of these
fixtures. This is useful engineering for source-aware abstention and reuse,
not proof of trustworthy open-world counsel or general intelligence.
