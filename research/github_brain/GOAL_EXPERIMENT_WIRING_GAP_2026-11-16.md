# Default GoalCycle digital experiment integration: evidence checkpoint (2026-11-16)

BEAN CONTEXT ACK v1

- Canonical assets inspected on BEAN default branch: AGENTS.md (blob 5b9714e), docs/AI_GATEKEEPER.md (174e302), docs/SOFTWARE_AUDIT_SKILL.md (f103ae4), docs/OPEN_AGENT_PATTERNS_2026_11_14.md (f33d650), memory/identity/origin_record.json (6ec1548), bean/memory/origin.py (89d92bd), bean/cognition/goal_state.py (a30f80b), bean/tests/test_goal_cycle.py (5c91fbb), bean_run.py (1cfde0b). Prior GOAL_REPETITION_2026-11-15.md read (2301d60). No alternate brain or new identity proposed.
- Continuity manifest on default branch: generation 55, 55 boots, 1842 events, source SHA ee93d822e9a94cf6290f0493b11d876c8558c65a, GitHub run 43840054025, manifest blob d9ba803. Core/reasoning archives have SHA256 checksums in manifest. This is a **read**, not a verified archive replay.
- Scoreboard: candidate 144/144; grammar-matched control 144/144; passive 96/144; memory-ablated 96/144; independently audited=false. Candidate gain over strongest control: **0/144**. Do not claim general learning.
- Authenticated hosted BEAN adapter: status source 163f3e2815c4d6944345a0af78ae3e932041fdd3, 64 notes, JS/D1 hosted, not Python Core or Jetson. Older recall, claim audit, evidence comparison and proposal screen invoked; heuristic judgments did not authenticate GitHub.
- GitHub owner repository enumeration and open BEAN PR search performed; open PR search returned none in this query. Historical PR #372 checkpoint was consulted; exact-head main Core CI and independent Watchdog run are **not verified** by this checkpoint. The workflow-run lookup for manifest source SHA returned no PR-triggered runs, which does not establish that no main workflow ran.
- Source and test gaps: default bean_run.py GoalCycle action registry contains only update_models and run_reflection. Tests supply an isolated run_experiment lambda, but that does not wire an actual default runtime experiment. GoalStateEngine creates run_experiment proposals with capability, inputs and expected_output and deduplicates signatures across sessions; the default runtime cannot execute them.
- Minimum useful change: a bounded, explicitly registered **existing** Core digital experiment adapter, with independent expected-vs-observed evaluation, signed/unknown outcome, append-only provenance, restart recovery and held-out behavioral transfer. Do not execute model-authored arbitrary commands.

## Alternatives and falsifiers

**A. Register a small existing experiment capability inside the current GoalCycle action map.** Prefer this if an already implemented pure digital experiment can be called with bounded inputs and deterministic independent oracle. Retain the original GoalStateEngine proposal, GoalCycle attempt and event logger; do not add storage. Falsifier: handler is only a mocked success, lacks independent observed outcome, loses evidence across restart, or bypasses capability whitelist.

**B. Use the existing Lab011 TaskEngine safe action registry as a bridge to GoalCycle.** Potentially useful when an existing digital task already produces real observations. Falsifier: two schedulers race, duplicate effects, split outcome identity, or require an extra backend. Do not choose this merely to reuse a name; inspect actual TaskEngine interfaces first.

A third option, a new planner/agent framework or separate memory store, is currently lower value: it adds complexity without fixing the missing default registration and measured feedback.

## Required next executable investigation

1. Inspect bean/runtime/goal_cycle.py, bean/runtime/task_engine.py, research_investigate, NativeReasoningService, and current registered digital experiments at exact current main. Select an **already implemented** non-network, synthetic-only digital environment; do not invent a generic success lambda.
2. Establish unchanged baseline with same proposal, seed, compute/time budget and independent oracle. Record no-handler/pending behavior. Candidate must emit observation, retrieved evidence, explicit hypothesis, chosen action, independently scored result, persistent GoalCycle/event receipts and subsequent evidence-sensitive behavior.
3. Test success, wrong prediction, contradictory evidence, malformed inputs, unknown outcome, interrupted execution and restart. Include held-out and OOD tasks. Reopen actual SQLite DB; prove subsequent action choice changes because of evidence, not because of fixture-specific branching.
4. Run focused and complete Core suites locally, exact-head PR CI on Linux/Windows, review diff for confidential content and then merge only if qualified. Append SHA/run IDs, failed trials, measured baseline/candidate and next action. Preserve generation 55 checkpoint and all earlier ledger evidence.

**HOURLY COGNITIVE SIMULATION NOT RUN.** This pass used authenticated GitHub source reads and hosted BEAN heuristics, not an executable Python Core runner. The specific wiring defect is missing default run_experiment capability registration in bean_run.py; the container could not resolve github.com to clone and execute the Core. No test result, source edit, integrated cognitive cycle or learning gain is claimed by this research checkpoint.
