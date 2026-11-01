# BEAN on Jetson: inspect first, then install

This is a packaging update of the existing BEAN Python runtime, **not a new BEAN brain**. Run against JetPack 6 on an ARM64 Jetson. Existing BEAN memory, model files and motion experiments are not replaced.

## One-command diagnostic (from your existing BEAN repository directory)

This downloads the diagnostic source from a review branch without checking that branch out, does not install packages or edit the current checkout, and runs a one-tick smoke with disposable SQLite storage.

~~~sh
git fetch origin feature/jetson-package-preflight-20261101 && git show FETCH_HEAD:scripts/jetson_runtime_audit.py | python3 - --smoke
~~~

The diagnostic reports architecture, Python interpreter and package presence, active service state, existing camera/serial device names, loopback inference-server response, statically registered inbox commands and periodic tick handlers, and actual one-tick Core startup/import outcomes.

**Do not mistake the module count for active integration.** Static registration, successful imports, and synthetic smoke tests do not prove that vision, audio, learning, or motion actually execute together. The isolated smoke disables model inference and hardware output and uses the example body registry.

It does not read or upload private memory contents or secrets. Review terminal output before sharing it outside your trusted workspace.

## Packaging after checking the results

The existing installer remains install/jetson_brain_install.sh. This branch makes its paths use the current clone and Linux login instead of requiring a dedicated /home/bean account. It renders an actual systemd unit, preserves an existing /etc/bean/bean.env, creates a persistent data directory outside the repository, and installs lightweight Python dependencies in .venv.

The installer does not start/restart the BEAN brain process. It **does** install and start the independent local llama.cpp model server by default, after building CUDA support and downloading the public Qwen2.5 1.5B Instruct Q4_K_M GGUF model. Do not run it until the diagnostic has identified the current runtime state and you have checked which copy of BEAN is running.

When ready to test this branch in an isolated checkout:

~~~sh
git fetch origin feature/jetson-package-preflight-20261101
git worktree add ../BEAN-jetson-review FETCH_HEAD
cd ../BEAN-jetson-review
bash install/jetson_brain_install.sh
~~~

The install script automatically searches `/usr/local/cuda/bin/nvcc` and `/usr/local/cuda-*/bin/nvcc`, adds the compiler directory to PATH, and explicitly configures CMake with `CMAKE_CUDA_COMPILER` and `CMAKE_CUDA_ARCHITECTURES=87` for Jetson Orin Nano. It uses a dedicated `~/llama.cpp/build-bean-cuda` directory, preserving any earlier incomplete `~/llama.cpp/build` attempt. Missing basic build tools (`cmake`, `g++`, `git`, `make`, `curl`) are installed through the system package manager when needed. If the NVIDIA CUDA toolkit itself is absent, installation stops with a clear JetPack requirement rather than silently building a slower CPU-only alternative.

The installer reuses existing llama.cpp source and an existing GGUF model instead of redownloading them. It builds `llama-server`, downloads the official Qwen2.5 1.5B Instruct GGUF only when needed, creates a `bean-llamacpp.service` bound to `127.0.0.1:8080`, and starts it. The server advertises `--alias bean-local` for BEAN's existing local reasoning adapter. After startup, `install/jetson_llm_smoke.py` checks the model server's `/health` endpoint and requests a real completion using BEAN's expected alias. A successful result verifies the local inference provider, but not yet BEAN's reasoning handler or long-term learning. This remains unverified until it is run on the Jetson.

**Configuration switches:** `BEAN_LLM_INSTALL=0` skips the inference compiler step; `BEAN_LLM_START=0` installs without starting; `BEAN_LLM_DOWNLOAD=0` builds but does not download a model; `BEAN_LLM_SMOKE=0` skips the live completion check; `BEAN_GGUF_PATH=/absolute/path/model.gguf` uses an existing GGUF; `BEAN_BUILD_JOBS=2` controls compilation parallelism; `BEAN_NVCC=/path/to/nvcc` overrides compiler discovery; `BEAN_LLM_REBUILD=1` forces rebuild. Existing `/etc/bean/bean.env` and memory records are retained without being overwritten.

No automatic physical actuation: existing BEAN Core uses MotionSimulator and the real Arduino motion bridge remains in separate PR #204. Existing hardware-specific body calibration and voice/camera modules require separate confirmation on the installed Jetson.

## Verification labels

- **Source validation:** automated tests check environment/unit rendering, shell syntax, compiler discovery contracts and inventory behavior. CI results must be checked at the exact head commit.
- **Jetson runtime:** NOT VERIFIED until the target terminal audit runs.
- **Local model integration:** NOT VERIFIED until the installer’s live completion check passes on the Jetson and BEAN's native reasoning handler is exercised.
- **Real motor and manipulation control:** NOT VERIFIED; not activated by this package.
