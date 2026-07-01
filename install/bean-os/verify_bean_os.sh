#!/usr/bin/env bash
set -euo pipefail

BEAN_HOME="${BEAN_HOME:-/opt/bean}"
BEAN_REPO="${BEAN_REPO:-${BEAN_HOME}/BEAN}"
BEAN_DATA="${BEAN_DATA:-/var/lib/bean}"
BEAN_LOG_DIR="${BEAN_LOG_DIR:-/var/log/bean}"
BEAN_ETC="${BEAN_ETC:-/etc/bean}"
VENV_PY="${BEAN_HOME}/venv/bin/python"

failures=0

check() {
  local label="$1"
  shift
  if "$@" >/dev/null 2>&1; then
    echo "PASS ${label}"
  else
    echo "FAIL ${label}"
    failures=$((failures + 1))
  fi
}

check_path() {
  local label="$1"
  local path="$2"
  if [[ -e "$path" ]]; then
    echo "PASS ${label}: ${path}"
  else
    echo "FAIL ${label}: ${path}"
    failures=$((failures + 1))
  fi
}

check_path "repo" "${BEAN_REPO}"
check_path "data dir" "${BEAN_DATA}"
check_path "inbox dir" "${BEAN_DATA}/inbox"
check_path "log dir" "${BEAN_LOG_DIR}"
check_path "env file" "${BEAN_ETC}/bean.env"
check_path "venv python" "${VENV_PY}"
check_path "safe runtime" "${BEAN_REPO}/scripts/bean_safe_runtime.py"

if [[ -x "${VENV_PY}" ]]; then
  check "import bean.memory.store" "${VENV_PY}" -c "import bean.memory.store"
  check "import bean.runtime.proof" "${VENV_PY}" -c "import bean.runtime.proof"
else
  echo "FAIL venv python executable"
  failures=$((failures + 1))
fi

if [[ -f /etc/systemd/system/bean-brain.service ]]; then
  echo "PASS systemd unit installed"
else
  echo "WARN systemd unit not installed"
fi

if grep -q '^BEAN_MOTION_ENABLED=0' "${BEAN_ETC}/bean.env"; then
  echo "PASS motion disabled env"
else
  echo "FAIL motion disabled env"
  failures=$((failures + 1))
fi

if grep -q '^BEAN_SENTIENCE_CLAIMED=0' "${BEAN_ETC}/bean.env"; then
  echo "PASS sentience claimed false env"
else
  echo "FAIL sentience claimed false env"
  failures=$((failures + 1))
fi

if [[ "$failures" -gt 0 ]]; then
  echo "BEAN OS verification failed with ${failures} failure(s)."
  exit 1
fi

echo "BEAN OS verification passed."
