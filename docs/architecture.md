# BEAN Architecture

## Target stack

BEAN is intended to use split compute instead of forcing one board to do everything.

## High-level compute: Jetson Orin Nano

Responsibilities:

- Vision
- Object tracking
- Face/UI behavior
- Voice input/output
- Local LLM where practical
- Cloud LLM bridge when needed
- Behavior/orchestration
- Command generation for motion host

Known current Jetson state:

- Hostname: `BEAN`
- Project directory: `/home/bean/BEAN`
- Virtual environment: `/home/bean/beanenv`
- Python: 3.10.12
- OpenCV working
- Vosk working
- pygame face working
- Ollama installed/tested, but memory-limited on larger models

## Motion host: Raspberry Pi 4

Responsibilities:

- Receive motion commands from Jetson over hardwired Ethernet
- Maintain connection health/deadman timeout
- Bridge commands to Arduino layer
- Return status/telemetry to Jetson
- Keep motion stack isolated from AI/vision crashes

Planned protocol style:

- Transport: TCP over hardwired Ethernet
- Command style: simple JSON lines or compact text commands
- Minimum commands: `STOP`, `FWD`, `REV`, `LEFT`, `RIGHT`, `TURN`, `SPEED`, `STATUS`
- Required safety: timeout to stop if Jetson stops sending commands

## Real-time control: Arduino Nano layer

Responsibilities:

- Motor PWM/direction control
- Encoder reading
- Servo timing
- Proximity sensor reads
- Hardware failsafe logic
- Emergency stop state

Reasoning:

The Arduino layer keeps timing-critical hardware control away from Linux scheduling, UI threads, LLM stalls, and other nonsense that will absolutely happen at the worst possible moment.

## Future web/phone control

Planned Flask-style control bridge:

- `/move`
- `/arm`
- `/speak`
- `/status`
- `/stop`

This is useful for bench testing before autonomy.

## Future autonomy layers

Sequence should stay practical:

1. Manual command control
2. Deadman stop
3. Encoder feedback
4. Basic obstacle detection
5. LiDAR mapping or local avoidance
6. Behavior/autonomy overlay

Do not start with LiDAR until the robot can actually move under reliable command control.
