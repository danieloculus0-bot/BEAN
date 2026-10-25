# Core + Bridge feedback: one learning owner, actual source checks

This integration reuses **BEAN Python Core** `NativeReasoningService` (one SHA-linked SQLite decision/feedback history), and **BEAN AI Bridge** `ezbean.learning_loop.EvidenceLearningLoop` (the existing separate versioned source-definition library). Bridge is an **evidence verifier boundary**, not a replacement memory brain or a new language model.

**Connected path:** Core chooses a measured strategy → invokes the configured model once → records the actual answer and inference receipt → Bridge assesses that answer against newly submitted source observations using a caller-supplied verifier → only two agreeing, independently named and currently checked source origins produce a Core feedback event → the same Core ledger retains a correction when its answer was wrong → the same Core retrieval path can use that correction next time.

Bridge feedback also carries an explicit `bridge_concept:` scope in the same BEAN evidence references. Task-time retrieval rejects that correction for differently named concepts, even when they share common vocabulary. This prevents a correction about one sensor from being silently reused as an alleged fact about another. General reusable procedures without a Bridge concept scope remain eligible for broader task matching.

The verifier's source checks are **host-attested**; distinct labels do not guarantee truly independent real-world organizations or facts. A self-authored answer, historical definition without *new* corroborating sources, single source, conflict, rate limit or failed verification never earns positive feedback. Bridge saves unresolved evidence too.

## Local Python use

When the external BEAN-AI-Bridge- `src` is importable:

```python
from bean.learning import NativeReasoningService, TrialCase
from bean.learning.bridge_feedback import BridgeReasoningLoop
from ezbean.learning_loop import SourceObservation

class HostVerifier:
    def check(self, concept, observation):
        # REPLACE with actual independent source-integrity logic.
        raise NotImplementedError("Supply a real source verifier before running")

with_reasoning = NativeReasoningService("bean_reasoning.sqlite3", model=your_model)
try:
    # Before this call, use evaluate_and_select(...) on development cases
    # to choose one of Core's existing contextual reasoning strategies.
    loop = BridgeReasoningLoop(
        with_reasoning, "bridge_definitions.sqlite3",
        verifier=HostVerifier())
    result = loop.attempt(
        domain="inspection", task_ref="check-12",
        query="What should this inspection show?",
        concept="inspection-12", as_of="2026-10-25T14:00:00Z",
        observations=[
            SourceObservation("source:A", "independent-A", "accepted_result"),
            SourceObservation("source:B", "independent-B", "accepted_result"),
        ])
finally:
    with_reasoning.close()
```

A host may register `register_bridge_feedback_handler(existing_inbox, loop)` to expose `reasoning_bridge_experiment` without creating a second runtime. JSON inputs are converted to strict `SourceObservation(ref,origin,value)` instances and may not supply a `verified` flag. Source verifier is provided **out of band by trusted host code**, not by untrusted JSON.

## Actual mechanism test

`PYTHONPATH=bridge-src/src python -m unittest bean.tests.test_bridge_reasoning_loop -v`

Reproduces a synthetic sensor task with a frozen deterministic model:
- Measured development selection picks Core's reflection strategy.
- First new sensor task predicts **RED**; real Bridge LAB009 two-origin verifier reports **GREEN**; Core persists negative feedback and a source-linked correction.
- A second new sensor task uses **GREEN** from retained BEAN memory with the same unchanged model.
- After a new SQLite session, two additional different hidden-evaluation-style prompts score **adaptive 2/2; cold 0/2; irrelevant-memory placebo 0/2**.
- Single origin, duplicate origin, rejected source and conflicting source attempts retain uncertainty but **cannot** create lessons or grant a feedback reward.

Those numerical scores are **synthetic integration fixtures**, not Nemotron performance, general intelligence, independent factual authentication, or evidence of a profitable trading policy. This shows that actual shared feedback can change task-time behavior while retaining provenance and leaving the reasoning provider replaceable.

CI pins the external Bridge revision and runs full Core tests on both Windows and Ubuntu. Failure receipts stay on source; no automatic market trades or unsupported external actions.
