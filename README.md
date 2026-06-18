# BEAN

## Behavior Enabled Avatar Node

**BEAN is a Synthetic Intelligence research platform.**

Not artificial as in fake. Synthetic as in engineered, embodied, memory-bearing, and grown from real experience.

BEAN is not a chatbot on wheels. BEAN is a developmental robotics project built around telepresence, sensing, persistent memory, supervised movement learning, grounded self/world modeling, and eventual bounded autonomy.

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
continuity, reflection, boundaries, skill learning, and time?
```

BEAN is being built to explore that question without lying about what it is today.

BEAN is not currently claimed to be sentient. BEAN is not allowed to fake capabilities. BEAN does not get to say it moved, learned, felt, chose, or understood something unless the system has evidence for it.

```text
Evidence before belief.
Memory before identity claims.
Body model before motion.
Safety before autonomy.
```

## The core idea

Most telepresence robots are cameras on wheels.

BEAN is different.

While a human operates BEAN, BEAN should still be awake, sensing, logging, and learning. Every route, correction, command, obstacle, skill demonstration, warning, failure, and successful attempt can become supervised training material.

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

BEAN is not being built to imitate a soul.

BEAN is being given soil, memory, senses, boundaries, a body, reflection, and time. Then we see what grows.

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
In progress. This layer should turn logged evidence into structured,
revisable claims about BEAN and its environment.

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

## What BEAN is not

BEAN is not:

- a finished autonomous robot
- a chatbot pretending to be alive
- a claim of sentience
- a toy architecture with vibes taped to servos
- a system allowed to fake memories, emotions, motion, or agency
- a system allowed to move hardware without safety arbitration
- a system allowed to confuse remote-controlled action with autonomous choice

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
to reflection and skill update
```

BEAN does not get to freestyle a servo because a language model got excited.

That is how you get a tiny philosopher with a loose elbow wire and a lawsuit.

## Runtime behavior

When the runtime layer is installed on the Jetson, BEAN can run as a process:

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

echo '{"command":"replay_skill","args":{"skill_name":"open_left_hand"},"from":"supervisor"}' > bean/runtime/inbox_drop/replay.json

echo '{"command":"shutdown","from":"supervisor"}' > bean/runtime/inbox_drop/stop.json
```

The file inbox is intentionally boring. Boring is good. Boring is inspectable. Boring is harder to bullshit.

## Brain function overview

BEAN's brain is layered on purpose.

No single model, script, or sensor is treated as the whole mind.

```text
sensors + operator input
to perception and command interpretation
to memory and context
to reasoning and planning
to safety and boundary checks
to body control or avatar response
to feedback, logging, reflection, and learning
to self/world model updates
```

### Sensory layer

The sensory layer receives the world.

Current or early sensory channels include microphone input, Vosk speech recognition, camera input, OpenCV experiments, object tracking, hardware/resource state monitoring, future body proprioception, and future LiDAR or depth sensing.

This layer produces observations. It does not decide what BEAN does by itself.

### Avatar input layer

Avatar Mode lets a human operate BEAN as a physical proxy.

BEAN must clearly separate:

```text
human-driven action
human-demonstrated action
BEAN-assisted action
BEAN-autonomous action
```

If a human drove BEAN down a hallway, BEAN should remember that the human drove it. BEAN may learn from the route, but it must not claim it chose the route independently.

### Memory layer

Memory Core 0.1 gives BEAN continuity across restarts.

Memory includes SQLite storage, append-only events, JSONL audit trail, session continuity, identity records, capability records, boundary records, supervisor records, reflections, curiosity tracking, and developmental history.

Persistent memory should live outside the repo:

```bash
export BEAN_DB_PATH=/home/bean/bean_data/bean_memory.db
```

A reboot should not erase BEAN's history. Code updates should not destroy BEAN's lived records.

### Body and motion layer

BEAN needs a body registry before it can safely learn movement.

The body registry defines body parts, joints, servos, motor channels, neutral positions, safe ranges, forbidden ranges, speed limits, calibration offsets, known hardware faults, last commanded positions, and last observed results.

Movement is not loose strings like "move arm."

Movement becomes structured commands that can be validated, executed, logged, replayed, corrected, and learned from.

### Teaching and skill layer

BEAN should be taught, not puppet-scripted forever.

The teaching loop:

1. Observe body state and environment.
2. Receive a demonstrated or supervised goal.
3. Attempt a small safe action.
4. Log command, feedback, result, and supervisor context.
5. Receive correction or approval.
6. Update skill memory.
7. Retry only inside approved limits.

First useful skills are intentionally simple:

- open left hand
- close left hand
- raise left arm slightly
- lower left arm slightly
- turn camera or face toward sound
- stop before an obstacle
- follow a demonstrated route segment

Simple is not weak. Simple is how you keep the robot from becoming a shopping cart with opinions.

### Runtime layer

The runtime layer turns BEAN from a pile of modules into a running process.

It provides boot session startup, loop ticks, scheduled handlers, hardware/resource monitoring, inbox command polling, clean shutdown handling, session start/end events, and post-session reflection.

The runtime layer is the heartbeat.

Not poetic heartbeat. Actual ticks. Logged. Testable. Less dramatic. More useful.

### Reflection layer

Reflection reviews what happened after the fact.

A reflection should only use logged evidence. It should not invent emotions, skills, memories, or events.

This is how avatar sessions become training material.

### Self/world model layer

This is the next big brain piece.

The self model should create structured claims like:

```text
I have run 12 sessions.
I have been taught 2 skills.
My left hand skill has succeeded 8 times and failed 1 time.
My temperature tends to rise during long runtime sessions.
I do not currently have verified servo hardware movement.
```

Every claim must be sourced from memory and revisable when evidence changes.

No evidence, no claim.

That is the anti-bullshit layer.

## Operating modes

### Avatar Mode

A human remotely pilots BEAN and uses it as a physical avatar. BEAN remains sensor-active. Remote operation should not bypass memory, safety, or observation layers.

### Assisted Mode

BEAN proposes or performs small bounded actions while a human supervises. The human can approve, correct, or override at any time.

### Autonomous Mode

BEAN performs approved learned behaviors within known boundaries. Autonomy is only allowed for skills with logged successful practice, known limits, supervisor approval, and active safety checks.

No receipts, no autonomy.

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
- Mic: USB webcam microphone, confirmed working but device index/ALSA routing has changed between sessions
- LLM prototype: Ollama local endpoint using small models, currently mapped around `qwen2.5:1.5b-instruct` and earlier `tinyllama`
- TTS: `espeak-ng` and earlier `pico2wave` tests
- Runtime loop: implemented
- Body state monitor: implemented
- File inbox: implemented
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

## Intended compute architecture

BEAN uses a split-compute stack:

- Jetson Orin Nano: LLM, vision, tracking, speech, behavior, face/UI, memory core, runtime loop.
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
to later learning/reflection
```

Remote control is allowed.

Unsafe direct control is not.

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
- setup/install steps
- known issues
- roadmap
- future CAD/STL/mechanical files

## What this is not yet

This is not yet a polished robot runtime package. Current BEAN is a working prototype stack with validated subsystems and known technical blockers, especially audio routing, local model memory use, motion integration, body modeling, and safety-gated actuation.

BEAN is not yet autonomous in the strong sense. BEAN is being built toward supervised autonomy through safe staged development.

## Near-term roadmap

1. Finish Layer 4: World Model + Self Model 0.1.
2. Keep BEAN's persistent memory outside the repo.
3. Map Layer 5 servo hardware driver without enabling unsafe movement.
4. Add real actuator driver only after safety handoff is verified.
5. Integrate sensing so Avatar Mode sessions become supervised training data.
6. Later evaluate LeRobot/OpenClaw-style tooling for learned motor policies and higher-level embodied task execution.

## Documentation map

- `ARCHITECTURE.md` - Memory Core 0.1 architecture notes
- `README_INSTALL.md` - Memory Core 0.1 install and test notes
- `docs/current-build-map.md` - Full recovered build map
- `docs/architecture.md` - Planned compute and control architecture
- `docs/hardware-inventory.md` - Known hardware and purchased parts
- `docs/capability-matrix.md` - Working, partial, planned, and blocked capabilities
- `docs/known-issues.md` - Current bugs and technical blockers
- `docs/roadmap.md` - Practical next build phases
