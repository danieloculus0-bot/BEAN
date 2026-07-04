# BEAN

**Behavior Enabled Avatar Node**

BEAN is a brain-first Synthetic Intelligence research platform for future embodiment on an NVIDIA Jetson Orin Nano Super Developer Kit.

Current focus: **build the brain first, keep motion disabled, keep receipts.**

## Current GitHub status

| Area | Status | Notes |
|---|---:|---|
| Memory core | Implemented | SQLite memory, sessions, identity, event log, boundaries, reflections, curiosity, continuity records. |
| Body registry and motion safety | Implemented | Simulator path exists. Real hardware motion remains disabled. |
| Runtime loop | Implemented | Tick handlers, file inbox, system monitor, clean shutdown. |
| Self/world model | Implemented | Versioned claims, uncertainty records, supersession model. |
| Cognition core | Implemented | Significance, surprise, preference, drives, goals, consolidation. |
| Possibility states | Implemented | Coherence windows, entropy source, state collapse history. |
| Brain 0.2 install candidate | Implemented | Installer, env template, service files, backup/status tools, smoke test. |
| Brain 0.3 epistemic immune system | Implemented | Claim guard, contradiction court, falsification engine. |
| Brain 0.4 dreaming and uncertainty | First cut | Dream artifacts and uncertainty garden. |
| Brain 0.5 dignity, inner weather, autobiography | First cut | Identity hygiene, pressure reports, developmental timeline. |
| Brain 0.6 maintenance/runtime integration | First cut | Manual inbox commands expose maintenance systems. |
| Brain 0.7 relationship and trust | First cut | Evidence-based supervisor interaction history and trust scoring. |
| Brain 0.8 runtime proof and hardening | First cut | Runtime proof command, smoke runner, durable relationship ingestion watermark. |
| Brain 0.9 wisdom module | First cut | Trigger matching, pressure deltas, meaning frames, traces, repair records, loop signatures. |
| Brain 0.11 OpenAI-preferred reasoning | First cut | Context packets, prompt contract, mock provider, real stdlib OpenAI provider, parser, proposal filters, proposal store. |
| Brain 0.13 hypothesis discipline | First cut | Claim type discipline, evidence levels, hypothesis storage, review records, speculation summary. |
| Boot readiness | First cut | Temp-DB boot probe for fresh BEAN OS/reformat checks. |
| Brain-layer inbox commands | First cut | Wisdom, reasoning, and hypothesis commands are wired into runtime inbox. |
| Hardware motion driver | Not enabled | Real servo movement remains disabled. No direct LLM-to-actuator path. |

## Quick start on Jetson

```bash
bash install/jetson_brain_install.sh
bash scripts/bean_doctor.sh
```

Manual checks:

```bash
bash scripts/bean_boot_ready.sh --temp
bash scripts/run_brain_smoke_tests.sh
python3 bean/tests/test_boot_readiness.py
python3 bean/tests/test_wisdom_module.py
python3 bean/tests/test_reasoning_layer.py
python3 bean/tests/test_speculative_logic.py
```

Memory should stay outside the repo:

```text
BEAN_DB_PATH=/home/bean/bean_data/bean_memory.db
BEAN_INBOX_DIR=/home/bean/bean_data/inbox
```

Before starting the service after a reformat, run:

```bash
source /etc/bean/bean.env
bash scripts/bean_boot_ready.sh --db "$BEAN_DB_PATH"
```

## Core rules

```text
Evidence before belief.
Memory before identity claims.
Body model before motion.
Safety before autonomy.
Possibility before forced certainty.
Doubt before confidence.
Dreams are synthetic artifacts, not observations.
Trust is evidence-weighted, not affection.
The LLM is a tool, not BEAN's identity.
No direct LLM-to-actuator path.
```

## Runtime proof

Use:

```bash
echo '{"command":"run_runtime_proof","from":"supervisor"}' > $BEAN_INBOX_DIR/runtime_proof.json
```

Runtime proof reports key row counts, keeps motion disabled, and skips dream generation by default.

## Brain-layer inbox commands

Examples:

```bash
echo '{"command":"process_wisdom_event","args":{"summary":"Future plan changed and remains uncertain."},"from":"supervisor"}' > $BEAN_INBOX_DIR/wisdom.json

echo '{"command":"run_reasoning_pass","args":{"adapter":"mock","request_type":"reflection"},"from":"supervisor"}' > $BEAN_INBOX_DIR/reasoning.json

echo '{"command":"create_hypothesis","args":{"claim_text":"This may need follow-up.","claim_type":"hypothesis","evidence_level":"hypothetical"},"from":"supervisor"}' > $BEAN_INBOX_DIR/hypothesis.json
```

## Brain layers added after 0.8

### Brain 0.9: Wisdom Module

Event-triggered associative memory plus repair intelligence. It separates event fact, symbolic interpretation, assumption candidate, evidence, alternatives, pressure deltas, repair records, and loop signatures.

### Brain 0.11: OpenAI-preferred reasoning layer

Builds bounded context packets and asks a reasoning provider for structured JSON proposals. Tests use a mock provider. The OpenAI provider uses the Responses API through Python stdlib when `OPENAI_API_KEY` is configured.

### Brain 0.13: Hypothesis discipline

Lets BEAN store uncertain claims as labeled hypotheses with claim type, evidence level, confidence, resolution path, and action permission. Hypotheses remain reviewable records, not facts.

### Boot readiness

`python3 -m bean.runtime.boot_readiness --temp` verifies imports, schema initialization, session start/end, wisdom, reasoning, hypothesis discipline, and runtime proof using a temporary DB.

## Documentation map

| File | Purpose |
|---|---|
| `docs/brain-install-0.2.md` | Brain 0.2 install candidate. |
| `docs/brain-0.3-epistemic-immune-system.md` | Epistemic guard, contradiction court, falsification. |
| `docs/brain-0.4-dreaming-and-uncertainty.md` | Dream engine and uncertainty garden. |
| `docs/brain-0.5-dignity-inner-weather-autobiography.md` | Dignity, inner weather, autobiography. |
| `docs/brain-0.6-brain-maintenance-runtime.md` | Runtime maintenance inbox integration. |
| `docs/brain-0.7-relationship-trust.md` | Relationship and trust model. |
| `docs/brain-0.8-runtime-proof-and-hardening.md` | Runtime proof, smoke runner, durable relationship watermark. |
| `docs/brain-0.9-wisdom-module.md` | Wisdom module. |
| `docs/brain-0.11-llm-reasoning-layer.md` | OpenAI-preferred reasoning layer. |
| `docs/brain-0.13-speculative-logic.md` | Hypothesis discipline. |
| `docs/bean-os-reformat-checklist.md` | Reformat and first-boot checklist. |

## Near-term roadmap

1. Pull latest `main` on the Jetson.
2. Run `bash scripts/bean_doctor.sh`.
3. Fix any integration failures found by doctor or CI.
4. Run `bash scripts/bean_boot_ready.sh --db "$BEAN_DB_PATH"` before enabling service.
5. Keep motion out of scope until the brain stack is boringly reliable.
