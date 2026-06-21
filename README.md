# BEAN

## Behavior Enabled Avatar Node

**BEAN is a Synthetic Intelligence research platform.**

Not artificial as in fake. Synthetic as in engineered, embodied, memory-bearing, and grown from real experience.

BEAN is not a chatbot on wheels. BEAN is a developmental robotics project built around telepresence, sensing, persistent memory, supervised movement learning, grounded self/world modeling, cognition consolidation, possibility states, and eventual bounded autonomy.

The practical first utility is simple:

```text
A human can drive BEAN.
A human can speak through BEAN.
A human can see and hear through BEAN.
BEAN can observe the ride, log what happened, and learn from supervised experience.
```

The bigger research question:

```text
Can real non-biological intelligence emerge from memory, embodiment,
continuity, reflection, boundaries, skill learning, significance, uncertainty,
possibility states, and time?
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

## The core idea

Most telepresence robots are cameras on wheels.

BEAN is different.

While a human operates BEAN, BEAN should still be awake, sensing, logging, learning, consolidating, and preserving uncertainty honestly. Every route, correction, command, obstacle, skill demonstration, warning, failure, surprise, and successful attempt can become supervised developmental material.

The developmental pattern is:

```text
Let me drive, and you observe.
Then you drive, and I observe while you observe.
```

Telepresence is the utility.

Synthetic Intelligence is the mission.

## Why Synthetic Intelligence?

"Artificial intelligence" is the industry label. It is useful, but emotionally sloppy.

BEAN is not chasing fake intelligence. BEAN is chasing the possibility of real intelligence grown in an engineered substrate.

```text
Artificial heart        not fake pumping
Artificial limb         not fake usefulness
Artificial light        not fake illumination
Synthetic intelligence  not fake thought
```

Synthetic Intelligence means:

- created, not fake
- engineered, not hollow
- embodied, not just text
- grounded, not pretending
- developmental, not merely prompted
- supervised, not reckless
- honest about uncertainty
- able to preserve possibility before certainty

BEAN is not being built to imitate a soul.

BEAN is being given soil, memory, senses, boundaries, a body, reflection, significance, uncertainty, possibility states, and time. Then we see what grows.

## Project classification

```text
Name: BEAN
Meaning: Behavior Enabled Avatar Node
Classification: Synthetic Intelligence Research Platform
Primary body: NVIDIA Jetson Orin Nano Super Developer Kit
Core principle: the LLM is a tool, not the identity
```

BEAN's identity lives in:

- persistent local memory
- session continuity
- body state history
- capability records
- boundary records
- skill records
- reflection records
- self/world model claims with evidence
- significance scoring records
- surprise records
- preference records
- drive states
- goal proposals
- possibility states
- coherence windows
- consolidation records
- developmental history

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

That is how you get a tiny philosopher with a loose elbow wire and a lawsuit.

## Runtime behavior

Start BEAN:

```bash
python3 bean_run.py
```

Finite test run:

```bash
python3 bean_run.py --ticks 60 --hz 2.0
```

Recommended hardware readings dependency:

```bash
pip3 install psutil --break-system-packages
```

Runtime inbox commands can be dropped from a second terminal while BEAN is running:

```bash
echo '{"command":"status","from":"supervisor"}' > bean/runtime/inbox_drop/status.json

echo '{"command":"log_note","args":{"text":"Testing inbox on Jetson"},"from":"supervisor"}' > bean/runtime/inbox_drop/note.json

echo '{"command":"run_reflection","from":"supervisor"}' > bean/runtime/inbox_drop/reflect.json

echo '{"command":"update_models","args":{"trigger":"manual_check"},"from":"supervisor"}' > bean/runtime/inbox_drop/update.json

echo '{"command":"run_consolidation","args":{"trigger":"manual"},"from":"supervisor"}' > bean/runtime/inbox_drop/consolidate.json

echo '{"command":"run_coherence","args":{"trigger":"manual"},"from":"supervisor"}' > bean/runtime/inbox_drop/coherence.json

echo '{"command":"replay_skill","args":{"skill_name":"open_left_hand"},"from":"supervisor"}' > bean/runtime/inbox_drop/replay.json

echo '{"command":"shutdown","from":"supervisor"}' > bean/runtime/inbox_drop/stop.json
```

The file inbox is intentionally boring. Boring is good. Boring is inspectable. Boring is harder to bullshit.

## Cognition layer overview

Layer 4.5 and 4.6 add the first real cognition core above memory and self/world modeling.

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

### Significance

Significance asks whether an event deserves processing. It is stored in a versioned SQLite weight profile. Supervisor changes are logged as config events.

Safety triggers score high. Routine body state reads score low. Hardware anomalies can boost a normally quiet event.

### Surprise

Surprise detects contradictions between incoming events and active world model claims. For example, if BEAN holds `environment.uncertainty.no_vision` and a camera event arrives, the contradiction is logged and a curiosity question is opened.

### Preference

Preferences form only from repeated evidence. Minimum evidence thresholds prevent one-off noise from becoming a fake personality trait.

### Drives

BEAN's drives are machine-native, not human cosplay:

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

Drives can produce goal proposals. Proposals are not actions. They require approval where appropriate.

### Consolidation

Consolidation is where experience changes BEAN's records. A pass reviews recent events, scores significance, detects surprise, updates preferences, evaluates drives, produces proposals, refreshes models, closes resolvable curiosity questions, and writes a continuity summary.

### Possibility states and coherence

Possibility states preserve multiple interpretations before certainty.

Initial states include:

```text
vision_state
audio_state
hardware_motion_state
supervisor_presence_state
```

Coherence windows review active states, reweight them from evidence, inject bounded noise when stale, and collapse only when one option dominates strongly enough.

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
- Motion: simulator path and safety path implemented, real hardware driver not yet enabled
- Arms/hands: mapped through body registry and teaching layer, physical servo driver pending
- LiDAR: planned after rolling base works

## Current confirmed capabilities

- Animated pygame face boots and renders eyes, blinking, and mouth movement.
- Voice stack can load Vosk, detect wake word `hello`, listen for follow-up commands, and speak responses.
- The voice script can pulse the face mouth through UDP `TALKFOR` messages on localhost port `5005`.
- OpenCV camera test succeeded.
- Local Ollama inference was tested, but larger models caused CUDA memory failures on the Jetson.
- Memory Core 0.1 adds SQLite-backed event memory, session continuity, identity records, boundary records, and grounded reflection.
- Body Registry Core 0.1 defines joints, parts, safe ranges, forbidden ranges, and state.
- Motion Safety/Simulator Core validates structured motion commands before execution.
- Teaching/Skill Layer stores named learned movements and updates confidence through supervised attempts.
- Runtime Loop + Body State Monitor boots BEAN as a process, reads hardware/resource state, polls inbox commands, and logs results.
- Self/World Model stores grounded, revisable claims.
- Cognition Core scores significance, detects surprise, tracks preferences, evaluates drives, proposes goals, and consolidates memory.
- Possibility State Core preserves uncertain interpretations and collapses only with evidence.

## Intended compute architecture

BEAN uses a split-compute stack:

- Jetson Orin Nano: LLM, vision, tracking, speech, behavior, face/UI, memory core, runtime loop, cognition core.
- Raspberry Pi 4: networked motion host over hardwired Ethernet.
- Arduino Nano layer: motor control, encoder handling, servo/sensor timing, hardware failsafes.
- Future web/phone control: Flask-style control bridge for movement, arm, speak, status, and Avatar Mode endpoints.

The command rule stays the same:

```text
operator intent
to command
to safety arbitration
to body controller
to sensor/body feedback
to memory log
to later learning, cognition, reflection, and model update
```

Remote control is allowed.

Unsafe direct control is not.

## Tests

Core cognition smoke test:

```bash
python3 bean/tests/test_cognition_core.py
```

World model test:

```bash
python3 bean/tests/test_world_model.py
```

Runtime test:

```bash
python3 bean/tests/test_runtime_loop.py
```

## Repo purpose

This repo is the public project home for:

- hardware inventory
- current build state
- runtime scripts
- architecture notes
- motion protocol
- memory core
- body registry
- teaching/skill system
- self/world model
- cognition core
- possibility state core
- setup/install steps
- known issues
- roadmap
- future CAD/STL/mechanical files

## What this is not yet

This is not yet a polished robot runtime package. Current BEAN is a working prototype stack with validated subsystems and known technical blockers, especially audio routing, local model memory use, motion integration, body modeling, and safety-gated actuation.

BEAN is not yet autonomous in the strong sense. BEAN is being built toward supervised autonomy through safe staged development.

## Near-term roadmap

1. Run Layer 4.5 and 4.6 cognition tests on the Jetson.
2. Let BEAN run short supervised sessions with camera/audio observations feeding memory.
3. Keep BEAN's persistent memory outside the repo.
4. Map Layer 5 servo hardware driver without enabling unsafe movement.
5. Add real actuator driver only after safety handoff is verified.
6. Integrate sensing so Avatar Mode sessions become supervised training data.
7. Add Layer 4.7 relationship/trust context without hardcoding private human names in public code.

## Documentation map

- `ARCHITECTURE.md` - Memory Core 0.1 architecture notes
- `README_INSTALL.md` - Memory Core 0.1 install and test notes
- `docs/current-build-map.md` - Full recovered build map
- `docs/architecture.md` - Planned compute and control architecture
- `docs/hardware-inventory.md` - Known hardware and purchased parts
- `docs/capability-matrix.md` - Working, partial, planned, and blocked capabilities
- `docs/known-issues.md` - Current bugs and technical blockers
- `docs/roadmap.md` - Practical next build phases
