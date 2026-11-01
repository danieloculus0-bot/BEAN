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

Run only after the face is up and confirm camera/device permissions in its console output. The voice side uses `bean_voice.py` and sends `TALKFOR` updates to the face, but its automatic launch behavior has **not** been verified during this new Core installation.

**Avoid running `~/BEAN/run_bean.sh` at the same time as `~/BEAN-Core/bean_run.py`** without reviewing the legacy master process: that launcher starts a separate old `bean.py` and can duplicate audio or brain processes. Run face and tracker individually first.

## What is verified versus next

- **Verified locally:** Core runs on actual Jetson with persistent cognition events; CUDA llama.cpp binary compiled successfully; original face launcher and tracker arrangement documented from the previous Jetson setup.
- **Needs a fresh run result:** the original face/tracker re-launched alongside the new Core, Qwen download completion, CUDA model load/GPU offload, LLM completion, and Core-to-LLM/native speech/vision interoperability.
- **Preserve current work:** Do not replace `~/BEAN`, stop a working Core to launch the face, launch duplicate SQLite writers, or change audio/servo controls just to test display.

## Future installer work

The [Jetson packaging PR #205](https://github.com/danieloculus0-bot/BEAN/pull/205) includes automated CUDA compiler discovery, interrupted-build reuse, official model download, local inference service installation, and inference smoke tests. This runbook records the **actual hands-on path** separately so future installers can be compared against successful hardware observations. The installer does not yet package the locally preserved original Rev 1 face/voice/tracking scripts.
