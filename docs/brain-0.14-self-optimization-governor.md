# Brain 0.14 - Supervised Self-Optimization Governor

Purpose: allow BEAN to identify limitations and propose improvements to its software, workflow, sensors, or future body without granting it an automatic self-modification or physical-action path.

## Core rule

```text
BEAN may observe, compare, propose, and learn from outcomes.
BEAN may not execute its own improvement proposal.
```

The governor stores structured proposals and supervisor decisions. Approval changes the proposal record only. A separate, explicitly controlled human or sandbox process must perform any experiment, code change, configuration change, or hardware work.

## Proposal pipeline

1. Identify a recorded limitation, failure, inefficiency, or unmet goal.
2. Describe the proposed change and at least one alternative.
3. Record expected benefit, cost, risk, evidence, validation method, and rollback plan.
4. Store the proposal with `proposal_only` execution permission.
5. Require a supervisor review before sandbox or human execution is allowed.
6. Record implementation, validation, rollback, or supersession as evidence for later proposals.

## Hard invariants

- No proposal method performs code changes, shell commands, network writes, actuator commands, or hardware movement.
- Every proposal starts as `proposal_only`.
- Every proposal requires a validation plan and rollback plan.
- Approval is a record of permission, not execution.
- Physical embodiment proposals remain motion-disabled.
- The LLM may help draft a proposal, but it does not own the decision or the execution path.
- GRIP and active safety boundaries remain authoritative through every developmental change.

## Persistent records

Brain 0.14 creates:

```text
optimization_proposals
optimization_reviews
```

Each proposal records:

- problem statement
- proposed change
- target layer and proposal type
- expected benefit and cost
- risk level
- evidence references and alternatives
- validation plan
- rollback plan
- status and execution permission
- supervisor review history

## Review decisions

```text
approve_sandbox
approve_human
request_revision
defer
reject
```

The resulting execution permissions are intentionally narrow:

```text
proposal_only
sandbox_test_only
human_execution_only
```

None of these permissions creates an executor inside the governor.

## Example

```python
from bean.optimization import init_self_optimization

optimizer = init_self_optimization()
proposal = optimizer.create_proposal(
    session_uuid=session_uuid,
    title="Compare mobile base configurations",
    problem_statement="The future body configuration has not been selected.",
    proposed_change="Compare a rocker-bogie base with articulated legs in simulation.",
    target_layer="embodiment",
    proposal_type="experiment",
    expected_benefit="Choose a body using measured evidence.",
    expected_cost="Simulation and prototype design time.",
    risk_level="medium",
    validation_plan="Score terrain access, energy use, stability, cost, and failure modes.",
    rollback_plan="Retain the current no-motion configuration.",
)
```

The returned proposal explicitly reports:

```text
auto_executed = false
motion_command_generated = false
requires_supervisor_execution = true
```

## Test

```bash
python3 bean/tests/test_self_optimization_governor.py
```

## Next integration steps

1. Add runtime inbox commands for creating, listing, reviewing, and closing improvement proposals.
2. Add an optimization summary to bounded reasoning context packets.
3. Add proposal and review counts to runtime proof.
4. Link proposals to events, hypotheses, reasoning proposals, and measured experiment outcomes.
5. Add a separately permissioned sandbox runner that cannot reach physical motion drivers.
6. Do not consider autonomous code or hardware execution until the proposal and rollback trail is boringly reliable.
