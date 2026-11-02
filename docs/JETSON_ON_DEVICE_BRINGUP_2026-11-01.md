# BEAN Core: first on-device Jetson runtime deployment

**Observed November 1, 2026.** **Historical first-boot checkpoint:** later on the same day the local Qwen/CUDA backend and live `cognition_reason` receipt were also verified; see the [subsequent deployment milestone](JETSON_DEPLOYMENT_MILESTONE_2026-11-01.md). This is an operator-reported terminal acceptance record for a real NVIDIA Jetson Orin Nano Super running JetPack/L4T, Ubuntu/Linux ARM64 (aarch64) and Python 3.10.12. It documents the first successful local Core bring-up, **not** a completed autonomous robot or published end-to-end inference benchmark.

## Verified from operator-provided console output

1. The current Python BEAN Core repository was cloned into a separate directory on the Jetson. Older Rev 1 face/voice/tracker programs were left intact.
2. `python3 -m bean.runtime.boot_readiness --temp` reported **success: true**, zero errors and **10/10 passing checks**: `boundary_sync`, `capability_sync`, `core_memory`, `event_log`, `hypothesis_probe`, `origin_covenant`, `reasoning_probe`, `relationship_schema`, `runtime_proof` and `wisdom_probe`. The platform report explicitly identified the Orin Nano Super and Jetson/L4T.
3. `python3 bean_run.py --ticks 3 --hz 10` started BEAN Core **v0.13.1**, initialized its sample body registry and shut down cleanly.
4. `python3 bean_run.py --ticks 310 --hz 20` also completed and shut down cleanly. A subsequent read-only query against that test run's temporary SQLite database found **13 world-model updates, 10 memory consolidations, 5 reflections, 1 self-model update, 32 body-state events and zero logged error events**.
5. The operator started the Core continuously at 1 Hz with a **persistent SQLite database outside the source checkout**. While running, a separate terminal confirmed **27 database events**, including 6 world-model updates, 4 memory consolidations, 2 reflections, and **zero logged error events**. This verifies working scheduled cognitive routines and persisted records at the time of the check. It does not establish an uninterrupted uptime guarantee.

## What was not yet proven at the first-boot checkpoint

- **Local language inference:** The installed Ollama models were found unreliable, and the existing llama.cpp provider had no running server on port 8080. A separate CUDA llama.cpp build was attempted but CMake could not find `nvcc` despite CUDA 12.6 being present. A compiler-path/automated model installation change is being developed in [Jetson packaging PR #205](https://github.com/danieloculus0-bot/BEAN/pull/205). **Neither model-server success nor model-generated BEAN dialogue is claimed here.**
- **Physical robot control:** The Core loaded an **example** registry of 9 joints and 4 limbs. Its servo outputs were not connected or tested. The separate Arduino motion bridge remains [PR #204](https://github.com/danieloculus0-bot/BEAN/pull/204).
- **Rev 1 media interfaces:** Historical voice, face and visual-tracking source was located on the device. Functional end-to-end integration with the new BEAN Core is **not demonstrated** by this acceptance record.
- **Autonomous general learning or self-awareness:** Periodic reflection and event logging do not prove either.

## Deployment significance

**BEAN's Python cognitive Core has genuinely been deployed and executed on the intended Jetson ARM64 hardware with persistent memory.** This is beyond an x86 GitHub CI simulation. Continued work is to connect a working local inference engine and the preexisting media interfaces into the same runtime, with measured tests for each path.

This report contains only non-identifying, operator-shared summary counts and platform facts. No microphone recordings, private SQLite contents, identity/session UUIDs, environment variables, proprietary drawings, company records, or credentials are published.
