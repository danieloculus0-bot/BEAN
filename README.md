# BEAN

**Behavior Enabled Avatar Node**

🌱 **[Meet BEAN on the live website](https://danieloculus0-bot.github.io/BEAN/)** · [Run the offline demo](docs/GETTING_STARTED.md) · [Contribute or test](CONTRIBUTING.md) · [Share BEAN](docs/LAUNCH_KIT.md)

**Universal persistent reasoning for systems that need to remember, doubt, connect, learn, and keep receipts.**

BEAN is a persistent reasoning architecture. It is designed to carry state across time, evaluate evidence, preserve uncertainty, detect contradictions, connect events, form hypotheses, use external reasoning models when useful, learn from outcomes, and retain why a conclusion or proposal existed in the first place.

BEAN can operate as a standalone reasoning system, as a logic layer inside another application, as a service shared by multiple systems, or as the reasoning core of an embodied machine.

An LLM is not BEAN. A robot is not BEAN. A user interface is not BEAN.

Those are things BEAN can use.

**BEAN is the persistent logic that remains.**

## Try BEAN and verify its claims

[![BEAN full core regression](https://github.com/danieloculus0-bot/BEAN/actions/workflows/brain-smoke.yml/badge.svg)](https://github.com/danieloculus0-bot/BEAN/actions/workflows/brain-smoke.yml)

**New to BEAN?** Start with the [offline quickstart](docs/GETTING_STARTED.md), [live project website](https://danieloculus0-bot.github.io/BEAN/), or [research evidence index](docs/experimental-research-index-2026-10.md).

The current host-neutral API can record a fictional observation in a disposable local SQLite database and produce a stored, review-required proposal using a **mock** provider:

```bash
git clone https://github.com/danieloculus0-bot/BEAN.git
cd BEAN
python -m pip install psutil
python -m examples.quickstart_reasoning
```

This is an executable architecture demonstration, **not** a demonstration of trained-model intelligence or unsupervised autonomy.

**Want to follow BEAN's development?** Visit the [mint-green site](https://danieloculus0-bot.github.io/BEAN/#community), star/watch the repo if you find it useful, or [report what you can reproduce](CONTRIBUTING.md). The [launch kit](docs/LAUNCH_KIT.md) contains shareable, evidence-checked announcements and the independent test references.  The [BEAN AI Bridge](https://github.com/danieloculus0-bot/BEAN-AI-Bridge-) provides separate generic ERP/evidence adapters and synthetic replay. See the [public discovery and GitHub Pages activation checklist](docs/PUBLIC_DISCOVERY_LAUNCH.md). Source visibility alone does not provide a redistribution license.

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
| RAM-backed BEAN Watcher, configurable recall and N/A-aware source status | Implemented as opt-in local report adapter |
| Host-neutral evidence/uncertainty bridge and scheduled independent-source review | Implemented, Bridge smoke-verified (host-attested evidence; opt-in) |
| Generic host integration | Active development |
| Physical embodiment | Optional future host |

BEAN is developed against real host projects and changing domains rather than being designed as a sealed demo. The architecture is expected to keep evolving as those deployments expose better abstractions.

### Core ↔ Bridge evidence-continuity smoke

A [host-neutral evidence cycle](docs/EVIDENCE_BRIDGE_READINESS.md) connects typed
external source observations to BEAN Core's actual SQLite memory, uncertainty
garden and epistemic audits. A host can optionally schedule **bounded**
read-only review using BEAN's existing durable TaskEngine. Revisions,
contradictions and restart continuity are verified using a separate
[Bridge cross-platform smoke branch](https://github.com/danieloculus0-bot/BEAN-AI-Bridge-/tree/smoke/core-evidence-contract-20261010).
A declared source or verification ID is **host-attested**, not independent
authentication or proof of truth. No new physical or financial action is enabled.

## Research experiments and published findings

BEAN is being evaluated through **reproducible, isolated experiments** in evidence reliability, uncertainty reasoning, model revision, confidence-directed search, and lifelong empirical learning. The research code remains on experimental branches; documentation here does **not** mean those features are merged or production-ready.

**[Read the research index: findings, limitations, source branches, test runs and downloadable output artifacts](docs/experimental-research-index-2026-10.md)**

| Experiment | View experiment and output |
| --- | --- |
| **Evolution and source reliability** | [Lab 001 research branch](https://github.com/danieloculus0-bot/BEAN-AI-Bridge-/tree/experiment/bean-evolution-lab-20261009) · [Simulation report and tests](https://github.com/danieloculus0-bot/BEAN-AI-Bridge-/actions/runs/37995651207) |
| **Evidence Intelligence / competing hypotheses** | [Lab 003 findings](https://github.com/danieloculus0-bot/BEAN-AI-Bridge-/blob/experiment/bean-evidence-intelligence-20261010/experiments/evolution_lab/LAB003_FINDINGS.md) · [JSON/test output](https://github.com/danieloculus0-bot/BEAN-AI-Bridge-/actions/runs/38028778085) |
| **Learning when previous trust becomes wrong** | [Lab 004 findings](https://github.com/danieloculus0-bot/BEAN-AI-Bridge-/blob/experiment/bean-model-revision-lab004-20261010/experiments/evolution_lab/LAB004_FINDINGS.md) · [Cross-platform results](https://github.com/danieloculus0-bot/BEAN-AI-Bridge-/actions/runs/38029372008) |
| **Confidence-directed search and page reranking** | [Lab 005 source](https://github.com/danieloculus0-bot/BEAN-AI-Bridge-/tree/experiment/bean-confidence-search-lab005-20261010/experiments/search_lab) · [Ranking results](https://github.com/danieloculus0-bot/BEAN-AI-Bridge-/actions/runs/38029876766) |
| **Nonterminal learning and cross-abstraction relevance** | [Lab 006 research record](https://github.com/danieloculus0-bot/BEAN-AI-Bridge-/blob/experiment/bean-epistemic-continuity-lab006-20261010/experiments/search_lab/LAB006_CONTINUOUS_LEARNING.md) · [100-test run and output](https://github.com/danieloculus0-bot/BEAN-AI-Bridge-/actions/runs/38030419931) |

**Key result:** Empirical conclusions can be temporarily settled without blocking future observations. In the synthetic studies, confidence-driven investigation improved some outcomes but also exposed failure modes: stale learned trust, source-echo duplication, inspection expense, and regressions under changed conditions. **These are not live-browser benchmarks or evidence of AGI.** Exact caveats and comparative metrics are in the [research index](docs/experimental-research-index-2026-10.md).

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

## BEAN Watcher

Native BEAN Watcher connects authorized normalized report exports to BEAN's working memory and append-only event ledger. Reports lacking an explicit completeness assertion, required metrics or evidence references show **N/A**, not zero. Change events wake it early; a configurable recall interval still rechecks unchanged sources. Historical values are retained separately, never passed off as current results. See [Watcher contract and example](docs/bean-watcher-contract.md). No live ERP credentials are included.

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

## Evidence-pinned peer review and safe code drafts (opt-in)

The [peer development protocol](docs/bean-peer-development-lab017.md) provides reusable Python objects for **immutable, digest-linked selector/builder/validator review messages** and *disposable* code-change proposals pinned to a source SHA and original content hash. It detects reordered receipts, orphan test results and modified source before creating a preview. No module automatically runs generated code, signs off a change, merges branches or grants production permissions.

`from bean.optimization.peer_dialogue import PeerDialogue, PeerMessage` and `from bean.optimization.code_candidate import draft_candidate` expose these review-only primitives. SHA256 integrity is not identity verification: the host must independently check CI results, repository access and trusted evidence origins. See [regression tests](bean/tests/test_peer_dialogue_lab017.py).

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

## Opt-in durable task behaviors

The native BEAN task engine runs only when a trusted local `BEAN_TASK_CONFIG` file is supplied. It persists bounded, named tasks and execution receipts in the existing SQLite memory store, marks interrupted or unverifiable work as **unknown / needs review**, and will not silently retry unknown side effects. The current allowlist contains only local integrity checks, report Watcher inspections, inner-weather updates, and relationship-summary maintenance; no shell, arbitrary Python, network effects, trades, email, or motors. The scheduler is **disabled by default**, and its human-review workflow and unattended-service readiness are still future work. See [durable-task contract and configuration](docs/bean-durable-tasks-lab011.md).

## Offline capability exam and non-fabricated baselines

The optional [BEAN evidence-first entrance exam](docs/bean-entrance-exam-lab012.md) provides seven reproducible fictional cases for unknown handling, verified citations, corrections, read-only probe requests, and limited cross-domain transfer. The bundled `MockLLMAdapter` is expected **not to pass** these capability criteria; fixture test doubles validate the examiner itself, never BEAN intelligence. Real capability improvements must be measured on independent unseen data with source audits. Run `python -m bean.evaluation.entrance_exam` to reproduce the honest baseline without network, private inputs, or hardware.

## Embedded host-neutral reasoning interface

`from bean.integration import BeanReasoningLayer` exposes a small Python lifecycle interface that records host observations, builds bounded reasoning context, and returns **review-required, stored proposals**, not actions. The mock provider works offline and a host must own permissions, execution, project isolation and authenticated input. Use **one BEAN memory store per host process**, avoiding concurrent use of the process-level singleton. See [host-neutral reasoning guide](docs/general-reasoning-layer.md). This is an optional API, not a claimed general intelligence system.

## Offline research evaluation harnesses (not deployed intelligence)

Core includes opt-in synthetic evaluation modules for [supervised source calibration](docs/bean-composite-growth-lab013.md), [read-only investigation and restart retention](docs/bean-investigation-retention-lab014.md), and [symbolic LLM-style provider emulation](docs/bean-simulated-llm-lab015.md). These run only when invoked, use fictional data and isolate their SQLite state. **Fixture gains do not demonstrate neural-model learning, open-ended self-improvement or production autonomy.** The incomplete hosted Lab016 remains isolated; no real hosted-model capability has been promoted. Their purpose in `main` is reproducible falsification of future changes.
