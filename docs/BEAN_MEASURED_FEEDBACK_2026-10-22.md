# BEAN measured-outcome learning, October 22, 2026

BEAN Core now accepts **matched evaluator results** as a feedback source for
the original SpongeTD learner. This is a real Q update, not a simulated
counter: a signed performance change feeds TD learning and a checkpoint saves
the new Q table.

## One tested decision/outcome cycle

With \`BEAN_LEARNING_DB\` configured, the existing runtime inbox supports:

1. \`learning_choose\`: select an action from a caller-supplied list of legal
   actions, recording state and episode ID. This does not take the action.
2. Run the selected action in an actual application or evaluation harness.
   Compare baseline and candidate on the **same test cases**.
3. \`learning_evaluated_feedback\`: send the episode ID and a \`RewardTrial\` with
   \`experiment\`, \`metric\`, \`condition_id\`, \`baseline_run\`,
   \`candidate_run\`, \`baseline\`, \`candidate\`, \`direction\` ("higher"
   or "lower"), \`matched_cases\`, \`expected_cases\`,
   \`evaluation_sha256\` (SHA-256 lowercase), \`evidence_ref\` (HTTPS URL),
   and \`evidence_kind\` ("synthetic" or "measured").
4. \`learning_reward_history\`: returns saved per-receipt records, including
   negative rewards, Q step, trial and evidence link.

Incomplete comparisons, reused evaluation hashes, same-run comparators and
fewer than 30 matched cases yield **no learning credit**. An exact tie gives
a legitimate zero reward and is recorded as such. Regressions give negative
rewards. All eligible evaluations checkpoint immediately; durable receipt
and compressed Q checkpoint are committed in the same SQLite transaction.
This closes the crash window for *evaluated* feedback but does not change
the legacy raw \`learning_feedback\` path, which still requires explicit
checkpoints.

The module reuses \`bean/optimization/scoreboard_context.py\` from the earlier
PR #141 experiment, not a new scoring formula.

## Limits

The source evidence hash and HTTPS URL are supplied by the caller. **This is
not independently authenticated evidence** without a trusted grader;
receipts are marked as such. Core's existing reasoning engine emits proposals
for supervisor review; it does not inherently contain a ground-truth
outcome grader. A proposal passing structural filters is **not** fed back
as a positive reward. No host adapter, AIscend wallet, Axiom or EZ-FAIR
workflow is silently wired to the evaluator.

Reproduce: \`python -m unittest bean.tests.test_measured_feedback -v\`.

The original Lab027 Q-learning verification and PR #141 reward tests remain
separate source receipts. New branch CI is required for this integration.
