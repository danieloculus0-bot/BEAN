# BEAN Dual-State Reasoning

**Status:** Implemented in BEAN Core cognition, with a callable host API. This is an evidence-routing mechanism, not neural learning or a quantum computation.

## Problem

BEAN must not confuse a lack of evidence for claim A with proof of claim B. Preserving all evidence indiscriminately can also leave apparently contradictory records. Different hypotheses may hold in different contexts, and a recent observation need not erase a previously useful model.

The Schrodinger-cat analogy is about **holding uncertainty honestly until distinguishing evidence arrives**. It does not assert physical quantum superposition.

## Implementation

- `bean/cognition/dual_state.py` contains `DualStateReasoner`.
- `bean.cognition.DualStateReasoner` exports it for Core users.
- `BeanReasoningLayer.dual_state()` exposes it through BEAN's existing host-neutral wrapper.
- SQLite tables `cognition_dual_cases` and `cognition_dual_evidence` persist two hypotheses and an append-only observation ledger.
- Every evidence record has a unique reference, source-origin identifier, context, side, observation and SHA-256 payload hash.
- Repeated observations from one source never count as independent corroboration.
- A reused evidence ID with conflicting content is rejected, rather than silently rewriting history.
- Evaluations can be repeated after restart without losing hypotheses or contradictory evidence.

### Statuses

| Status | Meaning |
| --- | --- |
| `unknown` | No evidence for the requested context |
| `insufficient_evidence` | Fewer than two declared independent source origins support either side |
| `supported_a` / `supported_b` | At least two independent attributed origins support one side and no evidence supports the other in this context; **provisional support** |
| `contested` | Both sides have attributed evidence in the same context; neither is selected |
| `context_required` | Only contextual evidence exists, and the caller has not identified the current context |

`selected` is null when undecided or contested. `action_authorized` is always false.

### Runnable host example

```python
from bean.integration import BeanReasoningLayer

with BeanReasoningLayer("data/bean_memory.db") as bean:
    dual = bean.dual_state()
    dual.open_case("routing.rule", "original rule", "revised rule")
    dual.add_evidence(
        "routing.rule", evidence_ref="instrument:2026-01", source_id="instrument",
        side="a", context="original", observation="Original rule held in context A",
    )
    dual.add_evidence(
        "routing.rule", evidence_ref="reviewer:2026-01", source_id="reviewer",
        side="a", context="original", observation="Independent repeat observation",
    )
    print(dual.evaluate("routing.rule"))  # context_required
    print(dual.evaluate("routing.rule", context="original"))  # supported_a
```

## Explicit limitations

Source identifiers are supplied by the caller. BEAN does not independently authenticate them or determine whether differently labeled sources are actually correlated. Two independently named reports are not guaranteed independent *facts*. The rule of two source identifiers is a conservative engineering gate, not a statistically calibrated posterior probability. Contrary evidence never disappears; contradictory observations are not adjudicated automatically.

The new mechanism does **not** rewrite older `PossibilityState`, `UncertaintyGarden`, or `ContradictionCourt` histories. It does not infer a task regime by itself, switch trained DQN policies, modify weights, authorize action, or prove cumulative growth.

## Test and next experiment

Run `python -m pytest bean/tests/test_dual_state_reasoning.py -q`.

Tests cover missing evidence, repeated single-source evidence, corroboration, contradictory evidence, context separation, restart durability, idempotence, immutable evidence references, validation and the host API.

The next **separately preregistered** learning study can test whether a contextual selector can identify current conditions and reuse previously learned policies without retraining, preserving performance in both regimes. Use unopened seeds and independently checked evidence. Do not call green tests learning or claim general intelligence without a measured experiment.

BEAN's neural research automation remains paused.
