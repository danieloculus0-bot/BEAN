# Ordered Core cognition and peer recovery evidence, 2026-11-19

BEAN CONTEXT ACK v1

- Task: add ordered durable execution to existing goals and evaluate a real restart-separated Core cycle; begin explicit comparison with BabyAGI 3.
- Existing systems checked: AGENTS, required gatekeeper/audit/open-agent docs, canonical origin and loader, GoalStateEngine/GoalCycle, native digital experiment, native reasoning/local learning/feedback, tick scheduler, historical default-wiring corrections, restart tests and generation 66 manifest.
- Confirmed reusable assets: original goal SQLite, canonical event stream, existing reasoning SHA journal and native rule learner. `run_experiment` is **already conditionally registered later in `bean_run.py`**. Initial construction alone gives a misleading missing-registration conclusion; do not rebuild it.
- Ledger/scoreboard reviewed: generation 66 reports candidate 144/144 and grammar-matched 144/144, with no demonstrated memory-specific advantage. Historical compressed ledger and prior correction receipts remain separate and preserved.
- Current evidence before changes: main `d967dee3b6df0d58f0b84b1510a46e78a7b14d80`, full Core Action [44613956747](https://github.com/danieloculus0-bot/BEAN/actions/runs/44613956747) passed. No open PR was returned.
- Unknowns/conflicts: broader CHAT HISTORY NOT CHECKED; complete ecosystem implementation and broad peer performance audits remain unfinished. Hosted BEAN memory was recalled with older notes and all three preliminary screens were called; none authenticates code or outcomes.
- Minimum change: immutable host-created linear plans in existing proposal records, prerequisite-aware execution, exact inference references for later feedback, and executable evidence collection.
- Runtime/behavior changes: planned steps require completed predecessors. Existing capabilities, approval fields and unplanned selection remain as before. No general planner, world-truth certification, model-weight update or consciousness claim.

## Actual execution and retained failures

An identical manually persisted two-step sequence was executed against unchanged `d967dee3` and the candidate. The predecessor had priority 9; its dependent prediction had priority 1. Baseline selected **prediction first** and failed the declared ordering assertion. Candidate selected **learning first**. This establishes the new dependency behavior, not an intelligence gain.

The first full local run passed 1,438 tests with 22 skips and 374 subtests. A subsequently added transaction-failure test then found a real implementation defect: the legacy `INSERT OR IGNORE` silently discarded a rejected second step and allowed a partial plan to commit. The affected suite recorded **1 failed, 100 passed**. Plan transactions now use strict inserts and roll back the whole sequence; ordinary proposal insertion retains its previous semantics.

Final local result, Python 3.12.14: **1,440 passed, 22 skipped, 374 subtests passed**, 68.82 seconds. Optional Bridge, PyTorch, browser and drawing dependencies remain among the skips. The dedicated affected goal/cognition/task set passed **101 tests**. Compilation and whitespace checks passed. Exact candidate and merge Actions evidence is recorded by the associated PR; local results do not certify remote runs.

Before publication, main advanced independently through PR #431 to `9caf815b8f40cb93fb156bd7ea196bdba6ee54fa`, adding a native skill incubator and holdout/artifact checks. Its source and documentation were inspected and reused as existing context, not reimplemented or attributed to this patch. The combined source passed the complete local suite: **1,447 passed, 22 skipped, 374 subtests passed**, 69.10 seconds. That is the final reconciled local test result.

Continuation on November 20 reconciled further main changes through `218a5eff1d6342ff9bf6ff7ba3eb51bbf6728364`, including the already-implemented curiosity-selected skill runtime and newer drawing/visual-memory work. The goal workflow conflict was resolved by retaining both native-skill checks and the new plan/peer probes. **1,481 passed, 44 skipped, 374 subtests passed** in 69.50 seconds on this combined source; additional skips include optional drawing/preview dependencies. Both standalone probes also completed again. The compressed November 19 traces remain unchanged as historical evidence; candidate CI produces new exact-source traces and databases.

Main's full regression [44664703683](https://github.com/danieloculus0-bot/BEAN/actions/runs/44664703683) passed at `8d25766180807b5ba305cf70df2f527570946bda`, but Qwen run [44664703649](https://github.com/danieloculus0-bot/BEAN/actions/runs/44664703649), job `136052469776`, failed its real arithmetic check: the model answered `2` where the independently computed answer is `4`. This was inspected in the actual job log and is retained as a genuine negative model result. No test is weakened or result relabeled by this plan change. A full regression pass is not a passing Qwen correctness claim.

The executable Core probe completed three real actions across two Core sessions, with later inference after another reasoning-journal reopen. Its trace covers observation, retrieval, hypothesis induction, goal selection, action, synthetic evaluation, feedback and later changed behavior. The deliberately false expected label remained false/unverified. Cold Core abstained on both withheld queries; retained Core answered correctly; the fixed-rule control tied it. These are small known synthetic cases, not a blind external benchmark or evidence that host-authored planning is autonomous.

`cognition.json.gz` contains the full JSON stage evidence. `manifest.json` records raw/compressed hashes and the verified gzip round trip. Source hashes in the report identify the actual implementation used. CI additionally uploads the original disposable SQLite databases; no prior public Core checkpoint or private runtime memory was reset.

## First pinned BabyAGI 3 comparison

Reference: [yoheinakajima/babyagi3](https://github.com/yoheinakajima/babyagi3/tree/b505d35b59b3544157e97fa30b7123bd6bc315c8), revision `b505d35b59b3544157e97fa30b7123bd6bc315c8`, MIT, Copyright (c) 2025 Yohei Nakajima. Inspected actual `scheduler.py`, `agent.py`, scheduler tests, dependency manifest and license. No upstream source is copied or bundled. This comparison imports the pinned external scheduler, not a reimplementation or simulated BabyAGI response.

Protocol: both real runtimes register an action that appends and fsyncs one fictional marker. Normal control executes once. The crash condition exits the worker process immediately after that effect, before the runtime records completion. A new process reopens original state and invokes the runtime's ordinary recovery/due-task API. No LLM, API token, external service or network request is used by the probe. Only one declared crash boundary is measured; this is a mechanism test rather than a statistically sampled intelligence benchmark.

| Condition | BEAN effects / duplicate effects | BabyAGI 3 scheduler effects / duplicate effects | Automatic completion |
| --- | --- | --- | --- |
| Normal | 1 / 0 | 1 / 0 | Both complete |
| Crash then restart | 1 / 0 | 2 / 1 | BEAN: Unknown, no replay; BabyAGI 3: completed after rerun |

BEAN preserves at-most-once handling of an ambiguous effect at this boundary; BabyAGI 3 achieves automatic completion by repeating it. Both metrics must be reported. This BEAN crash behavior predates the new plan feature, so it is not attributed to the plan patch. Neither system is declared universally superior.

An initial local attempt timed out in the peer scheduler's asynchronous persistence under restricted sandbox permissions. Repeating with network permission available completed the same model-free probe. The failed environmental run is not counted as a peer performance loss. The successful results and source/license digests are in `babyagi3_restart.json.gz`.

```sh
python research/peer_restart_probe.py \
  --babyagi3-root /path/to/clean/babyagi3 \
  --expected-babyagi3-sha b505d35b59b3544157e97fa30b7123bd6bc315c8 \
  --output /tmp/new-peer-restart-evidence
```

## Broader comparative acceptance requirement

The owner's target is to outperform BabyAGI 3 and other relevant agent/AGI research projects. Treat this as a research objective, not an achieved title. Maintain per-capability wins, ties, losses and unavailable evidence. Do not convert one recovery result, a feature checklist or BEAN's unit-test count into an intelligence ranking.

Search discovery requested 18 results across three workstreams. Primary references selected include [BabyAGI 3 architecture](https://github.com/yoheinakajima/babyagi3/blob/b505d35b59b3544157e97fa30b7123bd6bc315c8/ARCHITECTURE.md), [LangGraph persistence](https://docs.langchain.com/oss/python/langgraph/persistence), and [LifelongAgentBench](https://arxiv.org/html/2505.11942v3). Search matches and paper claims are not independently reproduced measurements. LangGraph, Letta and OpenHands head-to-head execution is **NOT RUN** in this increment.

Next comparisons must pin source/model revisions and licenses, share task observations/tools, match inference/token/time budgets, and use independent held-out graders. Cover acquisition, delayed recall, stale/conflicting evidence, restart continuity, multistep completion, failure recovery, and transfer to new environments. Include memory-ablated and strong fixed/grammar-matched controls, retain negative outcomes, report per-task denominators and uncertainty, and distinguish framework execution from model competence. Use external task families such as lifelong DB/OS/KG tasks after checking existing BEAN research, rather than optimizing these opened toy cases. No broadly validated superiority over BabyAGI 3 or all AGI projects is established here.
