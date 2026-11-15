# Native goal false-expectation negative control (2026-11-15)

BEAN CONTEXT ACK v1. Read AGENTS.md, AI_GATEKEEPER.md, SOFTWARE_AUDIT_SKILL.md, OPEN_AGENT_PATTERNS_2026_11_14.md, canonical origin, generation-50 manifest, prior goal-repetition handoff, actual native reasoning service, experiment adapter and merged real-Core goal regression. Enumerated 24 accessible owner repositories; no private content copied. Mainline PR #381 was merged. Current generation-50 receipt: c50540e6d773d2abe019edd4e342e5effe7aa30bc2e42264c9c0c11ed5302c44; 50 boots, 1,672 events, candidate/grammar-matched/passive 144/144. Manifest source SHA edbee2bcf0ebff97ed757bf36a4048c316f722af. No fresh checkpoint generation inferred.

## Hypothesis and falsifier

A host-supplied expected answer is not a truth oracle. Existing integration tests cover a correct expected answer and cold abstention, but not a deliberately false expected answer after actual local rule learning. New disposable regression trains a real NativeReasoningService with three synthetic examples, then gives GoalCycle an intentionally wrong expected answer on a withheld query. Independent digit-sorting oracle yields KJL; false expectation JKL. Test requires observed answer KJL, mismatch flag, explicit unverified outcome, and persistence without replay after reopening both existing SQLite owners. It must fail if GoalCycle or the adapter promotes the host expectation to independent truth, or if restart discards the negative result.

Alternatives: (1) add a new independent-oracle framework, or (2) extend the existing real-Core test surface with a negative control. Chose (2) to avoid new stores, frameworks or untested trust assumptions. This does not establish generalization or AGI.

## Evidence and limitations

New test source commit 9576eb8fd743838e137bfd55e3a8fae6c15056e6. GitHub file was written through authenticated connector. Local checkout attempt failed with DNS resolution for github.com; **no executable pytest run or fresh cognitive simulation occurred**. Exact-head CI is pending. Do not merge before exact-head green tests, review, and compatibility/privacy check. No Core production behavior, public-safe checkpoint, private memory, hardware or scheduler changed.

Next: run `python -m pytest bean/tests/test_real_core_false_expectation.py bean/tests/test_real_core_goal_experiment.py -q`, inspect exact-head CI, repair failures, then build a multi-seed equal-budget evaluation with independent oracle and grammar-matched controls. Retain negative results.
