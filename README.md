# BEAN

## Behavior Enabled Avatar Node

**BEAN is a remote avatar that learns from the ride.**

BEAN is an embodied AI robotics project built around telepresence, sensing, memory, supervised learning, and eventual autonomy. Its first practical utility is remote presence: a human can drive BEAN, speak through BEAN, see through BEAN, and hear through BEAN. Its long-term goal is to learn from guided experience until it can perform approved skills and navigation behaviors on its own.

The developmental pattern is simple:

```text
Let me drive, and you observe.
Then you drive, and I observe while you observe.
```

BEAN is not meant to be a chatbot on wheels. BEAN is being built as a physical learner with a body, sensors, memory, safety boundaries, and a growing record of experience.

Most telepresence robots are cameras on wheels. BEAN is different: while being remotely operated, BEAN should still be awake, sensing, logging, and learning. Every tour, correction, command, obstacle, route, sound, object, and operator note can become supervised training material.

Telepresence is the utility. Autonomy is the destination.

## Inspiration

BEAN is partly inspired by Sheldon Cooper's mobile virtual presence device from *The Big Bang Theory*, specifically Season 4, Episode 2, "The Cruciferous Vegetable Amplification."

That idea was a remote presence device. BEAN takes the concept further: a remote avatar that can observe, remember, learn, and eventually act with bounded autonomy.

```text
Sheldon-bot:
Remote presence to avoid the physical world.

BEAN:
Remote presence that learns from being in the physical world.
```

## What makes BEAN different

BEAN is designed around continuity.

BEAN should track:

- what happened
- what it observed
- what a human operator did
- what BEAN attempted
- what worked
- what failed
- what it was taught
- what it is allowed to do
- what it still does not know

The language model is not BEAN's identity. It is one reasoning and communication tool. BEAN's identity lives in persistent local memory, body state, capability records, safety boundaries, developmental history, and supervised experience.

## Brain function overview

BEAN's brain is designed as a layered system. Each layer has a job. No single model, script, or sensor is treated as the whole mind.

```text
sensors + operator input
        |
        v
perception and command interpretation
        |
        v
memory and context
        |
        v
reasoning and planning
        |
        v
safety and boundary checks
        |
        v
body control or avatar response
        |
        v
feedback, logging, reflection, and learning
```

### 1. Sensory layer

The sensory layer is how BEAN receives the world.

Current or early sensory channels include:

- microphone input
- Vosk speech recognition
- camera input
- OpenCV vision experiments
- object tracking experiments
- body and system state monitoring as the hardware stack develops

This layer should not decide what BEAN does by itself. It produces observations. Those observations are logged and passed upward for context, reasoning, and possible action.

Example sensory events:

```text
heard wake word
heard operator command
camera detected face
camera detected motion
object tracker changed target
CPU temperature changed
battery state changed
```

### 2. Avatar input layer

Avatar Mode lets a human operate BEAN as a physical proxy. The operator may drive, speak, observe, and guide BEAN through an environment.

Avatar Mode is not passive for BEAN. While a human is driving, BEAN should still observe and record what happened.

BEAN must clearly separate:

```text
human-driven action
human-demonstrated action
BEAN-assisted action
BEAN-autonomous action
```

This prevents false memory. If a human drove BEAN down a hallway, BEAN should remember that the human drove it. It can still learn from that route, but it must not claim it chose the route independently.

### 3. Memory layer

BEAN's memory core is designed to be local, inspectable, and persistent.

Memory Core 0.1 includes:

- SQLite-backed memory store
- append-only event logging
- JSONL audit trail
- session boot/shutdown continuity
- identity records
- capability records
- boundary records
- supervisor records
- grounded reflection pass
- curiosity question tracking

The memory layer gives BEAN continuity across restarts. A reboot should not erase BEAN's history. Code updates should not destroy BEAN's lived records.

Persistent memory should live outside the repository, for example:

```bash
export BEAN_DB_PATH=/home/bean/bean_data/bean_memory.db
```

### 4. Identity and capability layer

BEAN should always know what it is and what it is not.

BEAN is:

- an embodied robotics project
- a telepresence and avatar platform
- a supervised learning system
- a memory-bearing robot prototype
- a platform for studying safe developmental autonomy

BEAN is not:

- a finished autonomous robot
- a chatbot pretending to be a robot
- a sentient being
- a system allowed to fake capabilities
- a system allowed to move hardware without safety checks

Capability records should stay honest. If BEAN cannot do something yet, the system should say so clearly.

### 5. Reasoning layer

The LLM is a reasoning and communication tool. It can help interpret language, explain actions, summarize memory, generate plans, and communicate with humans.

The LLM is not allowed to directly command hardware.

A safe future flow should look like this:

```text
human request or observed event
        |
        v
LLM interprets intent or suggests plan
        |
        v
planner converts idea into structured command
        |
        v
safety layer validates command
        |
        v
body controller executes only approved action
        |
        v
sensor feedback and result are logged
```

This keeps language reasoning separate from physical control.

### 6. Safety and boundary layer

BEAN's safety layer is not decoration. It is the gate between intent and physical action.

Required safety concepts:

- no direct LLM-to-servo path
- no unsupervised physical movement during early stages
- hard stops for forbidden ranges
- speed and range limits for joints and motors
- supervisor override at all times
- logging of every movement attempt
- clear separation of proposed action, approved action, executed action, and observed result

Even when a human is remotely operating BEAN, commands should still pass through safety arbitration when connected to real motion hardware.

### 7. Body and motion layer

BEAN needs a body registry before it can safely learn movement.

The body registry should define:

- body parts
- joints
- servos
- motor channels
- neutral positions
- safe ranges
- forbidden ranges
- speed limits
- calibration offsets
- known hardware faults
- last commanded positions
- last observed results

Movement should not be loose strings like "move arm." Movement should become structured commands that can be validated, executed, logged, replayed, corrected, and learned from.

### 8. Teaching and skill layer

BEAN should be taught, not puppet-scripted forever.

The goal is not to hand-code every motion. The goal is to give BEAN a safe learning loop:

1. Observe body state and environment.
2. Receive a demonstrated or supervised goal.
3. Attempt a small safe action.
4. Log command, sensor feedback, body feedback, and result.
5. Receive correction or approval.
6. Update skill memory.
7. Retry only inside approved limits.

The intended movement flow is:

```text
intent -> planner/teacher layer -> safety arbitration -> body controller -> sensors/proprioception -> memory log -> reflection/skill update
```

The first useful skills should be simple, safe, and observable:

- open left hand
- close left hand
- raise left arm slightly
- lower left arm slightly
- turn camera/face toward sound
- stop before an obstacle
- follow a demonstrated route segment

### 9. Reflection and learning layer

Reflection is how BEAN reviews what happened after the fact.

A reflection should only use logged evidence. It should not invent emotions, skills, memories, or events.

A useful reflection might answer:

- What happened this session?
- What did the operator demonstrate?
- What did BEAN attempt?
- What succeeded?
- What failed?
- What was uncertain?
- What questions should be tracked?
- What needs supervisor review?

This is how avatar sessions become training material.

## Operating modes

### Avatar Mode

A human remotely pilots BEAN and uses it as a physical avatar.

In Avatar Mode, BEAN should remain sensor-active. Remote operation should not bypass memory, safety, or observation layers. BEAN should log operator commands, camera observations, microphone events, body state, obstacles, route choices, corrections, and relevant context.

BEAN must remember that the human drove. It must not claim remote-controlled actions as autonomous choices.

### Assisted Mode

BEAN proposes or performs small bounded actions while a human supervises.

Examples:

- turn slightly toward a sound
- keep the camera centered on a face
- stop before an obstacle
- follow a previously demonstrated route segment
- repeat a taught hand or arm motion inside safe limits

The human can approve, correct, or override at any time.

### Autonomous Mode

BEAN performs approved learned behaviors within known boundaries.

Autonomy should only be allowed for skills with logged successful practice, known limits, supervisor approval, and active safety checks.

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
- Motion: hardware direction established, rolling motion not fully integrated yet
- Arms/hands: planned hardware direction exists, body model and safety layer still needed
- LiDAR: planned after rolling base works

## Current confirmed capabilities

- Animated pygame face boots and renders eyes, blinking, and mouth movement.
- Voice stack can load Vosk, detect wake word `hello`, listen for follow-up commands, and speak responses.
- The voice script can pulse the face mouth through UDP `TALKFOR` messages on localhost port `5005`.
- OpenCV camera test succeeded.
- Manual object tracking was confirmed in prior development notes, with tracker data sent over UDP to drive face/eye target behavior.
- Local Ollama inference was tested, but larger models caused CUDA memory failures on the Jetson.
- Memory Core 0.1 adds SQLite-backed event memory, session continuity, identity records, boundary records, and grounded reflection.

## Intended architecture

BEAN should use a split-compute stack:

- Jetson Orin Nano: LLM, vision, tracking, speech, behavior, face/UI, memory core.
- Raspberry Pi 4: networked motion host over hardwired Ethernet.
- Arduino Nano layer: motor control, encoder handling, servo/sensor timing, hardware failsafes.
- Future web/phone control: Flask-style control bridge for movement, arm, speak, status, and Avatar Mode endpoints.

The core architecture should preserve this rule:

```text
operator intent -> command -> safety arbitration -> body controller -> sensor/body feedback -> memory log -> later learning/reflection
```

Remote control is allowed. Unsafe direct control is not.

## Repo purpose

This repo should become the public project home for:

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

This is not yet a polished robot runtime package. Current BEAN is a working prototype stack with several validated subsystems and some known technical blockers, especially audio routing, local model memory use, motion integration, body modeling, and safety-gated actuation.

BEAN is not yet autonomous in the strong sense. BEAN is being built toward supervised autonomy through safe staged development.

## Near-term roadmap

1. Merge and test Memory Core 0.1 on the Jetson.
2. Keep BEAN's persistent memory outside the repo.
3. Add body registry for arms, hands, motion base, sensors, and safe limits.
4. Add motion safety arbitration.
5. Add Avatar Mode command logging.
6. Add teaching loop for simple movements.
7. Add skill memory with confidence, success count, failure count, and preconditions.
8. Integrate sensing so Avatar Mode sessions become supervised training data.
9. Later evaluate LeRobot/OpenClaw-style tooling for learned motor policies and higher-level embodied task execution.

## Documentation map

- `ARCHITECTURE.md` - Memory Core 0.1 architecture notes
- `README_INSTALL.md` - Memory Core 0.1 install and test notes
- `docs/current-build-map.md` - Full recovered build map
- `docs/architecture.md` - Planned compute and control architecture
- `docs/hardware-inventory.md` - Known hardware and purchased parts
- `docs/capability-matrix.md` - Working, partial, planned, and blocked capabilities
- `docs/known-issues.md` - Current bugs and technical blockers
- `docs/roadmap.md` - Practical next build phases
- `runtime/README.md` - Placeholder for runtime source files once copied from the robot
