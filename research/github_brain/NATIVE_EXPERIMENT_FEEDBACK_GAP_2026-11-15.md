# Native digital experiment: independent feedback gap (2026-11-15)

BEAN CONTEXT ACK v1

- Baseline: BEAN main `d18b7bb6ce5851515d370122ed836934ae2893fd`; existing canonical origin, AGENTS.md, AI_GATEKEEPER.md, SOFTWARE_AUDIT_SKILL.md, OPEN_AGENT_PATTERNS_2026_11_14.md, GoalCycle registration and earlier GOAL_REPETITION_2026-11-15.md were retrieved. Hosted BEAN status and older recall checked; hosted adapter revision `163f3e2815c4d6944345a0af78ae3e932041fdd3` is **not** native Core.
- Continuity: current GitHub-brain manifest blob `0d7025df582d15623eb64821892ade3636d0d1b5` reports generation 51, 51 boots, existing core/reasoning SHA-256 archives. No checkpoint rewritten.
- Inventory: GitHub returned 24 owned repositories, including private metadata. Private contents were not copied. No open BEAN PRs were returned. Relevant merged PRs #372 through #378 were inspected by metadata; #375 introduced `bean/runtime/digital_experiment.py`, #376 registered it in `bean_run.py`. Do **not** repeat the already completed registration work.
- CI: commit-associated PR workflow query and combined-status query at the inspected main SHA returned no records. This is **unknown exact-head CI**, not a failed or successful run.
- Minimum useful next change: independently scored digital experiment feedback that can affect later decisions, using existing Core journal, GoalCycle, event receipts and SQLite, with no parallel memory owner.

## Observed implementation and falsifiable gap

At inspected source blobs `864b206a74fd740e59c76c21590d3ea55a65172c` (`bean/runtime/digital_experiment.py`) and `9710a8bab414e96cfed6a61a91212e237d4620fe` (`bean/tests/test_digital_experiment.py`), the registered experiment calls `NativeReasoningService.reason_local` with bounded domain/task_ref/query, compares the answer to a host-supplied expected string, and **always** returns `unverified` for both matching and nonmatching answers. This is epistemically correct: the expected string is not independent ground truth. Its tests use a fake Core with scripted outputs; one integration test verifies persistence/no replay with synthetic SQLite. These tests do not demonstrate actual novel-task acquisition or adaptive improvement. The real `reason_local` method (blob `b1942541107af10651abca9fe7a91e9b019f3e30`) routes to local primitive/composed reasoning.

**Negative result:** current source and tests do not establish an independent measured reward, a later behavior change, or a held-out gain over a strong control. The generation-51 manifest still reports candidate 144/144 and grammar-matched control 144/144; this is a tie, not evidence of advantage. The hosted BEAN claim screen also downgraded an assertion of proven independent adaptation, but that heuristic is not an evaluator.

## Two approaches

**A. Reuse native Core feedback/evaluation and GoalCycle receipts (preferred).** Register an explicitly bounded synthetic environment evaluator as a trusted host capability; keep expected answers sealed until after prediction, emit evaluator provenance and case hash, persist feedback in the existing journal, then test whether subsequent goal selection or answer behavior changes. The evaluator must not let BEAN score its own answer or expose holdout labels before prediction. Falsifiers: unchanged behavior after feedback, a shuffled-label control matching candidate performance, repeated credit from identical receipts, failure to recover outcome after restart, or a strong grammar-matched baseline tying candidate.

**B. Add a separate benchmark/experiment service.** It could simplify environment lifecycle, but creates another persistence/receipt authority and risks disconnected tests. Reject unless the existing Core APIs demonstrably cannot represent observations, actions, outcomes and source-linked revisions. Falsifier for this rejection: a reproducible integrated experiment that cannot be expressed without a separate owner after a focused Core API test.

## Proposed executable experiment

Use at least two synthetic rule families with independent seed-based train/held-out splits and a domain-shift split. Freeze the evaluation cases and hashes before the candidate sees them. Record prediction, source SHA, selected goal/action, feedback receipt, elapsed/call budget, later prediction, abstention and wrong cases. Compare **paired** no-feedback, shuffled-feedback, grammar-matched and candidate conditions under identical budgets. Restart SQLite and the reasoning journal between learning and evaluation; verify exact receipt replay without duplicate reward. Report score deltas with individual failures, not just totals. No provider, Jetson, private memory, or employer data.

**HOURLY COGNITIVE SIMULATION NOT RUN.** This run inspected live GitHub source and test definitions but had no authenticated checkout/runner for the current main and no independent feedback evaluator registered in Core. Blocking wiring defect: the registered `run_experiment` only compares against host-provided `expected_output` and cannot produce independently verified outcome feedback. No test or CI success is claimed for this research note.

Next: implement the smallest sealed-evaluator hook using existing journal/GoalCycle interfaces, write failing-before/fixed-after regressions and a real restart+held-out paired run, then inspect exact-head CI and merge only on verified evidence. Preserve all existing generation-51 archives and failures.
