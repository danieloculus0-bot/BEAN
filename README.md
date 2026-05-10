# BEAN

BEAN is a modular telepresence and office rover robot project. The build direction is a mostly 3D-printable, maker-friendly robotics platform with Jetson-class AI, Raspberry Pi compatibility, Arduino-class real-time control, expressive face/UI behavior, local voice interaction, object tracking, and eventually basic roaming.

Current status: active prototype. The repo is being initialized as the canonical map for hardware, software, capabilities, blockers, and next build tasks.

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
- Motion: not rolling yet
- LiDAR: planned after rolling base works

## Current confirmed capabilities

- Animated pygame face boots and renders eyes, blinking, and mouth movement.
- Voice stack can load Vosk, detect wake word `hello`, listen for follow-up commands, and speak responses.
- The voice script can pulse the face mouth through UDP `TALKFOR` messages on localhost port `5005`.
- OpenCV camera test succeeded.
- Manual object tracking was confirmed in prior development notes, with tracker data sent over UDP to drive face/eye target behavior.
- Local Ollama inference was tested, but larger models caused CUDA memory failures on the Jetson.

## Intended architecture

BEAN should use a split-compute stack:

- Jetson Orin Nano: LLM, vision, tracking, speech, behavior, face/UI.
- Raspberry Pi 4: networked motion host over hardwired Ethernet.
- Arduino Nano layer: motor control, encoder handling, servo/sensor timing, hardware failsafes.
- Future web/phone control: Flask-style control bridge for movement, arm, speak, and status endpoints.

## Repo purpose

This repo should become the public project home for:

- Hardware inventory
- Current build state
- Runtime scripts
- Architecture notes
- Motion protocol
- Setup/install steps
- Known issues
- Roadmap
- Future CAD/STL/mechanical files

## What this is not yet

This is not yet a polished robot runtime package. Current BEAN is a working prototype stack with several validated subsystems and some known ugly little gremlins, especially audio routing, local model memory use, and motion integration.

## Documentation map

- `docs/current-build-map.md` - Full recovered build map
- `docs/architecture.md` - Planned compute and control architecture
- `docs/hardware-inventory.md` - Known hardware and purchased parts
- `docs/capability-matrix.md` - Working, partial, planned, and blocked capabilities
- `docs/known-issues.md` - Current bugs and technical blockers
- `docs/roadmap.md` - Practical next build phases
- `runtime/README.md` - Placeholder for runtime source files once copied from the robot
