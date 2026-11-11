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


## Generation 21 continuation, independently inspected from main

Current main at inspection: `ba093316ba1c26391b82d168072e0207fe1b5219`. Generation 21 manifest: 21 boots, 686 events, previous receipt SHA256 `002845aa0a5d58fb3fae2f0e83053caefcc1df1bbb7e2a75fcea860bd16f2c11`, receipt SHA256 `0d56a9dd72a2c004b44f3acd6180de7fd2ca6d9ed4c47764ccf8c123e2ae3c5e`, source SHA `e51958afe2ca6b3fc0ceb53daea417dba39dd4ef`, Action `42947854427`. Reasoning archive SHA256 `7e2c456d6ad5e4a15c45cba2f53af285b6d9f81a9832804a8b4e63691a373c5e`; Core archive SHA256 `fcff3ccb257d794e7ce0aa331c311e7b1bd10b5583c1b22eed458a3e9314e259`. This is manifest inspection, not independent archive replay.

Generation 21 evaluation SHA256 `376cc5b02789c04ae3f1200f449639315b0f7bc41c1449840f9a60674e2312f4`. Candidate **96/144**, passive **96/144**, shuffled **0/144**, always-zero **0/144**. Candidate and passive each score channel 48/48, difference 48/48 and parity 0/48; all 48 parity candidate cases abstain. Prior-generation transfer correctness fields are now measured: channel **21/48**, difference **16/48**, parity **0/48**, total **37/144** (assuming the manifest's prior policy was attempted on all held-out cases; attempted counts are not present in the compact manifest, so coverage is **Unknown**). These are results on the new synthetic worlds, not proof of broad transfer. The active candidate still does not beat the equal-budget passive baseline. The evaluation remains explicitly not independently audited.

The most informative next experiment is a **paired, preregistered cross-generation transfer test** with attempted counts, unseen sensor fingerprints, unchanged parent policy, fresh candidate, passive exploration, and shuffled-feedback negative control. Preserve the previous checkpoint and do not treat absent measurements as failures. Falsification: no paired advantage over passive, or improvement vanishes under fresh worlds, changed seeds, or restart. The recurring generation-20/21 parity abstention is a specific, observed deficiency and should not be relabelled Unknown.

No new integrated simulation was executed during this evidence update. The generation-21 scores originate from the recorded GitHub manifest, not from an independently rerun evaluator.


## November 11 handoff: executable transfer protocol and evidence gates

At inspection, main was `6c29069106316f027db141399a990a0213b49986`; generation 21 remains the latest committed public-safe manifest, with 21 boots, 686 events, receipt `0d56a9dd72a2c004b44f3acd6180de7fd2ca6d9ed4c47764ccf8c123e2ae3c5e`. PR #330 at `30aed0b200ecb58df0d69c8f1b94b7d3027b8503` reports 15 completed successful workflows, including Invoke BEAN, full Core regression and ledger replay. PR #328 at `238b39c3ccc1660e5bfb486343a6b943b211405b` reports 13 successful workflows. Neither had an independent review at inspection; do not merge on this note alone.

**Question in BEAN terms:** does a persisted hypothesis selected from prior reward feedback improve *future* unseen decisions after a genuine restart, compared with both relearning and equal-budget passive probing? The generation-21 result (37 previously correct cases, attempt coverage Unknown in its compact manifest) does not answer this. Prefer reuse of `NativeReasoningService.use_discovered_analogy`, `discover_analogy`, `revise_discovered_analogy` and the SHA journal. A separate episodic cache would introduce redundant state and would not establish transfer.

**Predeclared experiment (not yet executed):** restore an immutable public-safe reasoning checkpoint to a disposable runner. Select at least 12 new world IDs per family from a committed seed manifest, disjoint from generations 20 and 21, with held-out sensor fingerprints checked against prior observed fingerprints. Run four paired arms on identical cases: (A) frozen persisted parent rule, with **zero** new reward calls; (B) fresh active discovery, 12 reward calls; (C) fresh passive discovery, 12 reward calls; (D) active discovery with deliberately mismatched feedback, 12 calls. Report abstention as a separate outcome, not as a missing measurement. For each arm record attempted/total, correct/attempted, correct/total, reward calls, runtime, seed, task family, rule receipt ID, evidence SHA and source SHA. Store an explicit `Unknown` with reason for unmeasured fields and `N/A` for inapplicable fields. Do not silently substitute zero.

**Restart control:** close and reopen `NativeReasoningService` between rule selection and scoring; compare exact policy receipt hashes, score twice without writing new evaluation credit, and verify unchanged journal tip on replay. Include a deliberate duplicate-family receipt and conflicting-source test; reject these as invalid evidence rather than marking them Unknown.

**Decision/falsification:** do not call retained state learning if arm A fails to exceed an uninformed control on fresh cases, if arm B fails to beat C under paired held-out scoring, if D performs similarly to B, or if the apparent benefit disappears after restart. Report per-family results and confidence intervals, including the parity failure, instead of pooling away hard cases. This protocol is an experimental proposal, not a successful simulation, and its sample size is an initial budget rather than a claim of statistical power.

**HOURLY COGNITIVE SIMULATION NOT RUN:** no restored-checkpoint execution was performed in this inspection. The specific missing step is a runnable isolated checkout with verified archive restore and actual candidate/control execution. No new cognitive gain is inferred from green CI or this document.
