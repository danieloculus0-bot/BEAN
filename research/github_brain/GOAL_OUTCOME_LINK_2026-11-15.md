# Goal outcome receipt linkage, 2026-11-15

BEAN CONTEXT ACK v1. Read AGENTS.md, AI_GATEKEEPER.md, SOFTWARE_AUDIT_SKILL.md, OPEN_AGENT_PATTERNS_2026_11_14.md, canonical origin, GoalCycle, goal proposal state, tests and generation-49 manifest. Base main a5951d13892c5dda5d1e32918d071d731521e4a8. No open PRs returned by search at inspection. Prior PR #372 is merged; do not repeat that fix.

## Narrow deficiency and alternatives

GoalCycle already writes exact action results into the authoritative SQLite bean_goal_runs.result_json and emits compact event receipts, but the emitted receipt lacked a content digest linking it to the stored outcome. Downstream evidence processing could not verify which result bytes belonged to a particular goal event. Option A: duplicate full action output in the event stream, creating privacy/size risk and conflicting copies. Option B (selected): SHA-256 of the *exact persisted truncated JSON string* in the existing event receipt, preserving one authoritative result. Falsifier: digest does not match stored result after restart, or a failed action claims a nonexistent result.

## Change and verification status

Source: bean/runtime/goal_cycle.py; tests: bean/tests/test_goal_cycle.py. Adds result_sha256 for available persisted JSON and null for no result; two tests verify persistence, restart, non-replay and failure semantics. No new database, action registration, outbound calls, hardware behavior or memory reset. Exact branch head 797b7c82510262cf8b7c282ca9d4df63f4101b47 (before this handoff commit).

Generation 49 manifest: 49 boots, 1638 events, receipt 2a65419a6bad69ca61b079f3a3e566f55ba404e4e72b4af881bf33487a980399. Candidate, grammar-matched and passive each 144/144; memory-ablated 96/144. No strong-control advantage. Source evidence SHA 9c52c12e216026370aa1ee98c1fbae7704da3dc3. Manifest is historical; no new Core boot or checkpoint was performed.

**HOURLY COGNITIVE SIMULATION NOT RUN**: local checkout failed DNS resolution for github.com, and no authenticated GitHub workflow-dispatch action is available. New tests are committed but not verified executed; CI status must be checked on the exact final PR head. This is evidence plumbing, not an integrated cognitive cycle or independent learning improvement.

Next: run goal-cycle and complete Core regressions on exact head, review confidentiality and compatibility, merge only when checks and review permit. Then integrate a bounded real digital experiment into the default GoalCycle registry, with retrieval, hypothesis, action, outcome, revision, restart and matched controls.
