# BEAN Universal Evidence Rank v1

A shared **evidence-quality** engine, not an oracle or a calibrated probability of truth. It works with the existing BEAN Core SQLite database without a model, exchange account, ERP API, or internet connection. It cannot trade, move, change code, or grant host execution authority.

## One scoring contract, many domains

An integrating application supplies `domain`, `topic`, `value`, `origin`, `source_ref`, `observed_at`, and optional host-attested verification and measured outcomes. The same API handles manufacturing process observations, software test results, AIscend strategies, weather forecast verification, or memory source claims.

1. Validate source provenance. Multiple copies from one claimed origin count as **one origin**, regardless of volume. A host-provided `verified` field asserts independent verification but BEAN cannot authenticate the issuer by itself.
2. Score observations **before** persisting. Each receipt includes the original intake score, canonical source payload, and hash-chain link. Replayed identical IDs do not duplicate evidence.
3. Recompute rankings with new evidence. Independent attestation, separately referenced measured outcomes, age, and contradictions influence the ranking. Old receipts remain unchanged; corrected hypotheses require new evidence.
4. Report `insufficient`, `attested`, or `contested`. Conflicting verified sources remain visibly contested. Missing evidence returns an empty list, not an invented zero or false confirmation.
5. Treat the 0–99 score as **a ranking heuristic, not a percent probability of truth or guaranteed outcome**. Higher-ranked entries warrant attention; they do not automatically win promotion, trades, decisions, or changes.

## Host integration

```python
from bean.integration.reasoning_layer import BeanReasoningLayer
from bean.evaluation.evidence_rank import Evidence

with BeanReasoningLayer("bean_memory.db") as core:
    ledger = core.evidence_ranker()
    receipt = ledger.observe(Evidence(
        evidence_id="inspection-001", domain="manufacturing",
        topic="first_article", value="pass",
        origin="inspector_1", source_ref="FAI:001",
        observed_at="2026-10-11T12:00:00Z",
        verified=False,
    ))
    print(receipt["intake_score"], receipt["hash"])
    print(ledger.rank("manufacturing", "first_article"))
```

A single unattested source remains `insufficient`. For separately observed tests use `outcome="pass"` or `"fail"` and an independent `outcome_ref` on a host-attested observation. Do not label an LLM response or copied website article as independent empirical verification.

### Evidence Bridge integration

`EvidenceBridge.observe(...)` now uses this ranker **before** filing a bridge source record, in one SQLite transaction. This preserves the legacy bridge's own stricter source-consensus logic. Review rank receipts via `core.evidence_ranker().rank("external", claim_key)`. Existing older bridge evidence records are not retroactively fabricated or given invented scores.

### What this does NOT prove

- Inspired by PageRank's *idea* of reusable ranking, but **not Google's actual PageRank link-graph algorithm**.
- Hash chains expose partial tampering, not wholesale forgery by an attacker who controls the database.
- `verified` and `origin` are host attestations, not cryptographic proof of an independent source; coordinated misinformation can still poison scores.
- This is not a learned model. Weights are transparent baseline heuristics, pending independent calibration against known outcomes.
- Native adapters for every BEAN subsystem and applications beyond Core's evidence bridge still require integration and their own held-out performance trials.
- These tests prove ranking behavior and persistence; they **do not prove** improved live trading profits or general intelligence.

Run `python -m pytest bean/tests/test_evidence_rank.py -q` to verify ranked hashes, contradiction behavior, cross-domain use, historical no-peeking, and BEAN Core persistence.
