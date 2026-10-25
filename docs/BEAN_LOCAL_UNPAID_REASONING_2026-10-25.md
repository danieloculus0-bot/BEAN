# BEAN Core: On-device Qwen reasoning, no model API charges

**Core purpose:** BEAN retains one owner of reasoning strategy, memory, source-provenance, outcomes, and training. Qwen3 is **downloadable local model weights** providing natural-language inference through `llama.cpp` running on your own computer. The model does not replace BEAN's symbolic learner or its persisted feedback journal. No Ollama or paid API is required.

**Code:** `bean/reasoning/local_llamacpp_provider.py`. The regular `bean_run.py` selects `BEAN_REASONING_PROVIDER=local_llamacpp` by default. It makes **no model or network call on startup**. To explicitly disable any language-model dependency and retain symbolic reasoning only, set `BEAN_REASONING_PROVIDER` to an empty string. Previous OpenAI/OpenRouter/Ollama options remain explicit choices, never fallback destinations.

## Windows PowerShell — once for model setup

1. Install open-source llama.cpp:
   ```powershell
   winget install llama.cpp
   ```
2. On a modest PC, start with the smaller Apache-2.0 Qwen3 1.7B Q4_K_M weights. With a more capable PC, try Qwen3 4B Q4_K_M for better open-ended reasoning. Run one of these commands in a separate PowerShell terminal:
   ```powershell
   # Smaller CPU/RAM option:
   llama-server -hf ggml-org/Qwen3-1.7B-GGUF:Q4_K_M --alias bean-local --host 127.0.0.1 --port 8080 -c 4096

   # OR, stronger model:
   llama-server -hf Qwen/Qwen3-4B-GGUF:Q4_K_M --alias bean-local --host 127.0.0.1 --port 8080 -c 4096
   ```
   Some llama.cpp packages invoke this as `llama serve` instead; follow the installed binary's help if `llama-server` is not in PATH. The weights are downloaded on first use. Subsequent local inference does **not** use an external provider or incur token charges. RAM needs and speed depend on the quantization, model, CPU/GPU and requested context.
3. Run BEAN normally:
   ```powershell
   $env:BEAN_REASONING_PROVIDER = "local_llamacpp"
   $env:BEAN_LOCAL_LLM_URL = "http://127.0.0.1:8080"
   $env:BEAN_LOCAL_LLM_MODEL = "bean-local"
   python bean_run.py
   ```

BEAN's normal inbox exposes `reasoning_local` (its own learned symbolic rules), `reasoning_auto` (symbolic first, then local model if available), `reasoning_reason`, `reasoning_generate`, `reasoning_feedback` and the existing Bridge/web research commands. The local language model is **not a new ledger**.

## Behavior

- For tasks where BEAN already knows a validated symbolic procedure, `reasoning_auto` uses it with no model call.
- Otherwise it invokes local Qwen. If BEAN has a measured contextual strategy, that exact selected memory is sent to Qwen. If the domain has no measured strategy, BEAN records a cold local-model inference with an explicit `unselected_local_model_baseline` packet.
- Local answers are journaled with `provider_kind=local_llamacpp`, served model ID, context digest, receipt ID and `verified_outcome=false`. The existing feedback machinery accepts these receipts for source-linked corrections and subsequent strategy comparisons.
- If llama.cpp isn't running, is still loading weights, times out, returns invalid output or a wrong model alias, BEAN records a failed inference attempt and explicitly says the local model is unavailable. It does **not** switch to OpenRouter or any paid service.
- Only `127.0.0.1` or `[::1]` HTTP hosts are accepted. Proxies are bypassed; redirects forbidden. No cloud model API key, credit, or billing is required. The local port should not be exposed to a LAN or internet.
- The local model weights can later be replaced with a stronger GGUF or accelerated by a compatible GPU without changing BEAN's lessons. BEAN's provider interface remains stable.

## Scope and evidence

`python -m unittest bean.tests.test_local_llamacpp_reasoning -v` runs offline loopback HTTP tests on Windows/Linux and checks symbolic-first, no cloud/network leakage, real event journal, restart/feedback, chosen memory, failure and endpoint validation. These tests run a small **test HTTP server**, not a downloaded Qwen neural model. Model accuracy and response latency require genuine model-weight trials using the user's chosen hardware.

This is genuine no-cloud local inference **when a GGUF model and llama.cpp server run locally**, not a new foundation neural network trained from scratch. Qwen weights remain pretrained; BEAN's own learning loop still improves retrieval, rule selection, feedback, and reasoning context. Training or fine-tuning the model weights itself is a separate hardware-intensive research path.

Official reference: [llama.cpp server and loopback API](https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md), [official Qwen3 GGUF model](https://huggingface.co/Qwen/Qwen3-4B-GGUF), [small official-community GGUF](https://huggingface.co/ggml-org/Qwen3-1.7B-GGUF).
