#!/usr/bin/env bash
# Package BEAN's existing Jetson runtime; preserve its memory and model files.
set -euo pipefail

BEAN_USER="${BEAN_USER:-${SUDO_USER:-$(id -un)}}"
BEAN_GROUP="${BEAN_GROUP:-$(id -gn "$BEAN_USER")}"
BEAN_HOME="${BEAN_HOME:-$(pwd -P)}"
USER_HOME="$(getent passwd "$BEAN_USER" | cut -d: -f6)"
if [[ -z "$USER_HOME" ]]; then
  echo "Unable to resolve home for $BEAN_USER" >&2
  exit 1
fi
# Retain BEAN's existing persistent Jetson memory from earlier Core boots.
if [[ -z "${BEAN_DATA_DIR:-}" ]]; then
  if [[ -f "$USER_HOME/bean_core_data/bean_memory.db" ]]; then
    BEAN_DATA_DIR="$USER_HOME/bean_core_data"
  elif [[ -f "$USER_HOME/bean_data/bean_memory.db" ]]; then
    BEAN_DATA_DIR="$USER_HOME/bean_data"
  else
    BEAN_DATA_DIR="$USER_HOME/bean_core_data"
  fi
fi
export BEAN_USER BEAN_GROUP BEAN_HOME BEAN_DATA_DIR
BEAN_LOG_DIR="${BEAN_LOG_DIR:-$USER_HOME/bean_logs}"
ENV_FILE="${ENV_FILE:-/etc/bean/bean.env}"
SERVICE_FILE="${SERVICE_FILE:-/etc/systemd/system/bean.service}"

if [[ ! -f "$BEAN_HOME/bean_run.py" || ! -f "$BEAN_HOME/install/jetson_render.py" ]]; then
  echo "Run from BEAN repository root or set BEAN_HOME to your clone path." >&2
  exit 1
fi
cd "$BEAN_HOME"
echo "==> Check Jetson / JetPack environment"
python3 install/jetson_platform_check.py --require-jetson

if [[ ! -x .venv/bin/python3 ]]; then
  echo "==> Create local Python virtual environment"
  if ! python3 -m venv .venv; then
    echo "Python virtual environment creation failed. Checking python3-venv package."
    command -v apt-get >/dev/null 2>&1 || exit 1
    sudo apt-get update
    sudo apt-get install -y python3-venv
    python3 -m venv .venv
  fi
fi
if [[ ! -x .venv/bin/python3 ]]; then
  echo "Python venv is incomplete. Check python3-venv." >&2
  exit 1
fi
.venv/bin/python3 -m pip install psutil pytest

echo "==> Check BEAN Core with disposable SQLite"
.venv/bin/python3 -m bean.runtime.boot_readiness --temp

echo "==> Create persistent data directories"
sudo install -d -m 0750 -o "$BEAN_USER" -g "$BEAN_GROUP" \
  "$BEAN_DATA_DIR" "$BEAN_LOG_DIR" "$BEAN_DATA_DIR/inbox"
sudo mkdir -p "$(dirname "$ENV_FILE")" "$(dirname "$SERVICE_FILE")"

RENDER_ARGS=(--user "$BEAN_USER" --group "$BEAN_GROUP" --home "$BEAN_HOME" \
  --data-dir "$BEAN_DATA_DIR" --log-dir "$BEAN_LOG_DIR" --env-file "$ENV_FILE")

if [[ ! -e "$ENV_FILE" ]]; then
  .venv/bin/python3 install/jetson_render.py env "${RENDER_ARGS[@]}" | sudo tee "$ENV_FILE" >/dev/null
  sudo chmod 0640 "$ENV_FILE"
  echo "Created $ENV_FILE"
else
  echo "Preserved existing $ENV_FILE; check that its BEAN_HOME and data paths match."
fi
.venv/bin/python3 install/jetson_render.py service "${RENDER_ARGS[@]}" | sudo tee "$SERVICE_FILE" >/dev/null
sudo chmod 0644 "$SERVICE_FILE"
sudo systemctl daemon-reload

# This installs the missing native language inference backend, including
# JetPack CUDA compiler discovery, llama.cpp compilation and local GGUF model.
# Reuses existing sources and never restarts an already running BEAN process.
if [[ "${BEAN_LLM_INSTALL:-1}" == "1" ]]; then
  echo "==> Install local CUDA reasoning backend"
  bash install/jetson_local_llm_install.sh
else
  echo "Skipping local inference installation (BEAN_LLM_INSTALL=0)."
fi

cat <<'MSG'
BEAN's existing brain is packaged. This installer does not start or restart it.
Audit from your BEAN directory:
  .venv/bin/python3 scripts/jetson_runtime_audit.py --smoke
After reviewing runtime results:
  sudo systemctl enable --now bean.service
  journalctl -u bean.service -n 50 --no-pager
The local CUDA model service is installed and started unless BEAN_LLM_START=0.
Check journalctl -u bean-llamacpp.service for readiness.
Physical servo and motor outputs are not activated by this installer.
MSG
