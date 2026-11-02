# BEAN Jetson: verified local cognition deployment milestone

**Date:** November 1, 2026  
**Status:** Operator-tested on NVIDIA Jetson Orin Nano Super, JetPack 6 / Ubuntu ARM64. Source-code release and physical robot integration are separate milestones.  
**Provenance:** Observations from two Jetson terminal troubleshooting sessions, reviewed as operator-provided output. This document is not a remote copy of the Jetson's local databases or untracked legacy programs.

## Deployed components and observed results

| Component | Verified observation | Scope |
| --- | --- | --- |
| Python Core | BEAN Core **v0.13.1** passed **10/10** boot-readiness checks and a **310-tick** test. | Real ARM64 device, not merely CI simulation. |
| Durable runtime memory | Boot #2 recovered **2,361 events**. After a keyboard-interrupt shutdown, Boot #3 recovered **2,566 events**, with prior termination reported as `keyboard_interrupt`. | These are on-device persisted event counts at the respective boots, not independent learning scores. |
| CUDA model build | The Jetson compiled CUDA-enabled `llama.cpp` to **100%**, then loaded **Qwen2.5 1.5B Instruct Q4_K_M** using a local `llama-server` bound to `127.0.0.1:8080`, alias `bean-local`. | JetPack 6, CUDA 12.6, compute architecture 87. |
| API and adapter | `/health` returned HTTP **200**, a local chat call returned `BEAN ONLINE`, and the Core's `LocalLlamaCppProvider` returned `BEAN ADAPTER ONLINE`. | A short four-token sample yielded about **15.48 tokens/s**; this is not a sustained throughput benchmark. |
| Isolated native reasoning | `NativeReasoningService` returned `BEAN MEMORY ONLINE`, created an inference receipt, and reopened a separate test journal with **one persisted receipt**. | Separate test SQLite database, not the live runtime's journal. |
| Live Core cognition | An actual `cognition_reason` task with reference `live_core_test` returned **`BEAN CORE ONLINE`**. A subsequent **read-only** query of the live reasoning SQLite journal recovered the matching inference receipt. | Confirms live Core command processing, local model inference and persistent reasoning record together. The raw receipt hash and private SQLite bytes are not published. |
| CUDA runtime | The serving process was launched with `--n-gpu-layers 99`; `libggml-cuda`, `libcuda`, `libcublas`, `libcublasLt` and CUDA runtime libraries were observed loaded. | These checks establish library availability and the *requested* layer count, not exact actual layer placement. |
| GPU activity during completion | Concurrent `tegrastats` showed `GR3D_FREQ` of **99%, 92%, 93%, 92%, 99%** while a real chat request returned HTTP **200**; utilization then returned near zero. | Confirms GPU acceleration during Qwen generation. Exact GPU-offloaded layer count remains unverified from startup logs. |
| Original interfaces | Original Pygame face and manual OpenCV CSRT camera tracking have worked separately on Jetson. Legacy voice source has been inspected. | The old face, camera, microphone, speech output and current Core have **not** been proven operating together. |

## Integration architecture actually inspected

- The original local `~/BEAN/bean_voice.py` uses Vosk recognition, ALSA capture/playback, Piper synthesis, and UDP `TALKFOR` to animate the original Pygame face. It still calls **Ollama** in `ask_ollama()`. Do not describe it as already wired to Core's Qwen instance. Legacy source under `~/BEAN` is a local non-Git installation and has **not** been backed up in this public repository.
- `bean/modules/builtin.py` registers `cognition_reason`, which invokes the selected `NativeReasoningService.reason(domain, task_ref, query)`. It returns `answer`, `receipt_id`, provider information, decision context and a journal reference.
- `bean/runtime/inbox.py` accepts bounded, atomically placed JSON commands and archives processed or failed files. The runtime registers `inbox.poll(session_uuid)` via `bean/runtime/tick_handlers.py`.
- Inspection found **no response-file/outbox API**. The tick-handler lambda currently ignores the returned result, so voice has no demonstrated external answer-retrieval path. A request-correlated response channel is the **next proposed integration**, not a completed feature.
- No physical motors were connected or activated. Core continues to use the *example* body registry (9 joints, 4 limbs).

## Publication boundaries and recovery

This publication preserves the verified **source-repository milestone and evidence**, including failure and uncertainty boundaries. It does **not** export the Jetson's `bean_memory.db`, reasoning databases, private inference contents, downloaded GGUF, CUDA build binaries, or locally installed Rev 1 face/voice/tracker scripts. Those remain on-device and require a separate operator-controlled backup. An earlier `git status --short` showed no tracked Core source modifications and only a processed inbox runtime artifact as untracked; no matching on-device Git commit SHA was collected, so do not claim a byte-for-byte device snapshot.

**Runbook:** [Jetson local startup and recovery](JETSON_LOCAL_STARTUP_RUNBOOK.md). **Historical bring-up:** [initial deployment evidence](JETSON_ON_DEVICE_BRINGUP_2026-11-01.md).

**Source and CI boundary as of the publication review:** the previous `main` revision `1087b6942ffd` had a **successful GitHub Pages deployment** but a **failing full-core regression workflow**. PR [#205](https://github.com/danieloculus0-bot/BEAN/pull/205), the automated Jetson installer, remained **draft and not fully on-device verified**. This evidence report does not merge that PR or represent its installer as released.

## Next independently testable integration

1. Preserve the running BEAN Core, model server, SQLite stores and known-working old interface.
2. Add a bounded request-correlated answer channel to the **existing** Core inbox rather than a second local chatbot or reasoning database.
3. Route Vosk-transcribed text into the live `cognition_reason` command, retrieve `answer` reliably, and pass it to the existing Piper/ALSA/face-talk path.
4. Independently test speech in, persisted Core inference, spoken answer and face indication. Then test tracker; separately address physical motors.
5. Confirm exact offloaded layer count from model-load logs when available. Avoid needlessly restarting the working inference server.

**Evidence rating:** real on-device cognition + CUDA inference verified; spoken end-to-end integration **not yet verified**; physical actuation **not tested**.
