#!/usr/bin/env bash
set -euo pipefail

# BEAN OS v0 installer
# Target: NVIDIA Jetson running Ubuntu/JetPack.
# This is not a custom OS image. It is a safe JetPack overlay that installs
# BEAN as a brain-only systemd service with persistent memory paths.

if [[ "${EUID}" -ne 0 ]]; then
  echo "Run as root: sudo bash install/bean-os/install_bean_os.sh"
  exit 1
fi

REPO_SOURCE="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
BEAN_USER="${BEAN_USER:-bean}"
BEAN_HOME="${BEAN_HOME:-/opt/bean}"
BEAN_REPO="${BEAN_REPO:-${BEAN_HOME}/BEAN}"
BEAN_DATA="${BEAN_DATA:-/var/lib/bean}"
BEAN_LOG_DIR="${BEAN_LOG_DIR:-/var/log/bean}"
BEAN_ETC="${BEAN_ETC:-/etc/bean}"
INSTALL_SERVICE="${INSTALL_SERVICE:-1}"
ENABLE_SERVICE="${ENABLE_SERVICE:-1}"
START_SERVICE="${START_SERVICE:-0}"

log() {
  printf '\n[BEAN OS] %s\n' "$*"
}

require_command() {
  command -v "$1" >/dev/null 2>&1 || {
    echo "Missing required command: $1"
    exit 1
  }
}

log "Checking base system"
require_command python3
require_command systemctl

if [[ ! -f /etc/nv_tegra_release ]]; then
  echo "Warning: /etc/nv_tegra_release not found. This may not be a Jetson JetPack system."
fi

log "Installing base packages"
apt-get update
DEBIAN_FRONTEND=noninteractive apt-get install -y \
  python3 \
  python3-venv \
  python3-pip \
  python3-dev \
  build-essential \
  git \
  rsync \
  sqlite3 \
  ca-certificates

log "Creating BEAN user and directories"
if ! id "${BEAN_USER}" >/dev/null 2>&1; then
  useradd --system --create-home --home-dir "${BEAN_HOME}" --shell /usr/sbin/nologin "${BEAN_USER}"
fi

mkdir -p "${BEAN_HOME}" "${BEAN_REPO}" "${BEAN_DATA}" "${BEAN_DATA}/inbox" "${BEAN_LOG_DIR}" "${BEAN_ETC}"

log "Copying repository to ${BEAN_REPO}"
rsync -a --delete \
  --exclude '.git' \
  --exclude '.venv' \
  --exclude '__pycache__' \
  --exclude '*.pyc' \
  "${REPO_SOURCE}/" "${BEAN_REPO}/"

log "Creating Python virtual environment"
python3 -m venv "${BEAN_HOME}/venv"
"${BEAN_HOME}/venv/bin/python" -m pip install --upgrade pip setuptools wheel

if [[ -f "${BEAN_REPO}/requirements.txt" ]]; then
  log "Installing requirements.txt"
  "${BEAN_HOME}/venv/bin/pip" install -r "${BEAN_REPO}/requirements.txt"
else
  log "No requirements.txt found. Skipping Python dependency install."
fi

log "Installing environment file"
if [[ ! -f "${BEAN_ETC}/bean.env" ]]; then
  install -m 0640 "${BEAN_REPO}/install/bean-os/bean.env.example" "${BEAN_ETC}/bean.env"
else
  echo "Existing ${BEAN_ETC}/bean.env preserved."
fi

# Normalize defaults in case installer path overrides were used.
sed -i \
  -e "s|^BEAN_HOME=.*|BEAN_HOME=${BEAN_HOME}|" \
  -e "s|^BEAN_REPO=.*|BEAN_REPO=${BEAN_REPO}|" \
  -e "s|^BEAN_DATA=.*|BEAN_DATA=${BEAN_DATA}|" \
  -e "s|^BEAN_LOG_DIR=.*|BEAN_LOG_DIR=${BEAN_LOG_DIR}|" \
  -e "s|^BEAN_DB_PATH=.*|BEAN_DB_PATH=${BEAN_DATA}/bean_memory.db|" \
  -e "s|^BEAN_INBOX_DIR=.*|BEAN_INBOX_DIR=${BEAN_DATA}/inbox|" \
  "${BEAN_ETC}/bean.env"

log "Setting ownership and permissions"
chown -R "${BEAN_USER}:${BEAN_USER}" "${BEAN_HOME}" "${BEAN_DATA}" "${BEAN_LOG_DIR}"
chmod 0750 "${BEAN_HOME}" "${BEAN_DATA}" "${BEAN_LOG_DIR}"
chmod 0640 "${BEAN_ETC}/bean.env"
chown root:"${BEAN_USER}" "${BEAN_ETC}/bean.env"
chmod +x "${BEAN_REPO}/scripts/bean_safe_runtime.py"
chmod +x "${BEAN_REPO}/scripts/run_brain_smoke_tests.sh" || true
chmod +x "${BEAN_REPO}/install/bean-os/verify_bean_os.sh" || true

if [[ "${INSTALL_SERVICE}" == "1" ]]; then
  log "Installing systemd service"
  install -m 0644 "${BEAN_REPO}/install/bean-os/bean-brain.service" /etc/systemd/system/bean-brain.service
  systemctl daemon-reload
  if [[ "${ENABLE_SERVICE}" == "1" ]]; then
    systemctl enable bean-brain.service
  fi
  if [[ "${START_SERVICE}" == "1" ]]; then
    systemctl restart bean-brain.service
  fi
fi

log "Running installer verification"
"${BEAN_REPO}/install/bean-os/verify_bean_os.sh" || {
  echo "Verification failed. Inspect output above."
  exit 1
}

cat <<EOF

BEAN OS v0 install complete.

Paths:
  Repo: ${BEAN_REPO}
  Data: ${BEAN_DATA}
  Inbox: ${BEAN_DATA}/inbox
  Env: ${BEAN_ETC}/bean.env
  Logs: ${BEAN_LOG_DIR}

Service:
  sudo systemctl status bean-brain.service
  sudo systemctl start bean-brain.service
  sudo journalctl -u bean-brain.service -f

Safety:
  Physical motion remains disabled.
  BEAN_MOTION_ENABLED=0
  BEAN_SENTIENCE_CLAIMED=0

EOF
