# BEAN

**Behavior Enabled Avatar Node**

**Universal persistent reasoning for systems that need to remember, doubt, connect, learn, and keep receipts.**

BEAN is a persistent reasoning architecture. It is designed to carry state across time, evaluate evidence, preserve uncertainty, detect contradictions, connect events, form hypotheses, use external reasoning models when useful, learn from outcomes, and retain why a conclusion or proposal existed in the first place.

BEAN can operate as a standalone reasoning system, as a logic layer inside another application, as a service shared by multiple systems, or as the reasoning core of an embodied machine.

An LLM is not BEAN. A robot is not BEAN. A user interface is not BEAN.

Those are things BEAN can use.

**BEAN is the persistent logic that remains.**

## What BEAN does

Most software starts each decision with whatever state the application explicitly hands it. Most AI systems are extremely capable reasoners but are only as good as the context, evidence, memory, boundaries, and feedback around the current request.

BEAN exists to supply that missing structure.

    observations / events / evidence
                 |
                 v
       persistent BEAN state
                 |
       +---------+---------+
       |                   |
       v                   v
    deterministic       optional reasoning
    logic / rules        providers / models
       |                   |
       +---------+---------+
                 |
                 v
        hypotheses / proposals
                 |
                 v
      policy + capability boundaries
                 |
                 v
       host / service / effectors
                 |
                 v
              outcomes
                 |
                 +------> BEAN

The loop matters more than any one model. A stronger model can improve BEAN's available reasoning horsepower, but continuity, evidence, contradiction handling, uncertainty, history, policy, and learning do not disappear when the model changes.

## One architecture, several lives

BEAN is intentionally body-optional and provider-optional.

- **Standalone:** BEAN can maintain its own runtime, memory, world state, reasoning cycle, and bounded capabilities.
- **Embedded:** another project can use BEAN as its persistent reasoning and continuity layer.
- **Service:** multiple tools or applications can submit events and reasoning requests to the same governed BEAN instance.
- **Embodied:** sensors become inputs and physical systems become effectors. The body is a host, not the identity.
- **Multi-model:** language models, deterministic engines, local models, or future reasoning systems can be treated as replaceable cognitive resources rather than BEAN itself.

Execution is always a separate architectural concern from reasoning. In an embedded deployment the host may own execution. In a standalone or embodied deployment, explicit effectors and policy boundaries may own execution. A reasoning provider never gets a magical direct wire to the outside world.

## Core behavior

BEAN is being built around a small set of durable behaviors:

- Persistent local continuity instead of disposable prompt state.
- Evidence lineage and traceable context.
- Versioned self and world claims.
- Explicit uncertainty instead of forced certainty.
- Hypotheses that remain hypotheses until evidence changes them.
- Contradiction detection, review, and repair.
- Significance and attention so everything is not treated as equally important.
- Associative memory and wisdom traces without pretending associations are facts.
- Relationship and trust models grounded in evidence.
- Bounded context construction for external reasoning providers.
- Structured proposals that can be inspected before anything acts on them.
- Outcome history that can change future trust, assumptions, and reasoning.
- Self-improvement proposals with explicit benefit, cost, risk, validation, and rollback.

## Current implementation

| Capability | State |
|---|---|
| Persistent SQLite memory, sessions, events, continuity records | Implemented |
| Versioned identity, boundaries, capabilities, self/world claims | Implemented |
| Significance, surprise, preferences, drives, goals, consolidation | Implemented |
| Epistemic guard, contradiction court, falsification | Implemented |
| Uncertainty garden, hypotheses, evidence levels, review records | Implemented / evolving |
| Wisdom traces, repair records, loop signatures | Implemented / evolving |
| Relationship history and evidence-weighted trust | Implemented / evolving |
| Bounded reasoning context and replaceable provider adapters | Implemented / evolving |
| Structured reasoning proposals and proposal persistence | Implemented / evolving |
| Supervised self-optimization records and rollback planning | Implemented / evolving |
| Standalone runtime, inbox, system monitoring, durable state | Implemented |
| Generic host integration | Active development |
| Physical embodiment | Optional future host |

BEAN is developed against real host projects and changing domains rather than being designed as a sealed demo. The architecture is expected to keep evolving as those deployments expose better abstractions.

## Origin, quickly

BEAN began as the operating brain for a future robot.

That immediately forced a harder question than locomotion: what should persist when the model changes, how should evidence be remembered, how should uncertainty survive, how should contradictions be handled, and how can a system improve without rewriting its own history?

The reasoning architecture became more useful than the original body constraint. BEAN therefore evolved from **a brain for one robot** into **a universal persistent reasoning architecture that can inhabit software, workflows, services, machines, or a body**.

The robot is still invited. It just no longer gets to define the project.

## Operating principles

    Evidence before belief.
    Preserve uncertainty until evidence resolves it.
    Contradictions are information, not inconveniences.
    Memory is continuity, not identity theater.
    The LLM is a reasoning resource, not BEAN's identity.
    Reasoning and execution remain separable.
    Capabilities must be explicit.
    Actions must be attributable.
    Outcomes must come back into the system.
    Improvement should be inspectable and reversible.
    Never invent success.
    Keep receipts.

## Why this exists

Powerful reasoning should not require a giant organization, a giant software stack, or a giant consulting budget.

A small manufacturer, an autonomous research project, a quality system, a maintenance platform, a market agent, or a future machine can all benefit from the same underlying thing: a system that remembers what happened, understands what it knows, admits what it does not know, connects consequences across time, and gets less stupid from experience.

That is the job.

**BEAN does BEAN.**

## Repository orientation

The current codebase includes persistent memory, cognition, world/self modeling, epistemic controls, reasoning adapters, hypotheses, wisdom, relationships, self-optimization, runtime services, and early embodiment support.

One current standalone deployment target is the NVIDIA Jetson Orin Nano Super Developer Kit because embodiment was BEAN's original proving ground. Jetson support remains useful, but it is a deployment profile rather than the definition of the architecture.

Persistent runtime data should remain outside the repository:

    BEAN_DB_PATH=/home/bean/bean_data/bean_memory.db
    BEAN_INBOX_DIR=/home/bean/bean_data/inbox

Jetson installation:

    bash install/jetson_brain_install.sh
    bash scripts/bean_doctor.sh

For non-Jetson development:

    BEAN_ALLOW_NON_JETSON_INSTALL=1 bash install/jetson_brain_install.sh

## Development direction

The near-term work is organizational as much as additive: make BEAN's persistent reasoning primitives easier to understand, isolate from old embodiment assumptions, and reuse without copying logic into every new project.

Priority direction:

1. Keep the reasoning core independent of any one body, UI, model provider, or domain.
2. Stabilize event, evidence, context, proposal, outcome, capability, and policy contracts.
3. Make project-specific behavior adapters around the core instead of forks of the core.
4. Preserve project-local memory while supporting deliberately shared context where appropriate.
5. Turn live outcomes into better calibrated trust, hypotheses, causal understanding, and improvement proposals.
6. Keep embodiment as a first-class host without allowing embodiment to become BEAN's identity.

BEAN is not finished. It is also no longer waiting for a body to become useful.
