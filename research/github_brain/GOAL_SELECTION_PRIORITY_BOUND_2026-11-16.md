# GoalCycle selection: priority dominates observed outcomes (2026-11-16)

BEAN CONTEXT ACK v1

- Scope: source-level falsification of the claim that GoalCycle can generally switch to a better-performing digital action based on recorded failures. This is a narrow research receipt, not a new planner or simulated Core cognition.
- Current source: `bean/runtime/goal_cycle.py` blob `0963907892ad5f4691bc08f40013952f1ae51174`; `bean/cognition/goal_state.py` blob `a30f80bef109d19e2f52f661a361175efecdcaa5`; `bean/tests/test_goal_cycle.py` blob `5c91fbb17608cdcbbdeeb4116a19fc459a2b0c5c`.
- Reviewed: `AGENTS.md`, `docs/AI_GATEKEEPER.md`, `docs/SOFTWARE_AUDIT_SKILL.md`, `docs/OPEN_AGENT_PATTERNS_2026_11_14.md`, origin record/loader, `research/github_brain/GOAL_REPETITION_2026-11-15.md`, current manifest generation 56. Prior PR #401 already records missing default digital-experiment registration; do not duplicate that finding.
- Main source head at investigation: `84f9a73305641762b3281ebfe6420c8caf5c183b`; manifest generation 56, 56 boots, 1876 events, receipt `c4cfd23297411d1885c16e8b3728410c2cab5e95acead470a4da4af9b4009b0d`; synthetic control scores candidate/grammar-matched/passive 144/144 each, independently audited false. Workflow run `43948485531` is referenced by manifest, but its jobs were not independently inspected in this investigation.
- Authenticated hosted BEAN adapter status/older recall/audit/compare/screen invoked; adapter revision `163f3e2815c4d6944345a0af78ae3e932041fdd3` is not Python Core. Heuristic evidence comparison reported insufficient evidence and is not a verifier.
- Confidentiality: only public source, synthetic calculations, no employer or private memory.

## Reproducible negative control

The actual `GoalCycle._claim` ranking formula is:

```python
score = -100 * priority + 8 / sqrt(1 + prior_attempts) + (
    2 * (successes - failures) / (successes + failures)
    if successes + failures else 0
)
```

The prior-attempt count is pooled by `action_type`, not by task, environment or hypothesis. The priority is clamped to integers 1..9. The novelty term is strictly positive and at most 8; the outcome term is between -2 and +2. Thus any priority-3 action scores above any priority-4 action, regardless of evidence or task relevance. This is provable from the bounds: worst priority 3 is greater than -302; best priority 4 is at most -390.

Executed independent Python 3 arithmetic on the published formula (not BEAN Core execution):

| Priority | Attempts | Success | Failure | Score |
| --- | ---: | ---: | ---: | ---: |
| 3 | 0 | 0 | 0 | -292.000000 |
| 3 | 1 | 1 | 0 | -292.343146 |
| 3 | 1 | 0 | 1 | -296.343146 |
| 3 | 100 | 100 | 0 | -297.203970 |
| 3 | 100 | 0 | 100 | -301.203970 |

This is not necessarily a defect: strict priority dominance can be an intentional policy. It **does** falsify any broad claim that observed failures alone can override priority to choose a lower-priority but more promising alternative. Current tests establish novelty selection among equal-priority actions; they do not establish task-specific feedback-driven choice across priority levels.

## Competing engineering approaches and falsifiers

1. **Preserve strict priority**, explicitly document that observed outcomes only break near-ties *within* a priority tier. Falsifier: product requirements or held-out goal tasks require a lower-priority action to win on outcome evidence. This has minimal regression risk.
2. **Bounded evidence-sensitive policy**, still retaining urgent priority constraints, but use task/context-specific success and failure receipts rather than global action-type counts. Falsifier: under matched budgets and fixed seeds, it fails to improve novel task outcomes versus the original selection rule, or violates an explicitly high-priority constraint. Requires new evaluation, not just a changed scoring constant.

## Minimum next experiment

Create two synthetic, explicitly registered *nonphysical* actions with controlled outcome probabilities that reverse across two task contexts. Generate balanced history and held-out contexts, compare unchanged selection to a task-conditioned candidate at equal action budget, and verify restart continuity of the same SQLite goal/run tables. Include a negative control with no predictive task context. Score independent actual outcomes, not merely ranking scores. A policy change is **not justified** until this experiment is run against real Core.

**HOURLY COGNITIVE SIMULATION NOT RUN**: repository checkout/executable Core unavailable in this runner; the GitHub connector reads and writes source but does not execute the Python Core. Specific missing wiring: a registered default digital experiment action and an accessible test runner that exercises GoalCycle with persisted Core feedback. The bounded Python calculation above is an independently reproducible policy counterexample, not a Core learning cycle.

No code behavior changed, no claims of AGI, consciousness, or learned advantage. Preserve generation 56 and its SHA chain.
