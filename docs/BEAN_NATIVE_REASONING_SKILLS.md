# BEAN Native Reasoning Skills

**Status:** Experimental. Built on existing [Lab026](BEAN_ADAPTIVE_LAB026.md) and its journal, strategy selector and optional render-only host interface. No behavioral changes to Core `main` or hosted @BEAN.

## The four skills

| BEAN API | Inspiration | Actual behavior |
| --- | --- | --- |
| `BEANReasoningSkills.recall` | Letta / MemGPT | Deterministic, task-token-ranked retrieval of evidence-backed lessons from the existing BEAN ExperienceBank, scoped by domain and bounded by a query limit. Not vector or neural retrieval. |
| `reflect` | Reflexion | Retains the observed error and explicitly **unverified** correction hypothesis in BEAN's hash-chained SQLite journal. Repeated identical records deduplicate. |
| `retain_skill` | Voyager | Stores reported-successful procedures, ordered steps and source receipts under domain-tagged lessons. Does not execute generated procedures or demonstrate cross-domain transfer. |
| `propose_instruction`, `select_strategy` | DSPy / GEPA | Retains candidate instructions and reuses Lab026's real paired trial selection across cold, irrelevant placebo, reflection, skill and prompt arms. It is not a full evolutionary GEPA search. |

`decide` uses `bean.learning.brain_port.brain_decision` to consult BEAN's already-stored winning strategy, then limits the returned lessons to text matching the current task. `present` delegates **only presentation** through the existing `connector_presentation_packet`. Selection stays with BEAN.

## API example

```python
from bean.learning import ExperienceBank, BEANReasoningSkills

bank = ExperienceBank("bean_lab026.sqlite")
skills = BEANReasoningSkills(bank)
try:
    skills.reflect(
        domain="drawings", task_id="development-1",
        observed="incorrect tolerance association",
        expected="correct tolerance association",
        adjustment_hypothesis="bind each tolerance to its own dimension text",
        evidence_refs=["fixture:development-1"],
    )
    # Independent evaluator must later provide paired scored rows.
    # skills.select_strategy(domain="drawings", rows=..., ...)
    # skills.decide(domain="drawings", task_ref="new-print", query="tolerance")
finally:
    bank.close()
```

## Real integration reused

- `bean.learning.experimental.ExperienceBank`: durable existing event store.
- `bean.learning.brain_port.choose_from_outcomes`: matched-outcome learning mechanism, not a new selector.
- `bean.learning.brain_port.brain_decision`: BEAN-owned decision packet.
- `bean.learning.brain_port.connector_presentation_packet`: optional render-only host contract.
- `bean.learning.bridge.audit_sources`: already tested against the real BEAN AI Bridge on Lab026's pinned checkout. This new adapter does not automatically dispatch into the Bridge or any external Axiom app.

## Verification and remaining work

```bash
python -m unittest bean.tests.test_native_reasoning_skills -v
python -m unittest bean.tests.test_adaptive_brain_port_lab026 -v
python -m pytest bean/tests -q -ra --tb=short
```

The workflow `bean-native-reasoning-skills.yml` checks Windows/Ubuntu with the pinned Bridge dependency. Cases are synthetic, and repeated tests demonstrate implementation correctness, not learned general intelligence. Real domain holdouts and direct Bridge task dispatch remain separate experiments.

**Source inspiration, no copied external framework**, no new identity, consent, or behavioral policies, no implicit downloads, LLM inference, neural weight updates or production deployment. Holdout gains are not yet proven.
