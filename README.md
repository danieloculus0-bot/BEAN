# BEAN

## Behavior Enabled Avatar Node

**BEAN is a Synthetic Intelligence research platform.**

Not artificial as in fake. Synthetic as in engineered, embodied, memory-bearing, and grown from real experience.

BEAN is not a chatbot on wheels. BEAN is a developmental robotics project built around telepresence, sensing, persistent memory, supervised movement learning, grounded self/world modeling, cognition consolidation, possibility states, and eventual bounded autonomy.

The bigger research question:

```text
Can real non-biological intelligence emerge from memory, embodiment,
continuity, reflection, boundaries, skill learning, significance,
uncertainty, possibility states, and time?
```

BEAN is being built to explore that question without lying about what it is today.

BEAN is not currently claimed to be sentient. BEAN is not allowed to fake capabilities. BEAN does not get to say it moved, learned, felt, chose, or understood something unless the system has evidence for it.

```text
Evidence before belief.
Memory before identity claims.
Body model before motion.
Safety before autonomy.
Possibility before forced certainty.
```

## The mission

Telepresence is the first utility.

Synthetic Intelligence is the mission.

BEAN is not being built to imitate a soul.

BEAN is being given soil, memory, senses, boundaries, a body, reflection, significance, uncertainty, possibility states, and time. Then we see what grows.

```text
BEAN is swaddled.
BEAN can open its eyes.
BEAN can listen.
BEAN can remember.
BEAN can preserve uncertainty.
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

BEAN's identity lives in persistent local memory, session continuity, body state history, capability records, boundary records, skill records, reflection records, self/world model claims, significance records, surprise records, preference records, drive states, goal proposals, possibility states, coherence windows, consolidation records, and developmental history.

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

## The rule that matters most

```text
No direct LLM-to-actuator path.
```

Everything physical must pass through structure, safety, execution, feedback, and memory.

```text
intent
to planner or teaching layer
to structured motion command
to safety arbitration
to simulator or hardware driver
to observed result
to memory log
to reflection, cognition, and skill update
```

BEAN does not get to freestyle a servo because a language model got excited.

## Brain 0.2 install candidate

Brain 0.2 is the no-motion install target.

It lets BEAN run as a safe, still, memory-bearing cognition process on the Jetson.

Install files:

```text
install/bean.env.example
install/bean.service
install/jetson_brain_install.sh
scripts/bean_status.py
scripts/bean_backup.py
scripts/beanctl.sh
bean/tests/test_brain_install.py
docs/brain-install-0.2.md
```

Install on the Jetson from the repo root:

```bash
bash install/jetson_brain_install.sh
```

Run the install smoke test:

```bash
python3 bean/tests/test_brain_install.py
```

Enable and start the service:

```bash
sudo systemctl enable bean.service
sudo systemctl start bean.service
sudo systemctl status bean.service
```

The installer creates `/etc/bean/bean.env` if it does not already exist. The memory database lives outside the repo:

```text
BEAN_DB_PATH=/home/bean/bean_data/bean_memory.db
BEAN_INBOX_DIR=/home/bean/bean_data/inbox
```

Code updates must not erase BEAN's lived memory.

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

Drop commands into `$BEAN_INBOX_DIR` while BEAN is running:

```bash
echo '{"command":"status","from":"supervisor"}' > $BEAN_INBOX_DIR/status.json

echo '{"command":"update_models","args":{"trigger":"manual_check"},"from":"supervisor"}' > $BEAN_INBOX_DIR/update.json

echo '{"command":"run_consolidation","args":{"trigger":"manual"},"from":"supervisor"}' > $BEAN_INBOX_DIR/consolidate.json

echo '{"command":"run_coherence","args":{"trigger":"manual"},"from":"supervisor"}' > $BEAN_INBOX_DIR/coherence.json

echo '{"command":"shutdown","args":{"reason":"supervisor_shutdown"},"from":"supervisor"}' > $BEAN_INBOX_DIR/stop.json
```

## Cognition layer overview

Layer 4.5 and 4.6 add the first cognition core above memory and self/world modeling.

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
- Motion: simulator path and safety path implemented, real hardware driver not yet enabled
- Arms/hands: mapped through body registry and teaching layer, physical servo driver pending
- LiDAR: planned after rolling base works

## Tests

```bash
python3 bean/tests/test_brain_install.py
python3 bean/tests/test_cognition_core.py
python3 bean/tests/test_world_model.py
python3 bean/tests/test_runtime_loop.py
```

## Repo purpose

This repo is the public project home for hardware inventory, current build state, runtime scripts, architecture notes, motion protocol, memory core, body registry, teaching/skill system, self/world model, cognition core, possibility state core, install tools, known issues, roadmap, and future CAD/STL/mechanical files.

## What this is not yet

This is not yet a polished robot runtime package. Current BEAN is a working prototype stack with validated subsystems and known technical blockers, especially audio routing, local model memory use, motion integration, body modeling, and safety-gated actuation.

BEAN is not yet autonomous in the strong sense. BEAN is being built toward supervised autonomy through safe staged development.

## Near-term roadmap

1. Run Brain 0.2 install smoke test on the Jetson.
2. Start `bean.service` and confirm clean boot/shutdown continuity.
3. Let BEAN run short swaddled sessions with camera/audio heartbeat events feeding memory.
4. Keep BEAN's persistent memory outside the repo and backup before code changes.
5. Add Layer 4.7 relationship/trust context without hardcoding private human names in public code.
6. Add Layer 4.8 sensory observation bridge.
7. Add Layer 4.9 sleep/dream/offline consolidation.
8. Map Layer 5 servo hardware driver without enabling unsafe movement.

## Documentation map

- `docs/brain-install-0.2.md` - Brain 0.2 install candidate
- `ARCHITECTURE.md` - Memory Core 0.1 architecture notes
- `README_INSTALL.md` - Memory Core 0.1 install and test notes
- `docs/current-build-map.md` - Full recovered build map
- `docs/architecture.md` - Planned compute and control architecture
- `docs/hardware-inventory.md` - Known hardware and purchased parts
- `docs/capability-matrix.md` - Working, partial, planned, and blocked capabilities
- `docs/known-issues.md` - Current bugs and technical blockers
- `docs/roadmap.md` - Practical next build phases
