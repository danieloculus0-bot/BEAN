#!/usr/bin/env bash
# Install BEAN's local llama.cpp server for Jetson ARM64/CUDA.
# Reuses existing source and leaves BEAN's Python runtime and memory alone.
set -euo pipefail

say() { printf '\n==> %s\n' "$*"; }
fail() { printf 'BEAN local inference install failed: %s\n' "$*" >&2; exit 1; }

BEAN_USER="${BEAN_USER:-${SUDO_USER:-$(id -un)}}"
BEAN_GROUP="${BEAN_GROUP:-$(id -gn "$BEAN_USER")}"
USER_HOME="$(getent passwd "$BEAN_USER" | cut -d: -f6)"
[[ -n "$USER_HOME" ]] || fail "Cannot find Linux home for user $BEAN_USER"
BEAN_HOME="${BEAN_HOME:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)}"
BEAN_DATA_DIR="${BEAN_DATA_DIR:-$USER_HOME/bean_core_data}"
BEAN_LOG_DIR="${BEAN_LOG_DIR:-$USER_HOME/bean_logs}"
BEAN_ENV_FILE="${ENV_FILE:-/etc/bean/bean.env}"
LLAMA_CPP_DIR="${BEAN_LLAMA_CPP_DIR:-$USER_HOME/llama.cpp}"
# Prefer an existing, *successfully configured* CUDA build so an interrupted
# compile resumes from completed object files rather than rebuilding from zero.
# A failed/incomplete CMake configure has no generated build-system files and
# falls back to a separate clean build directory without deleting anything.
if [[ -n "${BEAN_LLAMA_BUILD_DIR:-}" ]]; then
  LLAMA_BUILD_DIR="$BEAN_LLAMA_BUILD_DIR"
elif [[ -f "$LLAMA_CPP_DIR/build/CMakeCache.txt" ]] &&
     { [[ -f "$LLAMA_CPP_DIR/build/Makefile" ]] ||
       [[ -f "$LLAMA_CPP_DIR/build/build.ninja" ]]; } &&
     grep -qxE 'GGML_CUDA:(BOOL|UNINITIALIZED)=ON' "$LLAMA_CPP_DIR/build/CMakeCache.txt" &&
     grep -qxF "CMAKE_HOME_DIRECTORY:INTERNAL=$LLAMA_CPP_DIR" "$LLAMA_CPP_DIR/build/CMakeCache.txt"; then
  LLAMA_BUILD_DIR="$LLAMA_CPP_DIR/build"
else
  LLAMA_BUILD_DIR="$LLAMA_CPP_DIR/build-bean-cuda"
fi
LLAMA_SERVER="$LLAMA_BUILD_DIR/bin/llama-server"
MODEL_PATH="${BEAN_GGUF_PATH:-$BEAN_DATA_DIR/models/qwen2.5-1.5b-instruct-q4_k_m.gguf}"
MODEL_URL="${BEAN_GGUF_URL:-https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct-GGUF/resolve/main/qwen2.5-1.5b-instruct-q4_k_m.gguf}"
MODEL_DOWNLOAD="${BEAN_LLM_DOWNLOAD:-1}"
LLM_START="${BEAN_LLM_START:-1}"
LLM_PORT="${BEAN_LLM_PORT:-8080}"
CUDA_ARCH="${BEAN_CUDA_ARCH:-87}"
BUILD_JOBS="${BEAN_BUILD_JOBS:-2}"
SERVICE_FILE="${BEAN_LLM_SERVICE_FILE:-/etc/systemd/system/bean-llamacpp.service}"

[[ -f "$BEAN_HOME/install/jetson_render.py" ]] || fail "BEAN_HOME must point to a BEAN checkout with Jetson installer"
[[ "$CUDA_ARCH" =~ ^[0-9]+$ ]] || fail "BEAN_CUDA_ARCH must be numeric (Orin Nano: 87)"
[[ "$BUILD_JOBS" =~ ^[1-9][0-9]*$ ]] || fail "BEAN_BUILD_JOBS must be a positive number"
[[ "$LLM_PORT" =~ ^[0-9]+$ ]] && (( LLM_PORT >= 1024 && LLM_PORT <= 65535 )) || fail "Invalid BEAN_LLM_PORT"
[[ "$MODEL_DOWNLOAD" == 0 || "$MODEL_DOWNLOAD" == 1 ]] || fail "BEAN_LLM_DOWNLOAD must be 0 or 1"
[[ "$LLM_START" == 0 || "$LLM_START" == 1 ]] || fail "BEAN_LLM_START must be 0 or 1"

say "Check installed compiler and build tools"
missing=()
for program in git cmake g++ make curl; do
  command -v "$program" >/dev/null 2>&1 || missing+=("$program")
done
if (( ${#missing[@]} )); then
  say "Install missing build prerequisites: ${missing[*]}"
  if ! command -v apt-get >/dev/null 2>&1; then
    fail "apt-get not available. Supply git, cmake, g++, make and curl."
  fi
  sudo apt-get update
  sudo apt-get install -y git cmake build-essential curl
fi

# JetPack commonly installs nvcc in /usr/local/cuda/bin without adding it to PATH.
NVCC="${BEAN_NVCC:-}"
if [[ -z "$NVCC" ]]; then
  NVCC="$(command -v nvcc || true)"
fi
if [[ -z "$NVCC" || ! -x "$NVCC" ]]; then
  for candidate in /usr/local/cuda/bin/nvcc /usr/local/cuda-*/bin/nvcc; do
    if [[ -x "$candidate" ]]; then NVCC="$candidate"; break; fi
  done
fi
[[ -n "$NVCC" && -x "$NVCC" ]] ||
  fail "nvcc missing: install the CUDA toolkit through NVIDIA JetPack for this Jetson. No CPU-only substitute is silently installed."
NVCC="$(readlink -f "$NVCC")"
CUDA_ROOT="$(dirname "$(dirname "$NVCC")")"
export PATH="$(dirname "$NVCC"):$PATH"
export CUDACXX="$NVCC"
say "CUDA compiler found: $NVCC"
"$NVCC" --version | tail -n 4

say "Reuse or clone official llama.cpp source"
if [[ -d "$LLAMA_CPP_DIR/.git" ]]; then
  echo "Reusing $LLAMA_CPP_DIR (no automatic git pull or source overwrite)"
elif [[ -e "$LLAMA_CPP_DIR" ]]; then
  fail "$LLAMA_CPP_DIR already exists but is not a git checkout. Preserve it and choose BEAN_LLAMA_CPP_DIR."
else
  git clone --depth 1 https://github.com/ggml-org/llama.cpp.git "$LLAMA_CPP_DIR"
fi

say "llama.cpp build directory: $LLAMA_BUILD_DIR"
if [[ -x "$LLAMA_SERVER" && "${BEAN_LLM_REBUILD:-0}" != 1 ]]; then
  say "Existing CUDA server found; skipping rebuild: $LLAMA_SERVER"
else
  say "Configure CUDA llama.cpp for Jetson Orin (arch $CUDA_ARCH)"
  # Reuse a previously configured CUDA build, including partially compiled
  # object files. For a failed configure, use build-bean-cuda instead.
  cmake -S "$LLAMA_CPP_DIR" -B "$LLAMA_BUILD_DIR" \
    -DGGML_CUDA=ON \
    "-DCMAKE_CUDA_COMPILER=$NVCC" \
    "-DCUDAToolkit_ROOT=$CUDA_ROOT" \
    "-DCMAKE_CUDA_ARCHITECTURES=$CUDA_ARCH" \
    -DCMAKE_BUILD_TYPE=Release \
    -DLLAMA_CURL=OFF
  say "Build CUDA llama-server with $BUILD_JOBS parallel jobs"
  cmake --build "$LLAMA_BUILD_DIR" --target llama-server -j "$BUILD_JOBS"
fi
[[ -x "$LLAMA_SERVER" ]] || fail "llama-server was not produced at $LLAMA_SERVER"

# Use a local GGUF file rather than depending on the llama.cpp HF auto-loader,
# since the lean build intentionally omits libcurl support.
if [[ -f "$MODEL_PATH" ]]; then
  say "Keeping existing GGUF model: $MODEL_PATH"
elif [[ "$MODEL_DOWNLOAD" == 1 ]]; then
  [[ "$MODEL_URL" == https://* ]] || fail "GGUF URL must use HTTPS"
  say "Download Qwen2.5 1.5B Instruct Q4_K_M GGUF (resumable)"
  mkdir -p "$(dirname "$MODEL_PATH")"
  part="$MODEL_PATH.partial"
  if ! curl --fail --location --retry 3 --connect-timeout 30 \
       --continue-at - --output "$part" "$MODEL_URL"; then
    echo "Resume unavailable. Retrying once from the beginning." >&2
    rm -f -- "$part"
    curl --fail --location --retry 3 --connect-timeout 30 \
      --output "$part" "$MODEL_URL"
  fi
  # Reject HTML/error pages and obviously truncated responses.
  [[ "$(head -c 4 "$part")" == GGUF ]] || fail "Downloaded file is not a GGUF model; retained $part for inspection"
  [[ "$(stat -c %s "$part")" -ge 100000000 ]] || fail "Downloaded model unexpectedly small"
  mv -- "$part" "$MODEL_PATH"
else
  say "Model download skipped; set BEAN_GGUF_PATH to an existing GGUF before starting"
fi

if [[ ! -f "$MODEL_PATH" ]]; then
  echo "CUDA llama-server is built, but no GGUF model is configured."
  echo "Model service was not installed; rerun with BEAN_GGUF_PATH or BEAN_LLM_DOWNLOAD=1."
  exit 0
fi
[[ "$(head -c 4 "$MODEL_PATH")" == GGUF ]] || fail "Selected model is not a valid GGUF header: $MODEL_PATH"

say "Render local-only model server service"
render_args=(--user "$BEAN_USER" --group "$BEAN_GROUP" --home "$BEAN_HOME"
  --data-dir "$BEAN_DATA_DIR" --log-dir "$BEAN_LOG_DIR" --env-file "$BEAN_ENV_FILE"
  --llama-dir "$LLAMA_BUILD_DIR" --model-path "$MODEL_PATH" --llm-port "$LLM_PORT")
# Only the model service is managed here. BEAN Core's existing service and
# the currently running BEAN process are not restarted or replaced.
sudo mkdir -p "$(dirname "$SERVICE_FILE")"
python3 "$BEAN_HOME/install/jetson_render.py" llm_service "${render_args[@]}" | sudo tee "$SERVICE_FILE" >/dev/null
sudo chmod 0644 "$SERVICE_FILE"
sudo systemctl daemon-reload
if [[ "$LLM_START" == 1 ]]; then
  say "Enable local llama.cpp server"
  sudo systemctl enable --now "$(basename "$SERVICE_FILE")"
  sudo systemctl is-active "$(basename "$SERVICE_FILE")" || fail "Local inference service did not become active"
  if [[ "${BEAN_LLM_SMOKE:-1}" == "1" ]]; then
    say "Verify Qwen model readiness and a real local inference response"
    python3 "$BEAN_HOME/install/jetson_llm_smoke.py" --port "$LLM_PORT" ||
      fail "llama-server started, but did not pass a local model response check. See journalctl -u bean-llamacpp.service."
  fi
else
  echo "LLM_START=0: service configured but not started"
fi
cat <<MSG
BEAN local CUDA inference package installed.
Binary: $LLAMA_SERVER
Model:  $MODEL_PATH
Server: http://127.0.0.1:$LLM_PORT
Alias:  bean-local
Use:    journalctl -u bean-llamacpp.service -n 50 --no-pager
Existing BEAN runtime and its persistent memory were not restarted.
MSG
