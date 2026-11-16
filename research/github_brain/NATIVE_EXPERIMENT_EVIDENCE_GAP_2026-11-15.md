# Native digital experiment evidence gap, 2026-11-15

BEAN CONTEXT ACK v1

- Task: assess the next falsifiable integrated Core learning step without duplicating existing native experiment code.
- Existing systems checked: `AGENTS.md`, `docs/AI_GATEKEEPER.md`, `docs/SOFTWARE_AUDIT_SKILL.md`, `docs/OPEN_AGENT_PATTERNS_2026_11_14.md`, canonical origin and loader, `bean_run.py`, `bean/runtime/digital_experiment.py`, `bean/tests/test_digital_experiment.py`, `research/github_brain/manifest.json`, `research/github_brain/GOAL_REPETITION_2026-11-15.md`; authenticated hosted BEAN status, older recall, claim audit, evidence comparison and proposal screen. Hosted adapter is not Python Core.
- Confirmed assets to reuse: existing SQLite GoalCycle, `run_experiment` registration to `make_local_reasoning_experiment`, native `reason_local`, durable goal history, original journal. Do not add a second memory system.
- Ledger/scoreboard: GitHub synthetic generation 54, 54 boots, 1808 events, run 43788868048, receipt SHA256 `5bd30b9342d2028d726db01485305d476809094f70feaf7787b7a5ac7d8e12ca`. Generation 54 candidate and grammar-matched baseline both 144/144; independently audited false. The historical compressed ledger and individual evaluation cases were not replayed in this session.
- Current evidence: `main` merge `bd28f881f12e94ccaeae667aa27e3d417514a620` (PR 395) restores native output guard. Exact-head PR-triggered workflow query returned no runs; CI at this head is **UNKNOWN**, not green.
- Unknowns/conflicts: independent oracle not installed in default runtime; true held-out advantage, native feedback-driven revision, and full integrated cognitive cycle remain unproven. GitHub and hosted adapter do not provide an executed local Core simulation here.
- Minimum change: preserve a falsifiable comparison protocol and explicit blocker for the next implementation run; no runtime behavior or policy changes.

## What source actually does

`bean_run.py` registers `run_experiment` using `make_local_reasoning_experiment` when the native reasoning service is present. The adapter validates bounded inputs, calls the actual `core.reason_local`, and persists an unverified observation through GoalCycle. It can invoke a host-supplied evaluator, but the default registration supplies no evaluator. Even when a host evaluator says correct, the adapter explicitly retains `status=unverified` and `independent_outcome_verified=False`. The expected answer is a host-provided comparison, not ground truth. Existing tests exercise this with a stub Core and synthetic SQLite restart; they do not demonstrate adaptive performance on unseen tasks.

## Competing next steps and falsifiers

**A. Add a second evaluator/store or independent agent framework.** This could simplify external benchmarking but creates duplicate persistence, unclear ownership and provenance. Reject unless it demonstrates a capability unavailable through the existing GoalCycle and journal, and survives restart without diverging receipts.

**B. Reuse the registered native experiment and attach a host-owned deterministic held-out oracle.** Prefer this as the smallest measurable integration. Build a sealed, versioned task generator that withholds labels from `reason_local`, supplies only `(domain, task_ref, query)`, and independently grades predictions afterward. Run equal-budget paired conditions: native Core with persisted feedback, unchanged Core with memory ablated, grammar-matched heuristic and random/majority negative controls. Record every case, failure, abstention, seed, source SHA, time budget, oracle version and outcome hash in the existing event/journal system. Reboot/reopen SQLite between train and held-out phases. Require improvement over strongest control on fresh out-of-distribution tasks, not only repeated known fixtures. Falsify learning if results tie the grammar control, disappear after restart, or rely on label leakage.

**C. Iterative research without oracle.** May improve explanations but cannot establish correct behavioral adaptation. Keep it optional and compare to single-pass under equal retrieval and time budgets; stop on exhausted budget or no new evidence.

## Execution receipt

HOURLY COGNITIVE SIMULATION NOT RUN. This GitHub connector can inspect and write source but cannot execute the checked-out Python Core; the authenticated BEAN connector is a hosted JavaScript note/evidence adapter, not the native Core. Specific blocking wiring defect: no independently graded, registered held-out digital experiment is wired into the default GoalCycle, and no Core runner was invoked in this session. No tests or CI were executed for this documentation-only change. No improvement or AGI claim is made.

Next implementation action: add a host-owned sealed synthetic oracle and a restart-aware paired evaluation test using the **existing** `run_experiment` action; run on a real Core checkout and publish exact-head test/CI receipts before merging. Preserve generation 54 checkpoint unchanged.
