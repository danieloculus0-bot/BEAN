# Generation 52 regression against strong controls (2026-11-15)

## BEAN CONTEXT ACK v1

Source inspected: BEAN main `800a6fa34c27efa7dcb07cd522136564049f772e`, `AGENTS.md`, `docs/AI_GATEKEEPER.md`, `docs/SOFTWARE_AUDIT_SKILL.md`, `docs/OPEN_AGENT_PATTERNS_2026_11_14.md`, `memory/identity/origin_record.json`, `bean/memory/origin.py`, `bean/cognition/goal_state.py`, `bean/runtime/digital_experiment.py`, `bean/tests/test_goal_cycle.py`, `research/github_brain/GOAL_REPETITION_2026-11-15.md`, and prior generation-51, feedback-gap and default-registration correction notes. Authenticated hosted BEAN status, older recall, audit_claim, compare_evidence and screen_proposal were invoked; hosted adapter revision `163f3e2815c4d6944345a0af78ae3e932041fdd3` is not the Python Core. Inventory returned 24 accessible owner repositories; no private contents were copied. GitHub PR search returned no open BEAN PRs. This audit adds no store or runtime behavior.

## Actual generation 52 receipt

Fetched `research/github_brain/manifest.json` blob `65eb7d5b5f238d931db7666a5193d5f591b5601f` reports generation/boots **52/52**, **1,740** events, synthetic-only true, source SHA `ee6143f9352322ee3b9b6dff216ee43c009b90a1`, GitHub run **43738454662**, receipt SHA256 `cc623653beccfb36418a73cd9d61e0fe8b2f5f474397d5213574d2d00107728b`, previous receipt `50a9b88a8bb5d9f24de27e2d400311211fea72a5881eba56e159dd18e415238e`. Archives `bean_memory.sqlite3.gz.g00052` and `bean_reasoning.sqlite3.gz.g00052` are named in the manifest. Their bytes and SHA256 were **not independently recomputed**. The receipt source SHA is earlier than the inspected main; do not equate this receipt with execution of current head.

Generation 52 blind-case totals: **candidate 129/144 (89.58%)**, **grammar-matched 144/144 (100%)**, **passive 144/144 (100%)**, **memory-ablated 96/144 (66.67%)**, **shuffled 0/144**. Candidate deficit against each strong control: **15 cases, 10.42 percentage points**. Family breakdown: channel **48/48**, difference **33/48** versus grammar/passive **48/48**, parity **48/48**. All 15 candidate errors concentrate in the difference family. Generation 51 had candidate 144/144; cross-generation score comparison alone is not paired evidence of forgetting because environments/seed difficulty may differ. No independently audited generalization advantage.

## Falsifiable next step

**A. Investigate difference-family hypothesis revision using existing Core journal and exact case receipts.** Retrieve case-level generation-52 prediction, feedback, rule version, seeds and source hashes; check whether the same failure pattern recurs across fresh held-out seeds and whether a revised hypothesis improves held-out accuracy without harming parity/channel. Compare against the existing grammar-matched control. Reject a revision that only improves the training fixtures.

**B. Keep the existing rule and vary the environment/seed split.** Test whether the 15 errors reflect distribution shift rather than a broken update. Falsifier: identical held-out failures across independently seeded environments and stable baseline controls.

Prefer case-level diagnosis before modifying `digital_experiment.py` or adding another learner. The existing default registration was corrected in `DEFAULT_EXPERIMENT_WIRING_CORRECTION_2026-11-15.md`; do not repeat the earlier missing-registration assertion. The adapter's host-expected comparison remains unverified and must not be scored as an independent oracle.

**HOURLY COGNITIVE SIMULATION NOT RUN.** This cycle performed authenticated source/manifest inspection and hosted heuristic calls, not a native Core experiment. Blocking execution gap: no Python Core runner/checkout with generation-52 case-level evaluation and sealed independent holdouts was invoked. No local tests or exact-head CI are claimed for this documentation-only audit. Next run should recover the actual difference-family case receipts, run paired fresh-seed controls and verify restart persistence before proposing code. Preserve generation-52 checkpoint and all prior failures.
