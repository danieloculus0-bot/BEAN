# BEAN Current Build Map

Recovered from prior build notes, uploaded scripts, and runtime logs.

## Identity

- Project name: BEAN
- Product type: telepresence / office rover robot
- Build phase: active prototype
- Design target: modular, mostly 3D-printable, low-machining robot platform
- Main goal: useful office rover with expressive interaction, basic autonomy, and upgradeable compute

## Current robot computer state

- Machine: NVIDIA Jetson Orin Nano Super Developer Kit
- Hostname: `BEAN`
- OS: Ubuntu / JetPack
- Python: 3.10.12
- Virtual environment: `/home/bean/beanenv`
- Project folder: `/home/bean/BEAN`
- Confirmed run command examples:
  - `~/beanenv/bin/python ~/BEAN/bean_face.py`
  - `~/beanenv/bin/python ~/BEAN/bean_tracker.py`
  - `~/beanenv/bin/python ~/BEAN/bean_voice.py`
  - `~/beanenv/bin/python ~/BEAN/bean_master.py`

## Current runtime files known from prior work

- `bean_face.py` - standalone pygame face test, 1024x600, blinking eyes, simple smile
- `bean_tracker.py` - manual object tracking, OpenCV-based, sends normalized target information over UDP
- `bean_voice.py` - current voice loop using Vosk, wake word, Ollama HTTP API, espeak-ng, ALSA devices, UDP talk pulses
- `bean_master.py` - older integrated face + voice + Ollama prototype
- `bean.py` - object-oriented prototype runtime with pygame face, Vosk, Ollama, pico2wave
- `run_face.sh` - launcher for face script under `~/beanenv`
- `run_bean.sh` - launcher for older main runtime under `~/beanenv`

## Current voice stack

- STT: Vosk
- Vosk model path: `/home/bean/vosk-model-small-en-us-0.15`
- Wake word: `hello`
- Follow-up timeout: 15 seconds in current `bean_voice.py`
- Capture device in current file: `plughw:0,0`
- Playback device in current file: `plughw:1,3`
- Rate: 16000 Hz
- Channels: 1
- LLM endpoint: `http://127.0.0.1:11434/api/generate`
- Current local model target: `qwen2.5:1.5b-instruct`
- Earlier model target: `tinyllama`
- TTS: current `bean_voice.py` uses `espeak-ng` piped to `aplay`
- Earlier TTS: `pico2wave` with `/tmp/bean.wav` or `/tmp/bean_tts.wav`

## Current face stack

- Rendering library: pygame
- Known screen sizes used:
  - 1024x600 for standalone face
  - 600x300 in older `bean_master.py`
  - 1024x600 in `bean.py`
- Known face capabilities:
  - eyes
  - blinking
  - pupils
  - mouth animation while talking
  - UDP talk pulse support in current voice script through `TALKFOR:<duration>` to `127.0.0.1:5005`

## Current vision/tracking stack

- Camera: USB webcam
- OpenCV camera test succeeded and saved `bean_cam_test.jpg`
- Video devices existed as `/dev/video0` and `/dev/video1`
- OpenCV 4.13.0 and contrib tracking installed
- Tracker type: `cv2.legacy.TrackerCSRT_create`
- Manual ROI tracking confirmed working
- Tracker sends normalized target position over UDP, previously noted as port `5006`
- Face receives tracker target data to move eyes/attention

## Current hardware inventory

- Jetson Orin Nano Super Developer Kit
- Raspberry Pi 4B, 4GB
- Arduino Nano x3
- USB webcam with mic
- USB powered speakers / monitor speakers
- 10-inch Android tablet, initially planned for robot face/display
- 555 motors with gearboxes, corrected from older 775 motor baseline
- BTS7960 43A H-bridge drivers
- Milwaukee M12 battery adapters
- Fused distribution / fuse box with negative bus
- PCA9685 16-channel servo driver
- MG995 metal gear servos
- Emergency stop switches
- R188ZZ bearings
- PETG filament
- Stainless metric fastener assortment
- Brass heat-set insert kit
- Neodymium magnets

## Motion status

- Current prototype cannot move yet.
- User wants BEAN rolling before adding LiDAR.
- Planned split:
  - Jetson handles high-level commands, perception, voice, and behavior.
  - Raspberry Pi 4 acts as hardwired Ethernet motion host.
  - Arduino handles real-time motor, encoder, servo, and failsafe control.

## Power and mechanical direction

- Battery platform: Milwaukee M12 adapters
- Distribution: fused low-voltage distribution
- Design philosophy:
  - 3D printed replaceable parts
  - shoulder bolts / bearings where practical
  - minimal machining
  - modular repairable assemblies
  - prototype behavior before fancy architecture

## Local model status

- Tiny local models worked enough to test voice loops.
- Qwen2.5 1.5B is the current practical local target.
- Qwen2.5 7B caused CUDA out-of-memory failures on the Jetson.
- Future approach should include model-size guards and fallback behavior.

## Current blockers

- Audio routing/device indexing changes between sessions.
- Older `sounddevice` stack hit invalid channel/device mismatch issues.
- Larger Ollama models can crash or fail due to CUDA memory allocation.
- pygame face loop has previously segfaulted on shutdown in threaded integrated runtime.
- Motion stack is not wired into a working drive base yet.
- No LiDAR integration yet.

## Current next practical milestone

Get the rolling base working with a minimal Jetson-to-Pi-to-Arduino command path:

1. Pi motion host accepts simple commands over hardwired Ethernet.
2. Arduino receives simple motor commands from Pi.
3. Jetson sends forward / reverse / left / right / stop commands.
4. Emergency stop and deadman timeout work before autonomy.
5. Only then add LiDAR or richer autonomy.
