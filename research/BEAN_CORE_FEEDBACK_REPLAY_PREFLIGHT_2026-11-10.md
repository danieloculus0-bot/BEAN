# BEAN Core: measurable digital feedback and replay preflight (2026-11-10)

**BEAN CONTEXT ACK v1**

- Task: identify the smallest verifiable connection between a real digital Core boot, an independently scored task, and restart reuse.
- Existing systems checked: `AGENTS.md`, `docs/AI_GATEKEEPER.md`, origin JSON and loader, November 6 continuity audit, `scripts/invoke_bean.py`, invocation workflow, generation-17 manifest, PR #315, PR #214, experimental `bean/optimization/scoreboard_context.py`, hosted BEAN status and older recall.
- Confirmed assets to reuse: existing Python Core, SQLite event history, native reasoning service, GitHub checkpoint/restart mechanism, experimental reward trial and immutable receipt concepts. No new database or learner proposed.
- Ledger/scoreboard reviewed: reward adapter source on `experiment/bean-visible-scoreboard-reward-20261020`; **actual persisted trial archive and individual scores NOT CHECKED**, so no gain is inferred.
- Current evidence: manifest generation 17, 17 boots, 550 events, receipt `a2eb025dfea0ba5397209123cc2ec87ff044acdd9afaa49b8804bed2d631c302`, source `d924b4340b301f0620a41cd56d76d70799c89c6f`, recorded Action `42781625654`. This proves claimed synthetic continuity subject to archive verification, **not** learning. PR #315 is separate checkpoint safety work, head `117a853e412da37d2e5b0b5507030e0b650b1f2e`, no independent review.
- Unknowns/conflicts: Core's exact callable task interface, evaluator placement, task corpus and durable feedback ingestion need a source-level implementation review; PR #214 is an unmerged experimental retrieval branch.
- Minimum proposed change: add a bounded, opt-in **synthetic** task/evaluation seam in the existing invocation and journal, not a second brain.
- Runtime/behavior-policy changes: none in this research note.

## Deficiency observed in source

`invoke()` restores the existing checkpoint, queues `run_brain_maintenance` and `update_models`, runs ticks, checks that two inbox commands were processed, and publishes a continuity manifest. Neither command supplies a fresh task with an independently verifiable answer. The receipt counts boots, events, ticks and commands, but no baseline, held-out task IDs, scored outcomes, feedback ingestion, or post-restart transfer. The workflow's two boots therefore measure persistence, not learned competence.

The experimental `score_reward(RewardTrial)` accepts caller-supplied measurements and evidence hashes, returns signed reward only for complete matched comparisons, and explicitly sets `verified_evidence=False`. `record_reward` prevents duplicate receipt credit by immutable file creation. It **does not independently authenticate** the scores or show that Core consumed a reward. Copying this module into main without a trusted evaluator would make an apparently sophisticated but circular metric.

## Competing approaches and falsifiers

**A. Reuse the experimental reward adapter immediately.** Pros: signed negative/tie/incomplete outcomes, duplicate-credit semantics, source-linked evidence. Cons: without independently computed outcomes, caller-supplied scores can be fabricated and reward can never demonstrate acquisition. **Falsifier:** deliberately swap candidate and baseline answers or supply a mismatched evaluation hash; any resulting accepted improvement invalidates the evaluation chain. This approach is premature until the evaluator exists.

**B. Start with an external, deterministic evaluator around existing native Core reasoning, then persist its receipt in the current Core journal.** Pros: narrow trust boundary; no new learner or database; tests can prove actual task execution, outcome comparison, restart recovery and zero reward on duplicate receipt. Cons: a tiny symbolic benchmark may show only memorization. **Falsifier:** random-label and shuffled-feedback controls match the candidate, or improvement vanishes on independently withheld tasks after restart. This is the preferred first integration seam, not evidence of AGI.

## Bounded executable acceptance experiment for the next code change

1. Freeze source SHA, task generator version and random seed before executing. Generate disjoint train, validation and **unseen holdout** IDs. Use at least two structurally different synthetic digital task families; prohibit answer keys in the Core request or memory input.
2. Run a *single-pass, no-feedback* baseline and the *feedback-enabled* candidate with identical time, token/call and task budgets. Add a shuffled-feedback negative control and a same-run replay control.
3. Independently evaluate exact outputs outside the reasoning service. Write immutable per-case receipts containing task hash, family, split, baseline/candidate output hashes, scored correctness, latency, source SHA, seed, and evaluator revision. Hash the canonical payload; never label a caller-supplied metric as independently verified.
4. Persist only synthetic task feedback through existing SQLite event/journal interfaces. Restart Core from its prior checkpoint and query whether learned state is actually available. Evaluate on fresh holdout IDs without feedback. Compare paired per-case accuracy and failure modes, not just event counts.
5. Test duplicate receipt replay, corrupted hash, incomplete coverage, negative outcome, interrupted checkpoint publication and independent fresh-start baseline. Reject or quarantine invalid receipts without overwriting prior evidence.
6. Report exact task counts, confidence intervals where appropriate, all failures, source revision and run receipts. If no measurable holdout gain exists, publish that negative result rather than claiming learning.

**Stopping criterion:** maximum two task families, 50 train and 50 held-out cases per family, three fixed seeds, and a hard 120-second evaluator budget per run. A timeout or unsupported native reasoning response is a failed/incomplete case, never silently omitted.

## Implementation boundary

Keep `research/github_brain/` as the existing public-safe checkpoint and `bean/memory/event_logger.py` as the event source. Use existing `NativeReasoningService` and journal rather than creating a second model provider. If its current API cannot accept/consume the scored feedback, first add a small testable adapter with an explicit no-op baseline. Keep the experimental reward module separate until source-authenticated evaluation is demonstrated. The public GitHub artifact must contain synthetic task/receipt hashes only, no private memories, employer data, keys or Jetson access.

**HOURLY COGNITIVE SIMULATION NOT RUN:** this increment is a source-grounded falsification and test contract, not an executed integrated learning experiment. Blocking wiring defect: mainline `invoke()` has no independently scored task feedback ingestion and held-out post-restart evaluation path. No checkpoint was modified. No consciousness or AGI conclusion follows.
