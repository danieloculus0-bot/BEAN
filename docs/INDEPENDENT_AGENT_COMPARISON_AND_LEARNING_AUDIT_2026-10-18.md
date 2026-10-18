# BEAN Independent-Agent Comparison and Learning Audit

**Date:** 2026-10-18  
**Status:** Source-grounded design review. **No head-to-head performance comparison was run.**  
**Research owner:** Daniel Boone / BEAN  
**Primary ledger:** [BEAN machine-readable learning ledger](../research/learning_ledger.jsonl)  
**Related:** [Hypothesis Evaluation and Analysis Engine](HYPOTHESIS_EVALUATION_ANALYSIS_ENGINE_ROADMAP.md), [Lab023 causal retention](bean-causal-retention-lab023.md)

## What counts as learning

The label *learning* is too broad unless the mechanism is specified. BEAN must distinguish:

- **Memory recorded:** information or a lesson was durably saved; no behavioral improvement is implied.
- **Evidence update:** an observation changed an evidence rank, uncertainty status, or belief record; test the specific update rule.
- **Policy adaptation:** a selection policy changed and measurably improves a task criterion; this is not automatically a weight update.
- **Code/skill improvement:** an executable skill or source change passed independent tests; test transfer outside the original fixture.
- **Contextual learning:** a persistent reflection improves future model behavior without modifying neural weights; requires paired, held-out tests.
- **Weight learning:** model parameters demonstrably changed in a documented training process; require before/after model artifacts and run metadata.
- **Scientific discovery:** a falsifiable new prediction survived external empirical testing; simulation-only agreement is not proof.

**Promotion rule:** a Git commit, journal entry, high confidence, model-generated reflection or green synthetic test **alone** does not prove causal agent learning. A positive learning claim needs a baseline, treatment, same-model controls, independent held-out evaluation, documented changed mechanism, reproducibility and a placebo/no-memory ablation.

## Peer mechanism comparison (not a ranking)

| System or study | Documented useful mechanism | BEAN related capability | Unproven gap / experiment |
| --- | --- | --- | --- |
| [Letta MemFS](https://docs.letta.com/concepts/memfs/) | Git-versioned, inspectable per-agent memory filesystem and context management | BEAN SQLite evidence journal, source receipts and restart recovery; [backup gate](BEAN_BACKUP_RELEASE_GATE_2026-10-12.md) | Unified memory change histories across BEAN components; retrieval/retention quality under controlled repeated tasks |
| [OpenHands Benchmarks](https://github.com/OpenHands/benchmarks) | Version-pinned benchmark evaluation harness: SWE-bench, GAIA, Commit0 and other task families | Multiple synthetic BEAN labs and separate bridge harnesses | Comparable public task suite with identical model, budget, environment, score key and run receipts |
| [SWE-agent Trajectories](https://github.com/SWE-agent/SWE-agent/blob/main/docs/usage/trajectories.md) | Inspectable stepwise model responses, actions, observations, config and evaluation records | BEAN source-hashed evidence and research traces, but no common trajectory schema across every app | Record the complete learning-trigger-to-behavior-change chain with sensitive data redacted |
| [Reflexion (2023)](https://arxiv.org/abs/2303.11366) | Episodic verbal reflection used as context in later attempts; not neural weight retraining | [Lab023](bean-causal-retention-lab023.md) attempts retained reflections with real local models | Prove causal transfer versus cold context and equal-length irrelevant-memory placebo |
| [Voyager (2023)](https://arxiv.org/abs/2305.16291) | Store successful executable skills, refine via environmental feedback, reuse in novel settings | BEAN's proposal review, experimentation, and bounded code-improvement research | Verified skills library with cross-task reuse and rollback, not just saved reflections |
| [LangGraph Checkpoints](https://docs.langchain.com/oss/python/langgraph/checkpointers) | Checkpoint and replay workflow state for recovery, debugging and human review | BEAN durable journal, backup/restore and bounded authorization model | Test power-loss/disk-full recovery, multi-host consistency and full tool-state replay |

Sources are developer documentation or published research, not independently audited performance proofs. Differences in model choice, domains, budgets, and tools prohibit assigning an honest numerical BEAN-vs-peer rank from this review. OpenHands, SWE-agent and Letta serve partially different purposes.

## What BEAN already has: carefully scoped

1. **Persistent evidence:** [Universal Evidence Rank](UNIVERSAL_EVIDENCE_RANK.md) uses canonical source records, scores and hashes. Its confidence rank is *heuristic*, not calibrated probability; host-supplied origins are not authenticated.
2. **Ambiguity preservation:** [Dual-State Reasoning](BEAN_DUAL_STATE_REASONING.md) records conflicting hypotheses and context rather than forcing an answer.
3. **Memory reliability work:** [Backup release gate](BEAN_BACKUP_RELEASE_GATE_2026-10-12.md) documents restore drills; uncontrolled real-world power-loss and off-host disaster-recovery tests are outstanding.
4. **Existing experimental failures matter:** [Lab003 and Lab004](experimental-research-index-2026-10.md) report improvements on some synthetic metrics but regressions or alternate advantages elsewhere.
5. **Causal learning is not demonstrated:** [Lab023](bean-causal-retention-lab023.md) reports persisted reflections, but its first two real-model attempts were rate-limited or **inconclusive** due to incomplete candidates and model receipts. Do not describe the 4-vs-6 pilot as a proven learning gain.
6. **Proposed scientific engine:** [HEAE roadmap](HYPOTHESIS_EVALUATION_ANALYSIS_ENGINE_ROADMAP.md) is documentation, not a deployed autonomous physics or hypothesis evaluator.

## Prioritized holes in the logic framework

| Priority | Gap | Specific remediation | Evidence needed to close |
| --- | --- | --- | --- |
| **P0** | No uniform cross-component account of *what* was learned and *how* | Make `research/learning_ledger.jsonl` a validated, append-only-by-policy lesson registry with versions, artifact hashes and causal status | Validator, round-trip restart, mutation/forgery tests and reviewable example receipts |
| **P0** | Claimed learning conflated with storing a note or generating a patch | Separate observations, hypothesis, proposed adaptation, applied mechanism, measured outcome and causal transfer | Blind, matched baseline/treatment/placebo trial on unseen tasks |
| **P0** | Origin identifiers may be self-attested, not independently authenticated | External signatures/attestations and provenance trust levels, plus Sybil/duplicated-origin stress tests | Actual independent sources survive deliberate spoofing |
| **P1** | Retrieval can amplify stale or misleading memories | Contradiction-aware recall with supersession, provenance filtering, expiration conditions and answer abstention | Retrieval precision/recall and poisoned-memory tests with measured regression rates |
| **P1** | No common comparable open-agent benchmark suite | Version-pinned coding/logic/long-context/memory task set, same model and resource limits, published raw trajectories | Reproducible matched benchmark receipts, no fabricated leaderboard percentages |
| **P1** | Logic framework can treat heuristic ranks as ground truth | Calibration and independent error estimates; separate evidence-quality rank from probability-of-correctness | Held-out calibration plots, confidence interval coverage and error analysis |
| **P1** | Missing cause-of-change explanations and reversibility | Policy/skill/weights/prompt versions with reason-for-change, reproduction recipe and rollback pointer | Replayed pre/post behavior after restart and verified rollback |
| **P2** | Scientific and physics scenarios need disciplined modeling | Unit checks, conservation constraints, solver convergence and observation-vs-simulation type tracking | Independent physical or analytic benchmarks with error propagation and uncertainty |
| **P2** | PEMDAS preview and mnemonic recovery remain hypothetical | Five prespecified exposure windows, two isolated matched agents, original source revoked before uncued and cued questions | Total latency, held-out recall, false-memory rate and reproducible controlled logs |

## Learning receipt contract

Every retained lesson needs:
1. **Identity and provenance:** stable lesson ID, date, owner, domain, sources, code/model revisions and method of measurement.
2. **Before state:** old behavior, baseline run and known assumptions.
3. **Observation:** what was measured, failed, contradicted or discovered, including contrary evidence.
4. **Mechanism:** *exactly what changed*, e.g. prompt-memory artifact, SQLite record, source diff, selection-policy revision or model checkpoint.
5. **After state:** observed output, cost, failure modes, confidence bounds and tool context.
6. **Causal test:** matched control, same model/resources, placebo condition, held-out result and judge independence.
7. **Status:** proposed / synthetic observation / implemented engineering rule / inconclusive / independently replicated, plus rollback and next falsification test.

The current [initial ledger](../research/learning_ledger.jsonl) contains historical observations and proposals, **not autonomously generated or causally verified model learning**. Every entry explicitly records `causal_learning_demonstrated: false`. This flag must not be set true without linked baseline, treatment, held-out evaluation and mechanism artifacts.

## Peer-aligned experiments, phased

**Phase 1: Reproducibility and provenance.** Freeze source/model/tool versions, learning receipt schema and controls. Test malformed/contradictory records. Prefer structural validation and local regression tests before claiming feature success.

**Phase 2: Causal memory transfer.** Same model, same tasks, same tool access and token/cost budget; cold, relevant lesson, same-length irrelevant lesson, and source-only arms. Balance order and blind the judge. Record exact outcome shifts and abstentions.

**Phase 3: External peers.** Where practical, compare on open benchmark tasks with the same underlying LLM and compute budget. Disclose when an external agent provides different tools. Do not compare vendor-promoted scores that use different models or secret settings.

**Phase 4: Scientific transfer.** Evaluate physical constraints, dimensions, hidden ground truth, simulations and real empirical measurements separately, using the proposed HEAE framework only after implementation and testing.

**Phase 5: Retention after change.** Repeat cold/relevant/placebo comparisons after process restart, memory consolidation, conflicting lessons and longer delays. Tests should verify the learned policy is still actually consulted, not merely stored.

## Negative-result discipline

- Five short-exposure conditions are **a pilot design**, not a statistically definitive claim.
- If document readers are fixed heuristics rather than real inference agents, report **evidence recoverability surrogate** only.
- Failed, inconclusive and positive results all stay indexed. Source references are necessary but not sufficient: independently check real logs and artifacts before asserting trial results.
- Public benchmark leaks, privileged answer-key access, unequal prompts or missing model receipts invalidate causal comparisons.
- Do not publish credentials, customer/company records or private prompts in raw traces.

## Immediate operating rule

For every BEAN change said to be learned, ask:

> What was different after the observation; where is the durable changed artifact; what matched counterfactual proves that artifact helped; and what result would falsify the claim?

If any part is unknown, **call it a memory, hypothesis, engineering revision or inconclusive experiment, not a demonstrated learning improvement**.
