#!/usr/bin/env bash
# BEAN Jetson install helper.
# Run from the repository root on the Jetson.

set -euo pipefail

BEAN_USER="${BEAN_USER:-bean}"
BEAN_HOME="${BEAN_HOME:-/home/bean/BEAN}"
BEAN_DATA_DIR="${BEAN_DATA_DIR:-/home/bean/bean_data}"
BEAN_LOG_DIR="${BEAN_LOG_DIR:-/home/bean/bean_logs}"
ENV_DIR="${ENV_DIR:-/etc/bean}"
ENV_FILE="${ENV_FILE:-/etc/bean/bean.env}"
SERVICE_FILE="${SERVICE_FILE:-/etc/systemd/system/bean.service}"

if [[ ! -f "bean_run.py" ]]; then
  echo "Run this script from the BEAN repository root."
  exit 1
fi

echo "==> Checking Jetson / JetPack platform"
python3 install/jetson_platform_check.py --require-jetson

echo "==> Creating BEAN data directories"
mkdir -p "$BEAN_DATA_DIR" "$BEAN_LOG_DIR" "$BEAN_DATA_DIR/inbox"
sudo mkdir -p "$ENV_DIR"

if [[ ! -f "$ENV_FILE" ]]; then
  sudo cp install/bean.env.example "$ENV_FILE"
  sudo sed -i "s|^BEAN_HOME=.*|BEAN_HOME=$BEAN_HOME|" "$ENV_FILE"
  sudo sed -i "s|^BEAN_DATA_DIR=.*|BEAN_DATA_DIR=$BEAN_DATA_DIR|" "$ENV_FILE"
  sudo sed -i "s|^BEAN_LOG_DIR=.*|BEAN_LOG_DIR=$BEAN_LOG_DIR|" "$ENV_FILE"
  sudo sed -i "s|^BEAN_DB_PATH=.*|BEAN_DB_PATH=$BEAN_DATA_DIR/bean_memory.db|" "$ENV_FILE"
  sudo sed -i "s|^BEAN_INBOX_DIR=.*|BEAN_INBOX_DIR=$BEAN_DATA_DIR/inbox|" "$ENV_FILE"
  echo "Created $ENV_FILE"
else
  echo "$ENV_FILE already exists. Leaving it unchanged."
fi

echo "==> Preparing Python virtual environment"
if [[ ! -d ".venv" ]]; then
  python3 -m venv .venv
fi

. .venv/bin/activate
python3 -m pip install --upgrade pip
python3 -m pip install psutil

echo "==> Running temporary boot readiness check"
python3 -m bean.runtime.boot_readiness --temp

echo "==> Installing systemd service"
sudo cp install/bean.service "$SERVICE_FILE"
sudo systemctl daemon-reload

echo
cat <<'MSG'
BEAN install files are in place.

Next commands:
  source /etc/bean/bean.env
  bash scripts/bean_doctor.sh
  bash scripts/bean_boot_ready.sh --db "$BEAN_DB_PATH"
  sudo systemctl enable bean.service
  sudo systemctl start bean.service
  sudo systemctl status bean.service

Physical output hardware is not enabled by this installer.
MSG
