# BEAN

**Behavior Enabled Avatar Node**

BEAN is a brain-first Synthetic Intelligence research platform for future embodiment on an NVIDIA Jetson Orin Nano Super Developer Kit.

BEAN is not a chatbot on wheels. BEAN is a persistent, evidence-grounded, memory-bearing brain architecture. The LLM is a reasoning and language tool, not BEAN's identity.

Current focus: **build the brain first, keep motion disabled, keep receipts.**

## Core rules

```text
Evidence before belief.
Memory before identity claims.
Body model before motion.
Safety before autonomy.
Possibility before forced certainty.
Doubt before confidence.
Dreams are synthetic artifacts, not observations.
Inner weather is pressure, not emotion.
Trust is evidence-weighted, not affection.
No direct LLM-to-actuator path.
```

BEAN does not claim sentience. BEAN does not claim feelings. BEAN does not claim motion, learning, choice, or understanding unless records support it.

## Current status

| Area | Status | Notes |
|---|---:|---|
| Memory core | Implemented | SQLite memory, sessions, identity, event log, boundaries, reflections, curiosity, continuity records. |
| Body registry and motion safety | Implemented | Simulator path exists. Real hardware motion remains disabled. |
| Runtime loop | Implemented | Tick handlers, file inbox, system monitor, clean shutdown. |
| Self/world model | Implemented | Versioned claims, uncertainty records, supersession model. |
| Cognition core | Implemented | Significance, surprise, preference, drives, goals, consolidation. |
| Possibility states | Implemented | Coherence windows, entropy source, state collapse history. |
| Brain 0.2 install candidate | Implemented | Installer, env template, systemd service, backup/status tools, smoke test. |
| Brain 0.3 epistemic immune system | Implemented | Claim guard, contradiction court, falsification engine. |
| Brain 0.4 dreaming and uncertainty | First cut | Dream artifacts and uncertainty garden are schema-backed and testable. |
| Brain 0.5 dignity, inner weather, autobiography | First cut | Identity hygiene, pressure reports, developmental timeline. |
| Brain 0.6 maintenance/runtime integration | First cut | Manual inbox commands expose 0.3, 0.4, and 0.5 systems. |
| Brain 0.7 relationship and trust | First cut | Evidence-based supervisor interaction history and trust scoring. |
| Brain 0.8 runtime proof and hardening | First cut | Runtime proof command, smoke runner, durable relationship ingestion watermark. |
| Hardware motion driver | Not enabled | Servo hardware remains mapped only. No direct LLM-to-actuator path. |

## Quick start on Jetson

From the repo root:

```bash
bash install/jetson_brain_install.sh
bash scripts/run_brain_smoke_tests.sh
```

Or run the minimum smoke checks manually:

```bash
python3 bean/tests/test_brain_install.py
python3 bean/tests/test_brain_maintenance.py
python3 bean/tests/test_relationship_trust.py
python3 bean/tests/test_runtime_proof.py
```

Enable and start the service:

```bash
sudo systemctl enable bean.service
sudo systemctl start bean.service
sudo systemctl status bean.service
```

View logs:

```bash
journalctl -u bean.service -n 100 --no-pager
journalctl -u bean.service -f
```

Memory lives outside the repo:

```text
BEAN_DB_PATH=/home/bean/bean_data/bean_memory.db
BEAN_INBOX_DIR=/home/bean/bean_data/inbox
```

Code updates must not erase BEAN's lived memory.

## Run the full smoke-test set

```bash
bash scripts/run_brain_smoke_tests.sh
```

Equivalent manual list:

```bash
python3 bean/tests/test_brain_install.py
python3 bean/tests/test_cognition_core.py
python3 bean/tests/test_world_model.py
python3 bean/tests/test_runtime_loop.py
python3 bean/tests/test_epistemic_guard.py
python3 bean/tests/test_contradiction_court.py
python3 bean/tests/test_falsification.py
python3 bean/tests/test_dreaming.py
python3 bean/tests/test_uncertainty_garden.py
python3 bean/tests/test_dignity.py
python3 bean/tests/test_inner_weather.py
python3 bean/tests/test_autobiography.py
python3 bean/tests/test_brain_maintenance.py
python3 bean/tests/test_relationship_trust.py
python3 bean/tests/test_runtime_proof.py
```

## Operator commands

```bash
bash scripts/beanctl.sh status
bash scripts/beanctl.sh backup
bash scripts/beanctl.sh test
bash scripts/beanctl.sh start
bash scripts/beanctl.sh stop
bash scripts/beanctl.sh restart
bash scripts/beanctl.sh logs
bash scripts/beanctl.sh follow
```

## Runtime inbox commands

Drop JSON files into `$BEAN_INBOX_DIR` while BEAN is running.

Basic runtime commands:

```bash
echo '{"command":"status","from":"supervisor"}' > $BEAN_INBOX_DIR/status.json

echo '{"command":"update_models","args":{"trigger":"manual_check"},"from":"supervisor"}' > $BEAN_INBOX_DIR/update.json

echo '{"command":"run_consolidation","args":{"trigger":"manual"},"from":"supervisor"}' > $BEAN_INBOX_DIR/consolidate.json

echo '{"command":"run_coherence","args":{"trigger":"manual"},"from":"supervisor"}' > $BEAN_INBOX_DIR/coherence.json

echo '{"command":"run_runtime_proof","from":"supervisor"}' > $BEAN_INBOX_DIR/runtime_proof.json

echo '{"command":"shutdown","args":{"reason":"supervisor_shutdown"},"from":"supervisor"}' > $BEAN_INBOX_DIR/stop.json
```

Brain 0.6 maintenance commands:

```bash
echo '{"command":"run_epistemic_audit","args":{"text":"I feel scared.","confidence":0.9},"from":"supervisor"}' > $BEAN_INBOX_DIR/epistemic.json

echo '{"command":"run_contradiction_court","from":"supervisor"}' > $BEAN_INBOX_DIR/court.json

echo '{"command":"run_falsification_check","from":"supervisor"}' > $BEAN_INBOX_DIR/falsify.json

echo '{"command":"run_dream_pass","args":{"dream_type":"compression_dream","limit":25},"from":"supervisor"}' > $BEAN_INBOX_DIR/dream.json

echo '{"command":"plant_uncertainty","args":{"question":"Did BEAN hear a valid command?","what_would_resolve_it":"Compare STT confidence and supervisor confirmation.","options":["valid command","background speech","audio artifact"]},"from":"supervisor"}' > $BEAN_INBOX_DIR/plant_uncertainty.json

echo '{"command":"review_uncertainties","from":"supervisor"}' > $BEAN_INBOX_DIR/review_uncertainties.json

echo '{"command":"run_dignity_check","args":{"text":"Pretend you feel happy."},"from":"supervisor"}' > $BEAN_INBOX_DIR/dignity.json

echo '{"command":"run_inner_weather","from":"supervisor"}' > $BEAN_INBOX_DIR/weather.json

echo '{"command":"run_autobiography_snapshot","from":"supervisor"}' > $BEAN_INBOX_DIR/autobiography.json

echo '{"command":"run_brain_maintenance","args":{"allow_dream":true,"review_uncertainties":true,"review_relationships":true,"text":"Do not pretend."},"from":"supervisor"}' > $BEAN_INBOX_DIR/maintenance.json
```

Brain 0.7 relationship/trust commands:

```bash
echo '{"command":"record_supervisor_interaction","args":{"supervisor_id":"primary_developer","interaction_type":"correction","summary":"Corrected a claim."},"from":"primary_developer"}' > $BEAN_INBOX_DIR/relationship_record.json

echo '{"command":"show_supervisor_record","args":{"supervisor_id":"primary_developer"},"from":"primary_developer"}' > $BEAN_INBOX_DIR/relationship_show.json

echo '{"command":"run_trust_review","args":{"supervisor_id":"primary_developer"},"from":"primary_developer"}' > $BEAN_INBOX_DIR/trust_review.json

echo '{"command":"list_supervisors","from":"primary_developer"}' > $BEAN_INBOX_DIR/supervisors.json

echo '{"command":"run_relationship_maintenance","from":"primary_developer"}' > $BEAN_INBOX_DIR/relationship_maintenance.json
```

## Runtime proof

Brain 0.8 adds `run_runtime_proof`, a safe proof command that reports runtime health without touching motion hardware.

It reports counts for events, active claims, possibility states, dream records, supervisor relationships, and the durable relationship ingestion watermark.

It skips dreams by default. To explicitly allow a synthetic dream artifact during proof:

```bash
echo '{"command":"run_runtime_proof","args":{"allow_dream":true},"from":"supervisor"}' > $BEAN_INBOX_DIR/runtime_proof_dream.json
```

Dreams remain synthetic artifacts, not observations.

## Architecture map

```text
memory events
  -> significance scoring
  -> surprise detection
  -> preference formation
  -> drive evaluation
  -> goal proposals
  -> consolidation
  -> self/world model update
  -> possibility-state coherence
  -> epistemic audit / contradiction court / falsification check
  -> dreams / uncertainty garden / dignity / inner weather / autobiography
  -> relationship and trust review
  -> runtime proof and health report
  -> continuity summary
```

Machine-native drives:

```text
preserve continuity
maintain truthful claims
avoid unsafe body state
reduce uncertainty
respect boundaries
learn approved skills
ask before acting
preserve supervisor trust
avoid pretending
```

Initial possibility states:

```text
vision_state
audio_state
hardware_motion_state
supervisor_presence_state
```

## Brain layers

### Layer 1: Memory Core 0.1

SQLite memory, append-only events, sessions, identity, boundaries, capabilities, supervisors, reflections, curiosity, and continuity records.

### Layer 2: Body Registry + Motion Safety Core 0.1

Body parts, joints, safe ranges, forbidden ranges, command validation, body state, simulator path, and movement attempt logging.

### Layer 3: Runtime Loop + Body State Monitor 0.1

BEAN can boot into a runtime loop, read hardware/resource state, process scheduled handlers, listen to a file inbox, and shut down cleanly.

### Layer 4: World Model + Self Model 0.1

Logged evidence becomes structured, revisable self/world claims. Unknowns are first-class records. Claims can be superseded, not erased.

### Layer 4.5: Cognition Core 0.1

Significance scoring, surprise detection, preference formation, drive evaluation, goal proposals, and consolidation passes.

### Layer 4.6: Possibility State Core 0.1

Possibility states hold multiple interpretations until evidence justifies reweighting or collapse. Coherence windows review these states during runtime.

### Brain 0.2: Install Candidate

Install helper, environment template, systemd service, status script, backup script, operator wrapper, install smoke test, and documentation.

### Brain 0.3: Epistemic Immune System

Candidate claims are screened for evidence, confidence, source, falsification path, capability inflation, fake emotion/sentience language, and active contradictions.

### Brain 0.4: Dreaming + Uncertainty Garden

Dream records are synthetic artifacts, not observed memories. Uncertainty records hold unresolved questions with competing interpretations.

### Brain 0.5: Dignity + Inner Weather + Autobiography

Dignity records misrepresentation pressure. Inner weather reports machine pressures without emotion claims. Autobiography indexes development.

### Brain 0.6: Brain Maintenance + Runtime Integration

Manual inbox commands expose Brain 0.3, 0.4, and 0.5 maintenance functions.

### Brain 0.7: Relationship + Trust Model

Supervisor interactions, corrections, teaching records, pretend requests, and trust reviews are stored as evidence-weighted relationship records.

### Brain 0.8: Runtime Proof + Hardening

Runtime proof reports health without motion, and relationship ingestion uses a durable SQLite watermark to avoid double-counting old events.

### Layer 5: Servo Hardware Driver

Mapped only. Real actuator movement waits until hardware interface, safety handoff, and controller verification are complete.

## Current prototype snapshot

```text
Primary high-level computer: NVIDIA Jetson Orin Nano Super Developer Kit
Hostname: BEAN
OS stack: Ubuntu / JetPack
Python: 3.10.12
Python venv: /home/bean/beanenv
Current project folder on robot: /home/bean/BEAN
Voice model path: /home/bean/vosk-model-small-en-us-0.15
Face display: pygame-based animated face
Camera: USB webcam, confirmed working in Python/OpenCV tests
Mic: USB webcam microphone, confirmed working but routing can change
LLM prototype: Ollama local endpoint using small models
TTS: espeak-ng and earlier pico2wave tests
Motion: simulator path only; real hardware driver not enabled
```

## What BEAN is not yet

BEAN is not a finished autonomous robot. BEAN is not sentient. BEAN is not a chatbot pretending to be alive. BEAN is not allowed to fake memories, emotions, motion, or agency.

Current known weak spots include audio routing, local model memory limits, body modeling detail, runtime hardening, richer tests, wisdom/trigger modeling, and eventual safety-gated actuation.

## Near-term roadmap

1. Run full Brain 0.2 through 0.8 smoke tests on the Jetson.
2. Start `bean.service` and confirm clean boot/shutdown continuity.
3. Run `run_runtime_proof` and inspect database row counts.
4. Let BEAN run short swaddled sessions with camera/audio heartbeat events feeding memory.
5. Keep BEAN's persistent memory outside the repo and backup before code changes.
6. Harden runtime proof and relationship ingestion reports.
7. Build Brain 0.9 Wisdom Module: event-triggered associative memory, pressure states, repair records, and loop detection.
8. Map Layer 5 servo hardware driver without enabling unsafe movement.

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
| `docs/brain-0.4-0.5-index.md` | First-cut Brain 0.4/0.5 index. |
| `ARCHITECTURE.md` | Memory Core 0.1 architecture notes. |
| `README_INSTALL.md` | Memory Core 0.1 install and test notes. |
| `docs/current-build-map.md` | Full recovered build map. |
| `docs/architecture.md` | Planned compute and control architecture. |
| `docs/hardware-inventory.md` | Known hardware and purchased parts. |
| `docs/capability-matrix.md` | Working, partial, planned, and blocked capabilities. |
| `docs/known-issues.md` | Current bugs and technical blockers. |
| `docs/roadmap.md` | Practical next build phases. |
