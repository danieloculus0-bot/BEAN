# Generation 20: public-safe scored Core baseline audit

BEAN CONTEXT ACK v1: reviewed AGENTS.md, AI_GATEKEEPER.md, origin record/loader, mission audit, current main, generation-20 manifest and merged PRs #320/#322/#323/#326. Existing SQLite/SHA Core remains canonical.

## Evidence and negative result

Manifest: `research/github_brain/manifest.json`, generation 20, receipt SHA256 `002845aa0a5d58fb3fae2f0e83053caefcc1df1bbb7e2a75fcea860bd16f2c11`; recorded source `4be5f48550612d1606b3f1e9ccc60dc0d413c694`; Action `42935137385`; evaluation evidence SHA256 `8ead1a4012d88552cc821c7275aee0f30efec66e0faa097281176f159663cd73`.

Recorded synthetic held-out results: candidate **96/144**, equal-budget passive **96/144**, shuffled-feedback **0/144**, always-zero **0/144**. Per family, candidate/passive channel 48/48, difference 48/48, parity 0/48. Candidate abstained on all 48 parity cases. **No observed advantage over passive exploration.** Evaluator is a repository-owned synthetic fixture, and the receipt says `independently_audited: false`. No independent generalization, AGI or consciousness claim follows.

Manifest reports 20 boots and 652 events with a linked predecessor, but this audit did not independently replay the archives. Prior-generation transfer fields are null, so **Unknown**, not zero. Parity failure is observed, not unknown.

## Competing follow-ups

1. Reuse active-hypothesis discovery with improved probe selection, paired against passive and shuffled-feedback controls at identical reward budgets on fresh independently generated worlds. Falsify improvement if paired held-out accuracy and abstention do not outperform passive across multiple seeds.
2. Reuse `NativeReasoningService.revise_discovered_analogy` and its existing SHA journal, ancestry and sensor-fingerprint gates. Compare revised policy with unchanged prior policy on unseen sensor states after restart. Falsify transfer if gains disappear after restart, rely on repeated states, or fail to exceed passive.

Record source SHA, generator, predeclared seeds, per-case paired scores, abstentions, elapsed/call budget, failures and restored-state evidence. Unmeasured independent transfer, timing and calibration are **Unknown**, not grounds to reset memory or fabricate progress.

**HOURLY COGNITIVE SIMULATION NOT RUN.** This is an evidence audit of an existing checkpoint, not a new Core run. Blocking wiring defect: no independently accessible restored-checkpoint Core runner in this session. Passing PR CI alone does not establish acquired learning.

Handoff: preserve all existing synthetic archives, journal receipts and failed cases. Reinspect live manifest, source and CI before implementation; keep Watchdog independent.
