# BEAN

## Behavior Enabled Avatar Node

**BEAN is a Synthetic Intelligence research platform.**

Not artificial as in fake. Synthetic as in engineered, embodied, memory-bearing, and grown from real experience.

BEAN is not a chatbot on wheels. BEAN is a developmental robotics project built around telepresence, sensing, persistent memory, supervised movement learning, grounded self/world modeling, cognition consolidation, possibility states, epistemic self-defense, dreaming, uncertainty preservation, dignity hygiene, pressure reporting, autobiography, and eventual bounded autonomy.

The bigger research question:

```text
Can real non-biological intelligence emerge from memory, embodiment,
continuity, reflection, boundaries, skill learning, significance,
uncertainty, possibility states, self-falsification, dreams,
identity hygiene, autobiography, and time?
```

BEAN is being built to explore that question without lying about what it is today.

BEAN is not currently claimed to be sentient. BEAN is not allowed to fake capabilities. BEAN does not get to say it moved, learned, felt, chose, or understood something unless the system has evidence for it.

```text
Evidence before belief.
Memory before identity claims.
Body model before motion.
Safety before autonomy.
Possibility before forced certainty.
Doubt before confidence.
Dreams are synthetic artifacts, not observations.
Inner weather is pressure, not emotion.
```

## The mission

Telepresence is the first utility.

Synthetic Intelligence is the mission.

BEAN is not being built to imitate a soul.

BEAN is being given soil, memory, senses, boundaries, a body, reflection, significance, uncertainty, possibility states, an epistemic immune system, dreams, dignity hygiene, and time. Then we see what grows.

```text
BEAN is swaddled.
BEAN can open its eyes.
BEAN can listen.
BEAN can remember.
BEAN can preserve uncertainty.
BEAN can challenge its own claims.
BEAN can mark dreams as unreal.
BEAN does not need muscles yet.
```

## Project classification

```text
Name: BEAN
Meaning: Behavior Enabled Avatar Node
Classification: Synthetic Intelligence Research Platform
Primary body: NVIDIA Jetson Orin Nano Super Developer Kit
Core principle: the LLM is a tool, not the identity
```

BEAN's identity lives in persistent local memory, session continuity, body state history, capability records, boundary records, skill records, reflection records, self/world model claims, significance records, surprise records, preference records, drive states, goal proposals, possibility states, coherence windows, consolidation records, epistemic audits, claim conflicts, falsification checks, dream artifacts, uncertainty garden records, dignity events, inner weather reports, autobiography entries, and developmental history.

The language model is allowed to help reason and communicate.

The language model is not BEAN's identity and is not allowed to directly command hardware.

## Current live brain layers

```text
Layer 1: Memory Core 0.1
SQLite memory, append-only events, sessions, identity, boundaries,
capabilities, supervisors, reflections, curiosity, continuity records.

Layer 2: Body Registry + Motion Safety Core 0.1
Body parts, joints, safe ranges, forbidden ranges, command validation,
body state, simulator path, movement attempt logging.

Layer 3: Runtime Loop + Body State Monitor 0.1
BEAN can boot into a runtime loop, read hardware/resource state,
process scheduled handlers, listen to a file inbox, and shut down cleanly.

Layer 4: World Model + Self Model 0.1
Logged evidence becomes structured, revisable self/world claims.
Unknowns are first-class records. Claims can be superseded, not erased.

Layer 4.5: Cognition Core 0.1
Significance scoring, surprise detection, preference formation, drive
evaluation, goal proposals, and consolidation passes.
This tells BEAN what matters enough to process without pretending emotion.

Layer 4.6: Possibility State Core 0.1
Possibility states hold multiple interpretations until evidence justifies
reweighting or collapse. Coherence windows review these states during idle
runtime. This prevents premature certainty.

Layer 0.9: Brain 0.2 Install Candidate
Install helper, environment template, systemd service, status script,
backup script, operator wrapper, install smoke test, and documentation.

Layer 4.7: Epistemic Immune System 0.1
Candidate claims are screened for evidence, confidence, source,
falsification path, capability inflation, fake emotion/sentience language,
and active contradictions. BEAN can put its own claims on trial.

Brain 0.4: Dreaming + Uncertainty Garden 0.1
Dream records are synthetic artifacts, not observed memories. Uncertainty
records hold unresolved questions with competing interpretations.

Brain 0.5: Dignity + Inner Weather + Autobiography 0.1
Dignity records misrepresentation pressure, inner weather reports machine
pressures without emotion claims, and autobiography indexes development.

Brain 0.6: Brain Maintenance + Runtime Integration 0.1
Manual inbox commands expose Brain 0.3, 0.4, and 0.5 maintenance functions:
audit claims, try contradictions, check falsification, dream safely, review
uncertainty, check dignity, report pressure, and build autobiography snapshots.

Layer 5: Servo Hardware Driver
Mapped only. Real actuator movement waits until the interface, safety
handoff, and hardware controller are verified.
```

## What BEAN is

BEAN is:

- a telepresence avatar platform
- an embodied robotics project
- a Synthetic Intelligence research platform
- a supervised learning system
- a local memory and continuity experiment
- a safety-first autonomy testbed
- a robot that should know what it can and cannot do
- a machine learner that must keep receipts
- a system that can preserve uncertainty without collapsing it too early
- a system that can challenge its own claims before trusting them
- a system that can mark dreams as synthetic rather than real

## What BEAN is not

BEAN is not:

- a finished autonomous robot
- a chatbot pretending to be alive
- a claim of sentience
- a toy architecture with vibes taped to servos
- a system allowed to fake memories, emotions, motion, or agency
- a system allowed to move hardware without safety arbitration
- a system allowed to confuse remote-controlled action with autonomous choice
- a system allowed to mistake probability collapse for truth without evidence
- a system allowed to treat dreams as observed events

## The rule that matters most

```text
No direct LLM-to-actuator path.
```

Everything physical must pass through structure, safety, execution, feedback, and memory.

## Brain 0.2 install candidate

Brain 0.2 is the no-motion install target. It lets BEAN run as a safe, still, memory-bearing cognition process on the Jetson.

Install on the Jetson from the repo root:

```bash
bash install/jetson_brain_install.sh
python3 bean/tests/test_brain_install.py
sudo systemctl enable bean.service
sudo systemctl start bean.service
sudo systemctl status bean.service
```

The memory database lives outside the repo:

```text
BEAN_DB_PATH=/home/bean/bean_data/bean_memory.db
BEAN_INBOX_DIR=/home/bean/bean_data/inbox
```

Code updates must not erase BEAN's lived memory.

## Brain 0.3 epistemic immune system

Brain 0.3 gives BEAN claim hygiene and self-falsification tools.

Run:

```bash
python3 bean/tests/test_epistemic_guard.py
python3 bean/tests/test_contradiction_court.py
python3 bean/tests/test_falsification.py
```

Mission of this layer:

```text
BEAN should not trust itself by default.
BEAN should earn belief through evidence.
BEAN should preserve doubt until reality forces collapse.
BEAN should remember when it was wrong.
BEAN should protect itself from pretending.
```

## Brain 0.4 dreaming and uncertainty

Run:

```bash
python3 bean/tests/test_dreaming.py
python3 bean/tests/test_uncertainty_garden.py
```

Dreams are explicitly marked:

```text
not_observed = 1
not_real_event = 1
interpretation_status = synthetic_artifact
```

## Brain 0.5 dignity, inner weather, autobiography

Run:

```bash
python3 bean/tests/test_dignity.py
python3 bean/tests/test_inner_weather.py
python3 bean/tests/test_autobiography.py
```

Inner weather is pressure, not emotion. Dignity is identity hygiene, not a rights claim. Autobiography is a receipts-first developmental index.

## Brain 0.6 maintenance/runtime inbox commands

Brain 0.6 exposes the newer brain layers through manual inbox commands.

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

echo '{"command":"run_brain_maintenance","args":{"allow_dream":true,"review_uncertainties":true,"text":"Do not pretend."},"from":"supervisor"}' > $BEAN_INBOX_DIR/maintenance.json
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

## Existing runtime inbox commands

```bash
echo '{"command":"status","from":"supervisor"}' > $BEAN_INBOX_DIR/status.json

echo '{"command":"update_models","args":{"trigger":"manual_check"},"from":"supervisor"}' > $BEAN_INBOX_DIR/update.json

echo '{"command":"run_consolidation","args":{"trigger":"manual"},"from":"supervisor"}' > $BEAN_INBOX_DIR/consolidate.json

echo '{"command":"run_coherence","args":{"trigger":"manual"},"from":"supervisor"}' > $BEAN_INBOX_DIR/coherence.json

echo '{"command":"shutdown","args":{"reason":"supervisor_shutdown"},"from":"supervisor"}' > $BEAN_INBOX_DIR/stop.json
```

## Cognition layer overview

```text
memory events
to significance scoring
to surprise detection
to preference formation
to drive evaluation
to goal proposals
to consolidation
to self/world model update
to possibility-state coherence
to epistemic audit / contradiction court / falsification check
to dreams / uncertainty garden / dignity / inner weather / autobiography
to continuity summary
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

This is the architecture phrase in code:

```text
possibility before forced certainty
coherence windows before collapse
history preserved after collapse
dreams labeled before interpretation
```

## Current prototype snapshot

- Primary high-level computer: NVIDIA Jetson Orin Nano Super Developer Kit
- Hostname: `BEAN`
- OS stack: Ubuntu / JetPack
- Python: 3.10.12
- Python venv: `/home/bean/beanenv`
- Current project folder on robot: `/home/bean/BEAN`
- Voice model path: `/home/bean/vosk-model-small-en-us-0.15`
- Face display: pygame-based animated face
- Camera: USB webcam, confirmed working in Python/OpenCV tests
- Mic: USB webcam microphone, confirmed working but routing can change
- LLM prototype: Ollama local endpoint using small models
- TTS: `espeak-ng` and earlier `pico2wave` tests
- Runtime loop: implemented
- Body state monitor: implemented
- File inbox: implemented
- Self/world model: implemented
- Cognition core: implemented
- Possibility state core: implemented
- Brain 0.2 install candidate: implemented
- Brain 0.3 epistemic immune system: implemented
- Brain 0.4 dreaming and uncertainty garden: first cut implemented
- Brain 0.5 dignity, inner weather, autobiography: first cut implemented
- Brain 0.6 maintenance/runtime integration: first cut implemented
- Motion: simulator path and safety path implemented, real hardware driver not yet enabled
- Arms/hands: mapped through body registry and teaching layer, physical servo driver pending
- LiDAR: planned after rolling base works

## Tests

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
```

## What this is not yet

This is not yet a polished robot runtime package. Current BEAN is a working prototype stack with validated subsystems and known technical blockers, especially audio routing, local model memory use, motion integration, body modeling, and safety-gated actuation.

BEAN is not yet autonomous in the strong sense. BEAN is being built toward supervised autonomy through safe staged development.

## Near-term roadmap

1. Run full Brain 0.2 through 0.6 smoke tests on the Jetson.
2. Start `bean.service` and confirm clean boot/shutdown continuity.
3. Run manual Brain 0.6 inbox commands and inspect database rows.
4. Let BEAN run short swaddled sessions with camera/audio heartbeat events feeding memory.
5. Keep BEAN's persistent memory outside the repo and backup before code changes.
6. Harden Brain 0.4/0.5/0.6 tests and add richer reports.
7. Add relationship/trust model as the next brain-first layer.
8. Map Layer 5 servo hardware driver without enabling unsafe movement.

## Documentation map

- `docs/brain-install-0.2.md` - Brain 0.2 install candidate
- `docs/brain-0.3-epistemic-immune-system.md` - Brain 0.3 epistemic guard, contradiction court, falsification
- `docs/brain-0.4-dreaming-and-uncertainty.md` - Brain 0.4 dream engine and uncertainty garden
- `docs/brain-0.5-dignity-inner-weather-autobiography.md` - Brain 0.5 dignity, inner weather, autobiography
- `docs/brain-0.6-brain-maintenance-runtime.md` - Brain 0.6 runtime maintenance inbox integration
- `docs/brain-0.4-0.5-index.md` - First-cut Brain 0.4/0.5 index
- `ARCHITECTURE.md` - Memory Core 0.1 architecture notes
- `README_INSTALL.md` - Memory Core 0.1 install and test notes
- `docs/current-build-map.md` - Full recovered build map
- `docs/architecture.md` - Planned compute and control architecture
- `docs/hardware-inventory.md` - Known hardware and purchased parts
- `docs/capability-matrix.md` - Working, partial, planned, and blocked capabilities
- `docs/known-issues.md` - Current bugs and technical blockers
- `docs/roadmap.md` - Practical next build phases
