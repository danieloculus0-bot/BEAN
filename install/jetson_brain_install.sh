#!/usr/bin/env bash
# BEAN Jetson Orin Nano Super brain-only installer.
# Runs only after NVIDIA Jetson Linux has been installed and booted.
set -euo pipefail

BEAN_USER="${BEAN_USER:-bean}"
BEAN_HOME="${BEAN_HOME:-/home/bean/BEAN}"
BEAN_DATA_DIR="${BEAN_DATA_DIR:-/home/bean/bean_data}"
BEAN_LOG_DIR="${BEAN_LOG_DIR:-/home/bean/bean_logs}"
ENV_DIR="${ENV_DIR:-/etc/bean}"
ENV_FILE="${ENV_FILE:-/etc/bean/bean.env}"
SERVICE_FILE="${SERVICE_FILE:-/etc/systemd/system/bean.service}"

die() { printf 'BLOCKED: %s\n' "$*" >&2; exit 1; }

# This v1 template still has explicit service paths. Refuse unsupported
# overrides instead of leaving a silently broken service behind.
[[ "$BEAN_USER" == "bean" ]] || die "Service template supports BEAN_USER=bean only."
[[ "$BEAN_HOME" == "/home/bean/BEAN" ]] || die "Service template requires BEAN_HOME=/home/bean/BEAN."
[[ "$ENV_FILE" == "/etc/bean/bean.env" ]] || die "Service requires ENV_FILE=/etc/bean/bean.env."
[[ "$SERVICE_FILE" == "/etc/systemd/system/bean.service" ]] || die "Service requires /etc/systemd/system/bean.service."
[[ "$ENV_DIR" == "/etc/bean" ]] || die "Service requires ENV_DIR=/etc/bean."
[[ "$BEAN_DATA_DIR" == "/home/bean/bean_data" ]] || die "This candidate supports the documented data location only."
[[ "$BEAN_LOG_DIR" == "/home/bean/bean_logs" ]] || die "This candidate supports the documented log location only."

[[ -f "bean_run.py" ]] || die "Run from the BEAN repository root."
[[ "$(pwd -P)" == "$BEAN_HOME" ]] || die "Checkout must be at $BEAN_HOME (current: $(pwd -P))."
command -v sudo >/dev/null || die "sudo is required for systemd and account-owned directories."
command -v python3 >/dev/null || die "python3 is missing."
# Use a Python-version probe parseable even by older JetPack default Python.
python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)' ||
  die "BEAN requires Python 3.10+. Install a supported Python before running this script."
id "$BEAN_USER" >/dev/null 2>&1 ||
  die "Service user 'bean' does not exist. Provision it explicitly before installing."
[[ "$(id -gn "$BEAN_USER")" == "bean" ]] ||
  die "Service template requires group 'bean' as the bean user's primary group."
sudo -u "$BEAN_USER" test -r "$BEAN_HOME/bean_run.py" ||
  die "The bean service account cannot read this checkout."
sudo -u "$BEAN_USER" test -w "$BEAN_HOME" ||
  die "The bean service account must be able to create its venv in $BEAN_HOME."

echo "==> Checking installed Orin Nano platform and service configuration"
python3 install/jetson_deployment_gate.py ||
  die "Post-OS Jetson deployment gate failed; fix its reported blockers first."
python3 install/jetson_platform_check.py --require-jetson ||
  die "Jetson platform probe failed."
sudo -v

echo "==> Creating BEAN virtual environment under the actual service user"
if [[ ! -f "$BEAN_HOME/.venv/bin/python3" ]]; then
  sudo -u "$BEAN_USER" python3 -m venv "$BEAN_HOME/.venv"
fi
sudo -u "$BEAN_USER" "$BEAN_HOME/.venv/bin/python3" -m pip install --upgrade pip
sudo -u "$BEAN_USER" "$BEAN_HOME/.venv/bin/python3" -m pip install psutil

echo "==> Running temporary BEAN boot check as service user"
sudo -u "$BEAN_USER" "$BEAN_HOME/.venv/bin/python3" -m bean.runtime.boot_readiness --temp

echo "==> Creating private persistent directories"
sudo install -d -o bean -g bean -m 0750 "$BEAN_DATA_DIR" "$BEAN_LOG_DIR"
sudo install -d -o bean -g bean -m 0750 "$BEAN_DATA_DIR/inbox"
sudo install -d -o root -g root -m 0755 "$ENV_DIR"

if [[ ! -e "$ENV_FILE" ]]; then
  sudo install -o root -g bean -m 0640 install/bean.env.example "$ENV_FILE"
  echo "Created $ENV_FILE"
else
  [[ -f "$ENV_FILE" ]] || die "$ENV_FILE exists and is not a regular file."
  echo "Using existing $ENV_FILE; checking contract without overwriting settings."
fi

# Do not source a privileged environment file into this installer. Only check
# the required locations used by the fixed service contract.
for expectation in \
  "BEAN_HOME=$BEAN_HOME" \
  "BEAN_DATA_DIR=$BEAN_DATA_DIR" \
  "BEAN_LOG_DIR=$BEAN_LOG_DIR" \
  "BEAN_DB_PATH=$BEAN_DATA_DIR/bean_memory.db" \
  "BEAN_INBOX_DIR=$BEAN_DATA_DIR/inbox"; do
  sudo grep -Fqx "$expectation" "$ENV_FILE" ||
    die "Environment mismatch: $expectation. Update $ENV_FILE intentionally before enabling the service."
done

echo "==> Installing systemd service with verified fixed paths"
sudo install -o root -g root -m 0644 install/bean.service "$SERVICE_FILE"
sudo systemctl daemon-reload

cat <<'MSG'
BEAN brain install files are in place. No motor hardware was enabled.
Confirm service output and persistent memory continuity on the actual Jetson:
  sudo systemctl enable --now bean.service
  sudo systemctl status bean.service --no-pager
  sudo journalctl -u bean.service -n 100 --no-pager
  bash scripts/bean_doctor.sh
  bash scripts/bean_boot_ready.sh --db /home/bean/bean_data/bean_memory.db
Record cold reboot, restore/backup, temperatures, RAM and crash-restart evidence.
MSG
