# BEAN General-Purpose Reasoning Layer

## Purpose

BEAN can run without a physical body and without owning the user interface, workflow engine, database, or action layer of the project that uses it.

The general deployment model is simple:

- The host project owns its domain.
- The host sends BEAN observations, events, evidence, and reasoning requests.
- BEAN stores continuity, builds bounded context, calls a configured reasoning provider, filters the result, and keeps the receipts.
- BEAN returns a proposal or analysis record.
- The host decides whether any action is permitted and how that action is executed.

This keeps the reusable intelligence in one place while allowing every project to keep its own UI, permissions, domain rules, and execution code.

## Design rule

**BEAN reasons. The host acts.**

That rule is the primary integration boundary.

A BEAN reasoning result is not an instruction to execute. It is a structured proposal with traceable context, confidence, uncertainties, evidence references, candidate steps, risk flags, and filter results.

## What is already reusable

The existing repository already contains the core pieces required for a host-neutral reasoning layer:

- SQLite memory and session continuity.
- Append-only event history.
- Identity, capability, boundary, and supervisor records.
- World claims and explicit uncertainty.
- Wisdom traces and relationship summaries.
- Hypothesis discipline.
- Bounded reasoning context packets.
- Provider adapters.
- Structured response parsing.
- Proposal filters.
- Proposal persistence.
- Supervisor-review requirements.
- Supervised self-optimization records.
- Runtime proof and smoke tests.

The reasoning provider remains replaceable. BEAN identity and durable memory do not live in model weights.

## Logical architecture

```text
+-------------------------------+
| Host project                  |
| UI / workflow / sensors / API |
| domain data / permissions     |
+---------------+---------------+
                |
                | normalized observation, event, request
                v
+-------------------------------+
| BEAN ingress / host adapter   |
+---------------+---------------+
                |
                v
+-------------------------------+
| Persistent memory             |
| sessions / events / claims    |
| boundaries / hypotheses       |
+---------------+---------------+
                |
                v
+-------------------------------+
| Bounded context builder       |
| record IDs retained           |
+---------------+---------------+
                |
                v
+-------------------------------+
| Reasoning provider adapter    |
| mock / OpenAI / future        |
+---------------+---------------+
                |
                v
+-------------------------------+
| Parser + proposal filters     |
+---------------+---------------+
                |
                v
+-------------------------------+
| Stored proposal + audit trail |
+---------------+---------------+
                |
                | reviewed result
                v
+-------------------------------+
| Host policy / action layer    |
+-------------------------------+
```

No direct provider-to-action path belongs in this architecture.

## Current Python integration surface

The current reasoning engine is available from:

```python
from bean.reasoning import ReasoningEngine
```

A minimal embedded smoke integration can use the existing memory and session APIs:

```python
from bean.memory.store import init_store
from bean.memory.identity import bootstrap_identity
from bean.memory.session import begin_session, end_session
from bean.memory.event_logger import log_event, EventType, Source
from bean.reasoning import ReasoningEngine

init_store("./data/bean_memory.db")
bootstrap_identity()

session_uuid = begin_session()

event_id = log_event(
    session_uuid=session_uuid,
    event_type=EventType.OBSERVATION,
    summary="Host project submitted a condition for analysis.",
    source=Source.SYSTEM,
    data={
        "host": "example_project",
        "object_id": "sample-001",
        "evidence": {"state": "example"},
    },
)

engine = ReasoningEngine()

result = engine.run(
    session_uuid=session_uuid,
    request_type="analysis",
    source_event_id=event_id,
    adapter_name="mock",
)

print(result)

end_session(session_uuid)
```

The mock adapter should remain the default for smoke testing because it keeps tests offline and deterministic.

## Configured reasoning provider

The current OpenAI adapter reads configuration from environment variables:

```text
OPENAI_API_KEY
BEAN_OPENAI_MODEL
BEAN_OPENAI_BASE_URL
```

A configured run uses:

```python
result = engine.run(
    session_uuid=session_uuid,
    request_type="analysis",
    source_event_id=event_id,
    adapter_name="openai",
)
```

Provider output still passes through BEAN parsing, filters, persistence, and review requirements.

## Recommended host event envelope

This is the recommended host-neutral envelope for future adapter work. It is an integration contract, not a claim that a network endpoint already exists.

```json
{
  "host": "project_name",
  "event_type": "observation",
  "object_id": "domain-object-id",
  "summary": "Human-readable statement of what happened.",
  "evidence": {
    "source": "host_database",
    "values": {}
  },
  "tags": ["domain", "process"],
  "requested_reasoning": "analysis"
}
```

The adapter should translate the envelope into canonical BEAN event types rather than allowing arbitrary event strings into the event spine.

## Recommended reasoning result contract

The host should not have to query internal BEAN tables directly. A thin adapter should eventually expose a stable result shaped around the existing reasoning engine:

```json
{
  "success": true,
  "proposal_id": "proposal_xxx",
  "request_id": "request_xxx",
  "response_id": "response_xxx",
  "filter_passed": true,
  "requires_supervisor_review": true,
  "motion_command_generated": false,
  "memory_written": false
}
```

A host-facing adapter may add the parsed proposal body, but should preserve the BEAN record IDs so every answer can be traced back to its packet, request, response, proposal, and evidence.

## Deployment patterns

### 1. Embedded Python

Best first deployment for another Python application.

The host imports BEAN directly and keeps BEAN memory in a host-specific data directory.

Advantages:

- Lowest integration overhead.
- No network service required.
- Easy debugging.
- Direct access to typed Python interfaces.

Constraint:

- BEAN's current memory store is a process-level singleton. Treat one BEAN store as one reasoning service per process until that layer is refactored.

### 2. Local sidecar process

Best when the host is written in another language or should not import BEAN internals.

The existing runtime already supports file-inbox behavior. A general sidecar adapter can evolve from that pattern:

```text
host writes request
      |
      v
BEAN sidecar processes request
      |
      v
BEAN writes result / host reads result
```

This provides process isolation while keeping deployment local.

### 3. Network reasoning service

Target pattern for multiple applications or machines.

This should be built as an adapter around the BEAN core, not by moving memory or reasoning rules into a web framework.

Recommended service responsibilities:

- Authentication.
- Host identity.
- Request normalization.
- Rate and concurrency control.
- Mapping host events to canonical BEAN events.
- Returning proposal IDs and structured results.

The service should not become the source of truth. SQLite and BEAN records remain the durable reasoning history for a single-node deployment. A future multi-node design can replace the persistence implementation behind a stable BEAN interface.

## Project isolation

A general BEAN deployment needs explicit isolation between host projects.

Do not casually mix project data into one context packet.

The host adapter should eventually support at least:

- host/project identifier
- namespace or tenant identifier
- permitted context categories
- permitted capabilities
- project-specific boundaries
- project-specific data retention policy

Until namespacing exists in the schema, the safest deployment is one BEAN database per independent host project.

## Embodiment is optional

The current repository retains body-oriented history because BEAN began as a brain-first embodiment project.

General use changes the architectural assumption:

```text
BEAN != robot
BEAN != UI
BEAN != LLM
BEAN != host application

BEAN = persistent reasoning and continuity layer
```

A body is one possible host.

A desktop application is one possible host.

A manufacturing system is one possible host.

A maintenance system is one possible host.

A research agent is one possible host.

The reasoning architecture should work without knowing which one it is attached to.

## Implementation sequence for this branch

### Phase 1: Documentation and boundary definition

- Reframe README around body-optional reasoning.
- Publish this host-neutral deployment guide.
- Preserve the hard proposal-versus-action boundary.

### Phase 2: Thin host adapter

Create a small adapter layer that:

- initializes a host-specific BEAN data store
- begins and closes a reasoning session
- records canonical host events
- invokes `ReasoningEngine`
- returns stable proposal metadata
- never executes host actions

Suggested package:

```text
bean/integration/
    __init__.py
    reasoning_layer.py
    host_event.py
```

### Phase 3: Host profiles

Separate persistent BEAN core identity from deployment-specific details.

A host profile should describe:

- host name
- host type
- available capabilities
- execution boundaries
- permitted data sources
- project-specific context
- whether any physical output exists

This removes Jetson-specific assumptions from projects that do not have a body.

### Phase 4: Namespaced context

Add project/host scoping to events, claims, hypotheses, reasoning packets, and proposals.

The context builder must never pull unrelated project records merely because they share a database.

### Phase 5: Stable adapter contract

Add tests that prove:

- identical host input produces a valid reasoning request
- context is bounded
- record IDs are retained
- provider failure produces a stored safe result
- reasoning never directly executes an action
- one project's context cannot leak into another project
- mock-provider tests require no network

### Phase 6: Deployment wrappers

Package the same core for:

- embedded Python
- local sidecar
- Windows service
- Linux service
- optional network API

The wrappers should be boring. The intelligence belongs in BEAN, not in five different deployment shells.

## Minimal acceptance criteria

A project can claim BEAN reasoning-layer integration when all of the following are true:

- The host can submit a real domain observation.
- The observation is stored as a canonical BEAN event.
- A bounded context packet is created.
- The included record IDs are inspectable.
- A reasoning provider returns a structured response.
- The response becomes a stored proposal.
- Proposal filters run.
- The host receives a proposal identifier and review status.
- No provider output directly executes a host action.
- A later audit can reconstruct what BEAN saw and what it proposed.

## Failure philosophy

A reasoning layer should fail boringly.

If the provider is unavailable, parsing fails, context is incomplete, or a filter rejects the proposal:

- record the failure
- preserve the evidence
- return an explicit status
- do not invent a successful action
- do not silently bypass the reasoning boundary

The point of BEAN is not to always produce an answer. The point is to maintain useful continuity without lying about what happened.

## Why this matters

Most project-specific logic systems become islands. They know their own tables, screens, and rules but lose intelligence when a problem crosses the boundary into another system.

BEAN is intended to hold the reusable part:

- memory
- uncertainty
- evidence discipline
- reasoning
- traceability
- proposal filtering
- continuity

That lets each host remain specialized without rebuilding the same brain every time.
