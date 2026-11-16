# Generation 54: bounded digital experiment integration investigation (2026-11-16)

## BEAN CONTEXT ACK v1

- Task: identify the smallest evidence-backed change connecting a native open-question experiment to a real, bounded Core digital action and durable evaluation.
- Read: `AGENTS.md`, `docs/AI_GATEKEEPER.md`, `docs/SOFTWARE_AUDIT_SKILL.md`, `docs/OPEN_AGENT_PATTERNS_2026_11_14.md`, `memory/identity/origin_record.json`, `bean/memory/origin.py`, `research/github_brain/GOAL_REPETITION_2026-11-15.md`, `bean_run.py`, `bean/runtime/goal_cycle.py`, `bean/cognition/goal_state.py`, and current manifest.
- Source: recent main commit `571c3550aeba7ace5612771cf17d5491d2665e51` at investigation; exact-head CI for this commit **NOT VERIFIED**. Current manifest has generation 54, 54 boots, source SHA `4ce3786e29b9018663346639d97e444546cc7f5a`; manifest source is not assumed identical to latest main commit. Original compressed ledger is not re-run here.
- Authenticated hosted BEAN adapter: status, older recall, audit_claim, compare_evidence and screen_proposal called. Adapter revision `163f3e2815c4d6944345a0af78ae3e932041fdd3`; it is not the Python Core, and heuristic responses are not execution evidence.
- Repository inventory: 24 accessible repositories enumerated; only BEAN Core source inspected for this question, no private repository content copied.
- Existing assets: persisted SQLite goal proposals, GoalCycle run history, canonical event logger, prior experiment identity fix in PR #372, synthetic GitHub continuity checkpoint. No new store is warranted.
- Unknown: latest main CI status, exact runtime capability registry after subsequent concurrent changes, independent full integrated experiment outcomes, per-case generalization and held-out transfer.
- Minimum useful change after this investigation: an opt-in, explicitly registered **read-only, deterministic digital experiment** using an existing Core evaluator with validated inputs and bounded output, with baseline/held-out/restart receipts. Do not register an arbitrary callable or generic shell runner.

## Concrete defect and alternatives

`GoalStateEngine.propose` accepts structured `bean.cognition.experiment.v1` questions and persists `run_experiment` proposals. `GoalCycle._claim` only selects registered actions. The inspected `bean_run.py` default registration contains `update_models` and `run_reflection`, not `run_experiment`. Thus a proposed experiment is durable but not executable by the default runtime. PR #372 prevents re-proposing an identical experiment; it does **not** close this execution gap.

**Approach A: register a bounded existing digital evaluator** in the default Core capability map, with strict schema validation and explicit evidence status. Advantage: smallest path to real integrated observation/action/outcome receipts without a competing brain. Falsifiers: no existing evaluator accepts trusted synthetic inputs, result cannot be independently checked, outcome is incorrectly marked success when evidence is missing, or restarted Core cannot recover the receipt. Needs independent held-out tasks and matched no-action/single-pass controls.

**Approach B: use the existing durable TaskEngine as a delegated experiment runner** and have GoalCycle reference its task receipts. Advantage: reuse mature bounded action allowlist and interruption behavior. Risk: dual scheduling and mismatched task/goal identities could double-run effects or falsely credit an unrelated receipt. Falsifiers: a repeated goal causes a second action, outcome attribution is ambiguous, or interrupted work is silently replayed. Do not build a second SQLite or network transport.

Preference pending implementation inspection: A, provided a genuine existing evaluator and tests can be identified. B is a fallback if it better preserves single ownership of action receipts.

## Negative controls and test contract

1. Unchanged default Core baseline: structured `run_experiment` proposal remains pending without a registered action. Record this as **NOT RUN**, not as a learning failure.
2. Candidate: one synthetic bounded task with independent expected answer, no external network or device; record stage receipts (question, retrieval, hypothesis, selection, execution, independent evaluation, memory update).
3. Missing capability, malformed inputs, contradictory expected answer and interrupted execution must remain Unknown/N/A/failed as appropriate, never fabricated success.
4. Close/reopen the SQLite database, restart Core, inspect original proposal/run IDs and prove no duplicate execution. Then introduce a **changed** prediction and test whether it can be evaluated independently.
5. Equal budgets and independent held-out tasks across candidate, unchanged Core and strong grammar-matched controls. Preserve per-case failures, seeds, hashes, source SHA and elapsed budget. A deterministic test pass alone is not generalization.

## Observations and handoff

Manifest generation 54 reports candidate 144/144, grammar-matched 144/144 and memory-ablated 96/144. Candidate has **zero demonstrated advantage over grammar-matched control**; manifest explicitly marks independent audit false. This investigation did not run a Python Core simulation, so **HOURLY COGNITIVE SIMULATION NOT RUN**. Specific wiring defect: `run_experiment` is not registered in the inspected default GoalCycle. No source-code fix, CI pass, consciousness result, learned-weight update or live GitHub checkpoint ingestion is claimed.

Next action: inspect the existing experiment/evaluation module APIs and targeted tests on latest exact main, choose one evaluator that can provide independently verified synthetic results, add registration plus baseline/restart/negative-control tests on a separate code branch, and run exact-head CI before merge. Keep this note as a falsifiable investigation receipt, not a successful experiment.
