# Persistent ordered goal plans

`GoalStateEngine.propose_plan(session_uuid, plan_id, steps)` persists a host-authored sequence of 1..16 `GoalProposal` templates in the original `cognition_goal_proposals` table. No new database or upstream runtime is installed.

Use a stable ASCII plan ID. Each step receives a deterministic proposal ID. Repeating the same request, including in another session, returns the original step identities and current statuses. Changing an existing plan's content is rejected; propose a new plan ID for a revised approach. Existing attempts and failed plans remain inspectable.

`GoalCycle` releases step N only after step N-1 is completed. A higher priority does not override this dependency. Failed, interrupted, Unknown, unverified, missing or malformed prerequisites do not authorize the dependent action. Plans still require registered capabilities and the original approval fields. Unplanned goals retain their existing selection policy. Waiting steps do not consume the 100 executable-candidate scoring slots.

`cycle.plan_status(plan_id)` returns persisted per-step statuses and a summary. An unavailable or incomplete plan remains Unknown rather than completed. Creation is atomic: any rejected insert rolls back earlier steps. Partially missing history is not silently reconstructed.

This is ordered execution and continuation, **not autonomous plan invention, branching search or automatic failure repair**. A host can inspect failed evidence and propose a different plan without erasing the first. The default native experiment adapter remains unverified; an expected-answer match never by itself completes a prerequisite. The adapter now carries its actual `core_receipt_id` so the existing native feedback API can reference the exact inference.

## Executable integrated probe

```sh
python -m bean.evaluation.goal_plan_cycle --output /tmp/new-synthetic-plan-evidence
```

The output directory must be new. This host registers actual local learning, prediction/evaluation and feedback actions, then executes them through Core goals and the standard tick scheduler. It observes fictional development examples, retrieves the canonical event, induces and retains a native symbolic rule, restarts both existing SQLite owners, resumes the remaining plan, grades a withheld query, records feedback against the actual inference receipt, and applies retained knowledge to a second unseen query after reopening the reasoning journal.

The host oracle computes the declared synthetic task answer independently of the goal's deliberately false expected label. It is not independently audited world truth. Cold Core abstains, while a fixed grammar-matched sorter ties the retained rule. No general learning advantage is demonstrated. The host-created action wrappers belong to this evaluation; they are not newly enabled background handlers in `bean_run.py`.

`report.json` includes canonical events, goal decisions/results, hypothesis and inference identities, feedback, controls, source-file digests, database digests and a receipt hash. Linux/Windows CI uploads the complete synthetic databases and stage evidence. See [the execution record](../research/goal_plans/2026-11-19/README.md).
