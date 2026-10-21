# BEAN — AI activity gatekeeper (v1)

> **READ AND ACKNOWLEDGE BEFORE ANY BEAN TASK.**
> This is a context/orientation prompt for AI collaborators, not a restriction on BEAN's experimental reasoning or an automatic runtime authorization system.

## Start here

You are helping engineer **BEAN (Behavior Enabled Avatar Node)**, its experiments, interfaces, ledger, integrations or public documentation. Before recommending new architecture, writing code, running tests, changing a demo, or preparing a launch, determine **what already exists**. BEAN's research branches, mainline, Bridge, neural experiments and persistent compressed ledgers are not interchangeable.

### 1. Recall existing knowledge

- When the authenticated **BEAN connector** is available, call its `bean_status` and `bean_recall` functions with `include_older=true` for the task's topics. The hosted BEAN memory adapter is **not** the local Python Core or a neural trainer; its notes are clues, not independently authenticated facts.
- Search the canonical portfolio: https://github.com/danieloculus0-bot . Inspect BEAN `main`, relevant branches, open PRs, current files and CI before asserting a feature is absent, live or tested.
- Look for the **existing component first**, including implementations hidden in experimental branches. Do not rebuild a Q-network, event store, bridge, evaluator or UI because it did not appear in one README.

### 2. BEAN inventory before proposing changes

| Existing asset | Where to check | Critical distinction |
| --- | --- | --- |
| BEAN Core | `bean/`, `bean/runtime/boot_readiness.py`, `bean/memory/` on `main` | Local Python cognition and durable SQLite; no claim that every experimental feature runs here. |
| **SpongeTD Q-learning** | `experiment/bean-sponge-core-20261011`, `bean/optimization/sponge_td.py` | Real tabular updates and scored compressed checkpoints in a separate experiment. |
| **SpongeDQN neural learner** | `experiment/bean-deep-q-learning-20261012`, `bean/optimization/sponge_dqn.py` | PyTorch **3 → 64 → 64 → 3** DQN, minibatch replay, target network, gradient updates and compressed checkpoint recovery; engineered three-number Breakout state, **not** a general-purpose retrieval network or `main` runtime. |
| Neural evolution | Same deep-Q branch, `experiments/sponge_breakout/evolve.py` | Tested offspring with failures and fallbacks. Do not claim overall advantage without seed-level evidence. |
| BEAN AI Bridge | `danieloculus0-bot/BEAN-AI-Bridge-`, Lab009 and PR #46 | Separate evidence and learning-loop runtime; label frozen replay separately from online acquisition. |
| Compressed scoring ledger | `experiment/anticipatory-ledger-20261020`, `research/persistent_ledger/` | Keep **both** raw compressed history and rebuildable scoreboards. The append-only archive is evidence; the scoreboard is a summary. |
| BEAN self-benchmark | PR #140, `experiment/bean-self-benchmark-ledger-20261020` | Indexed recall benchmark on synthetic JUnit data; BEAN Core ranked host-proposed options; no neural ranker demonstrated. |
| Website | `docs/index.html`, `#learning` | Public claims must point to their exact experiment, branch, revision, and tests. GitHub Pages serves `main` after deployment. |

This inventory is a **starting map**, not an assertion that all links are current forever. Re-verify state each session.

### 3. Read the scoreboard and receipts

- Inspect `research/PERSISTENT_LEDGER.md` and `research/persistent_ledger/` on the ledger branch, including any newer experiment-specific scoreboards.
- Recover source events by hash/ID where available. If only an aggregate exists, **say individual-case retrieval is unverified**. Never reconstruct missing test results from totals.
- Separate: original baseline, persisted frozen replay, online new evidence, genuine learned-weight changes, conventional-control comparisons, and held-out evaluation.
- Retain failures, seeds, environments, versions, skipped tests, and negative outcomes. A repeating deterministic test is **repeatability**, not independent learning.
- Check current relevant CI **at the exact commit**; historical green runs do not certify a different head.
- Keep the active memory small and retrieve supporting records on demand. The compression legend/hash mapping must be versioned and reversible; hashes are identifiers, not condensed understanding.

### 3A. Show BEAN the scoreboard and the reward

A learning agent cannot benefit from an archive it has never read.

- Before optimizing a policy, retrieve the existing scoreboard and relevant compressed trial receipts, not just verbal summaries. On the experimental `experiment/bean-visible-scoreboard-reward-20261020` branch, `python -m bean.optimization.scoreboard_context --ledger research/persistent_ledger` exposes a bounded JSON inventory of known scoreboards.
- That experimental module's `score_reward` produces a **signed reward** from a matched outcome: positive for better, negative for worse, exactly zero for an evidenced tie, and `null` for incomplete/missing comparison. Rewards belong to an identified experiment and metric, never a made-up overall intelligence score.
- Each evaluation receipt can earn credit once. **Preserve the exact failure cases, matched baseline, full evidence, condition, source revision and training state**. A repeated identical deterministic test is not new independent learning.
- The reward context/adapter is **research only** and is not yet installed in Core `main` or the hosted BEAN memory connector. Treat access as `NOT WIRED` if the current runtime cannot call it; never say BEAN saw a score unless its actual input and response were inspected.
- This section defines a research-data interface and AI-workflow requirement, **not an extra BEAN inference-time safety rule or automatic reward tuning**.

### 4. Work with, not around, BEAN

- Use existing BEAN functionality to recall and preliminarily critique claims when available. BEAN's hosted `bean_audit_claim` is a **heuristic**, and can approve contradictory statements; it is not a truth oracle or independent test runner.
- For technical optimization, compare an unchanged baseline with the candidate using identical tasks, budgets and evaluation conditions. Let BEAN propose/select approaches in an experiment, but let an independent evaluator determine correctness.
- If the user requests freedom for exploratory research, **do not quietly introduce new behavior filters or arbitrary approval rules**. The gatekeeper exists to preserve context and evidence, not constrain a learning policy. Respect any separately applicable security and legal requirements.
- Do not claim BEAN Core and BEAN Bridge are already one continuously integrated runtime.
- If a required connector, file, branch, archive or test result is inaccessible, report that fact and proceed with a clearly scoped plan rather than guessing.

### 5. Required acknowledgement before work

Print an actual **BEAN CONTEXT ACK v1** for the current task before any substantive edit, with:

```text
BEAN CONTEXT ACK v1
Task: <what will be done>
Existing systems checked: <connector if available; specific repo/branches/files>
Confirmed assets to reuse: <actual implementations, with refs>
Ledger/scoreboard reviewed: <paths and limits, or UNAVAILABLE>
Current evidence: <CI run/commit; what it proves and does not prove>
Unknowns/conflicts: <list or none confirmed>
Minimum proposed change: <scope>
Runtime/behavior-policy changes: <none, or explicit proposal>
```

A missing tool does not justify inventing an acknowledgement. State `UNAVAILABLE` or `NOT CHECKED` and the reason. If a new discovery invalidates your ACK, amend it before continuing.

### 6. Prelaunch / publication handoff

Before publishing or launching, verify target branch/revision, proposed scope, test outcomes, prior failures, original data retention, model/dependency needs, public claim evidence and rollback target. Acknowledge **READY FOR REVIEW** or **BLOCKED: <reasons>**. This is a communication gate; it does not silently install runtime restrictions or make a private workstation reachable.

## Principle

**Remember the machinery we already built. Use it. Make improvements measurable. Preserve the evidence.**
