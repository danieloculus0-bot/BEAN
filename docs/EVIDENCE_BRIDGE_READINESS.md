# Native BEAN Evidence Bridge — Verified cross-repository readiness

**Scope:** A stable Core API for independently attested host observations,
revisable evidence findings and opt-in durable evidence-review tasks. This
promotes **a narrowly verified interoperability contract**, not the research
branches' synthetic rankings or their model weights.

## Why this exists

Before this work, BEAN had useful but separate modules: Core's persistent
world model, uncertainty, EpistemicGuard, proposal-only reasoning, durable
TaskEngine; and Bridge's ERP evidence ledger, experiments and output gates.
This module allows an authorized host to invoke the same actual BEAN Core
learning path without importing a Bridge experiment or pretending its model
is an evidence source.

```
Authorized read-only host source
        |
        v
typed SourceClaim + host verifier attestation + source origin
        |
        v
EvidenceBridge.start / observe (idempotent) / finalize
        |
        +---- insufficient or contradicted -> open uncertainty / N/A
        |
        +---- two different origins agree -> audited, revisable finding
        |
        v
BEAN Core SQLite events, UncertaintyGarden, EpistemicGuard
        |
        +---- later new round can revise or overturn an earlier finding
        |
        v
Host reads bridge.current() / bridge.history() on next session
```

### Opt-in autonomy without uncontrolled actions

`EvidenceReviewAction` is an explicitly registered, named, no-argument
action for the existing durable `TaskEngine`. A trusted host's **read-only
inbox** provides a `ReviewBatch` of previously attested `SourceClaim`
records. The task engine can execute the bounded verification/revision cycle
at a declared interval; it journals attempts, treats missing or contested
evidence as **N/A**, and marks interrupted in-flight runs as
`needs_review` instead of blindly replaying them.

The host still owns the source reader, source independence checks,
verification, allowed side effects and time budget. The action cannot execute
arbitrary commands, browse the internet, move hardware, or place transactions.

## Python API (illustrative)

```python
from bean.integration import (
    BeanReasoningLayer, EvidenceBridge, EvidenceReviewAction,
    ReviewBatch, SourceClaim,
)
from bean.runtime.task_engine import TaskEngine, TaskSpec

# This file path and read-only host inbox are chosen by the host.
with BeanReasoningLayer("bean_state.sqlite") as core:
    evidence = EvidenceBridge(core)
    action = EvidenceReviewAction(evidence, host_read_only_inbox)
    engine = TaskEngine({"check_evidence": action})
    engine.configure([TaskSpec("evidence_review", "check_evidence", 3600)])
    engine.recover_interrupted()
    outcomes = engine.poll_due()  # driven by the host's runtime ticks
```

Each `ReviewBatch` names one question/round and carries at most 32 typed
claims. Every claim has an immutable record ID, source reference, declared
origin, measured/observed value, explicit verification status, distinct
verifier reference and timezone-aware timestamp. Two attestations from
**different origins** are required. Echoes do not increase origin count.

**Important:** BEAN cannot authenticate source ownership or certify an
independent check merely because a host supplied a string. The host must
implement separate evidence verification and provenance controls.

## Smoke-test evidence

The isolated Bridge branch
[`smoke/core-evidence-contract-20261010`](https://github.com/danieloculus0-bot/BEAN-AI-Bridge-/tree/smoke/core-evidence-contract-20261010)
checks this candidate Core feature on **actual** Linux and Windows runners,
alongside the pre-existing Bridge tests. The workflow checks out a Core
feature branch before promotion, so no competing branch is modified.

[Open the cross-repository native smoke workflow](https://github.com/danieloculus0-bot/BEAN-AI-Bridge-/actions/workflows/native-bean-core-bridge-contract-smoke.yml)

Assertions include:
- A verified agreement from two independent *declared* origins becomes an
  evidence-backed finding; repeated claims from one origin cannot promote.
- A second observation round **after a Core restart** revises a prior result.
- A third round of independent contradictory claims marks the latest state
  contested and withholds `bridge.current()`, while preserving all history.
- Idempotent ERP Ledger replay and idempotent Core receipts reject mutated IDs.
- Separate historical Core runs persist genuine SQLite events and epistemic
  audits; no hardware action is enabled.
- A named opt-in durable task performs scheduled checks, returns N/A when no
  data or conflicting data exists, and preserves crash-review state.

The JSON and XML artifacts in the workflow are machine-produced **synthetic
fixtures**. A green CI proves the named software requirements under test, not
general autonomy or correctness of unrelated real-world claims.

## Readiness interpretation

This closes a **specific** readiness gap: reusable Core↔Bridge evidence
continuity plus governed recurring inquiry. It does not prove BEAN's broad
ability to invent and implement novel programs unassisted. Its autonomy is
bounded, typed, locally scheduled, and host-governed.

The screenshot's **8.0 technical originality, 6.5 implementation, 4.0 general
autonomy** are subjective assessments, not calibrated acceptance tests;
do not replace them with arbitrarily higher scores. Measurable readiness
gains here are cross-platform green tests, multiple real database restarts,
a tested revision path, explicit contradiction withholding, and an
interrupted-task recovery witness.

## Remaining gates

- Real read-only ERP/browser adapter with authenticated source ownership,
  permission checks, durable receipt signatures and temporal corrections.
- Load, concurrency, database-migration, and multi-process host tests.
- Provenance-grouping beyond string equality, correlated evidence detection,
  independently calibrated uncertainty and alerting on source recovery.
- Broader behavioral transfer on blind datasets and autonomous code-change
  research with external acceptance tests.
- Controlled release, observability and failure recovery outside GitHub CI.
