# BEAN Jetson: local launch and recovery runbook

**Hardware:** NVIDIA Jetson Orin Nano Super, JetPack 6 / ARM64, Ubuntu.  
**First Core bring-up:** November 1, 2026.  
**Purpose:** Reproduce the actual operator-tested start sequence without replacing the earlier face/voice installation or starting multiple BEAN brains.

## Keep the existing installations separate

| Component | Existing Jetson path | Notes |
| --- | --- | --- |
| BEAN Python Core | `/home/bean/BEAN-Core` | Current cloned repository; `bean_run.py` |
| Core persistent memory | `/home/bean/bean_core_data/bean_memory.db` | Keep outside source directory. Never overwrite the active database. |
| Original BEAN Rev 1 interface | `/home/bean/BEAN` | Prior working Pygame face, tracking, and voice. **These scripts are local to that installation and not present on current BEAN GitHub main.** |
| Original interface Python venv | `/home/bean/beanenv` | Pygame, camera and legacy media dependencies already used by Rev 1. |
| Official llama.cpp source | `/home/bean/llama.cpp` | Local checkout, compiled with CUDA support. |
| Compiled llama-server | `/home/bean/llama.cpp/build/bin/llama-server` | 100% `Built target llama-server` observed Nov 1, 2026. |
| GGUF download | `/home/bean/bean_core_data/models/qwen2.5-1.5b-instruct-q4_k_m.gguf` | Qwen2.5 1.5B Instruct Q4_K_M; download initiated. |

All paths here are from the original `bean` Linux login and may be adjusted for other users. No existing binary/model installation should be deleted in order to follow this document.

## Terminal 1: current cognitive Core

The operator successfully launched the Core in `/home/bean/BEAN-Core` with persistent memory:

```bash
cd ~/BEAN-Core
mkdir -p ~/bean_core_data
BEAN_DB_PATH="$HOME/bean_core_data/bean_memory.db" python3 bean_run.py --hz 1
```

The process runs continuously. Do **not** launch it a second time if it is already running: this would create two writers to the same memory database.

On-device acceptance prior to language model integration: 10/10 boot readiness, clean 310-tick run, and scheduled world-model, reflection and memory-consolidation records in SQLite. See [the deployment evidence](JETSON_ON_DEVICE_BRINGUP_2026-11-01.md).

## Terminal 2: CUDA inference compiler and model

The Jetson already had CUDA 12.6, but CMake initially failed to find `nvcc` because `/usr/local/cuda/bin` was missing from PATH. The corrected configuration is:

```bash
PATH="/usr/local/cuda/bin:$PATH" cmake -S ~/llama.cpp -B ~/llama.cpp/build -DGGML_CUDA=ON -DCMAKE_CUDA_COMPILER=/usr/local/cuda/bin/nvcc -DCMAKE_CUDA_ARCHITECTURES=87 -DCMAKE_BUILD_TYPE=Release -DLLAMA_CURL=OFF
```

**Interrupted compilation? Resume without cloning or reconfiguring the source:**

```bash
PATH="/usr/local/cuda/bin:$PATH" cmake --build ~/llama.cpp/build --target llama-server -j2
```

This was successfully completed through `[100%] Built target llama-server`. Standard CMake incremental builds preserve completed object files after Ctrl+C.

**Download the official public GGUF model (resumable):**

```bash
mkdir -p ~/bean_core_data/models
curl -fL --retry 3 -C - -o ~/bean_core_data/models/qwen2.5-1.5b-instruct-q4_k_m.gguf https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct-GGUF/resolve/main/qwen2.5-1.5b-instruct-q4_k_m.gguf
```

When the download is complete, launch the CUDA model server in its own terminal. **This exact inference invocation is a next-step procedure; successful model response and GPU offload have not yet been confirmed on the operator's Jetson:**

```bash
~/llama.cpp/build/bin/llama-server --model ~/bean_core_data/models/qwen2.5-1.5b-instruct-q4_k_m.gguf --host 127.0.0.1 --port 8080 --alias bean-local --ctx-size 2048 --n-gpu-layers 99
```

Inspect its startup logs for the CUDA backend, GPU layer offload and model-load result. Once running, test the local HTTP interface with `python3 install/jetson_llm_smoke.py --port 8080` from a checkout that contains that script (Jetson packaging PR #205). The Python Core's existing `local_llamacpp` adapter expects `http://127.0.0.1:8080/v1/chat/completions` and model alias `bean-local`.

The model service and BEAN Core are separate processes. Loading a model alone does not prove that a native reasoning inbox command has invoked it.

## Terminal 3: original Pygame face

**Existing local launcher:**

```bash
bash ~/BEAN/run_face.sh
```

That script runs `~/beanenv/bin/python ~/BEAN/bean_face.py`. This is the **original Rev 1 face**, not the new Core or the planned updated centered-face UI. It may require an active graphical desktop session.

## Terminal 4: original camera tracker

The known original camera tracker script is `~/BEAN/bean_tracker.py`. It sends normalized tracking coordinates by UDP to port **5006**, which the old face receives. To run it separately:

```bash
~/beanenv/bin/python ~/BEAN/bean_tracker.py
```

**Manual tracker activation (confirmed working on this Jetson in March 2026):** In the tracker window, press **Space**, drag a rectangle around the target (face or object), then press **Enter** to confirm the ROI. Tracking begins after confirmation; press **Q** to quit. Simply launching the tracker does not select a target.

Earlier working implementation used OpenCV 4.13/contrib `cv2.legacy.TrackerCSRT_create`. The webcam was identified as `web cam 1080p` with `/dev/video0` and `/dev/video1` enumerated; device selection can change after a reboot. If the tracker crashes, run it from a terminal with the command above and inspect the traceback before changing dependencies. The previously successful Python environment was `~/beanenv`, with `opencv-contrib-python` installed.

Run only after the face is up and confirm camera/device permissions in its console output. The voice side uses `bean_voice.py` and sends `TALKFOR` updates to the face, but its automatic launch behavior has **not** been verified during this new Core installation.

**Avoid running `~/BEAN/run_bean.sh` at the same time as `~/BEAN-Core/bean_run.py`** without reviewing the legacy master process: that launcher starts a separate old `bean.py` and can duplicate audio or brain processes. Run face and tracker individually first.

## Audio and speech recovery: known Jetson hardware

The earlier Jetson Rev 1 installation **did** capture speech and produce audible output. This matters because audio is often configured differently after device re-enumeration.

**Previously working equipment and settings (March-April 2026):**

| Component | Verified earlier | Notes |
| --- | --- | --- |
| Microphone | USB webcam named `web cam 1080p: USB Audio` | Worked as ALSA `plughw:0,0` in the final saved voice configuration. Earlier boots enumerated it as `hw:1,0` and `hw:2,0`. |
| Speech recognition | Offline Vosk | Model directory `/home/bean/vosk-model-small-en-us-0.15`; 16,000 Hz, mono (`CHANNELS=1`). |
| Speaker output | Jetson HDMI | Working final playback `plughw:1,3` using `espeak-ng --stdout` piped to `aplay`. Earlier successful HDMI tests also used `plughw:0,3`; numbering can change. |
| Rev 1 voice source | `/home/bean/BEAN/bean_voice.py` | Run using `/home/bean/beanenv/bin/python`. The prior script combined Vosk, speech output and **Ollama conversational requests**, so starting it alongside the new llama.cpp setup may produce two conversation paths. |
| Face speaking indicator | UDP `TALKFOR:<duration>` | Legacy voice signaled the face; UDP talk port 5005 was used in the saved voice script. Camera tracker coordinates are separate on port 5006. |

**These device numbers are past working values, not permanent hardware IDs or proof of today's routing.** Linux/JetPack supplies the audio kernel drivers; the userspace requirements include ALSA utilities, PortAudio for `sounddevice`, and a speech synthesizer such as `espeak-ng`. Installing an ALSA package alone does not guarantee the HDMI sink or microphone is selected.

Check which sound devices the current Jetson exposes, without stopping BEAN Core:

```bash
arecord -l
aplay -l
cat /proc/asound/cards
```

Also inspect the Python microphone list if the old `beanenv` exists:

```bash
~/beanenv/bin/python -c 'import sounddevice as sd; print(sd.query_devices())'
```

Test the webcam microphone using the **currently displayed** ALSA card/device pair. On the final previously working setup this was:

```bash
arecord -D plughw:0,0 -f S16_LE -r 16000 -c 1 -d 5 /tmp/bean_audio_test.wav
```

Listen back through the **currently listed** HDMI playback route. In the last known working configuration:

```bash
aplay -D plughw:1,3 /tmp/bean_audio_test.wav
```

If playback is silent, confirm HDMI audio is enabled and the correct output device is selected in the desktop/system audio settings. With the proper device from `aplay -l`, the prior working synthesized speech check was:

```bash
espeak-ng -v en-gb --stdout "BEAN audio check" | aplay -D plughw:1,3
```

**Rev 1 speech launch (separate process):**

```bash
~/beanenv/bin/python ~/BEAN/bean_voice.py
```

Launch this only when you intend to use the old voice pipeline. Its historical version talked to **Ollama** and would not automatically use the new CUDA llama.cpp model or Core memory. Verify the current source and route before treating speech as connected to the new Core.

**Piper** was part of older BEAN text-to-speech experiments, but the last *verified* complete microphone/speaker route used **Vosk + espeak-ng + ALSA**, not a documented working Piper configuration. Preserve any current Piper voices/settings; don't replace or rename them just to run the audio diagnostic.

The development installer now includes a separate read-only audio diagnostics step on its packaging branch, with optional installation of missing ALSA/PortAudio/espeak-ng userspace prerequisites. It does **not** reconfigure kernel drivers, force a default sound card, or start the legacy Ollama voice process.

## What is verified versus next

- **Verified locally:** Core runs on actual Jetson with persistent cognition events; CUDA llama.cpp binary compiled successfully; original face launcher and tracker arrangement documented from the previous Jetson setup.
- **Confirmed again November 1, 2026:** the original Rev 1 face and manual-target CSRT tracker are working on the Jetson together (operator-reported). Tracking uses Space, drag target ROI, then Enter. This confirms the original face/tracker pairing, not automatic integration with the new Python Core.
- **Needs a fresh run result:** Qwen download completion, CUDA model load/GPU offload, LLM completion, and Core-to-LLM/native speech/vision interoperability.
- **Preserve current work:** Do not replace `~/BEAN`, stop a working Core to launch the face, launch duplicate SQLite writers, or change audio/servo controls just to test display.

## Future installer work

The [Jetson packaging PR #205](https://github.com/danieloculus0-bot/BEAN/pull/205) includes automated CUDA compiler discovery, interrupted-build reuse, official model download, local inference service installation, and inference smoke tests. This runbook records the **actual hands-on path** separately so future installers can be compared against successful hardware observations. The installer does not yet package the locally preserved original Rev 1 face/voice/tracking scripts.
