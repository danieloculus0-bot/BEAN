#!/usr/bin/env bash
set -euo pipefail

SERVICE="bean-brain.service"
BEAN_DATA="${BEAN_DATA:-/var/lib/bean}"

printf '\nBEAN OS first boot check\n'
printf '========================\n\n'

if [[ -f /etc/nv_tegra_release ]]; then
  echo "Jetson release:"
  cat /etc/nv_tegra_release
else
  echo "WARN: /etc/nv_tegra_release not found. This may not be a Jetson JetPack install."
fi

printf '\nService status:\n'
systemctl --no-pager status "${SERVICE}" || true

printf '\nHeartbeat:\n'
if [[ -f "${BEAN_DATA}/heartbeat.json" ]]; then
  cat "${BEAN_DATA}/heartbeat.json"
else
  echo "No heartbeat yet. Start service with: sudo systemctl start ${SERVICE}"
fi

printf '\nRecent logs:\n'
journalctl -u "${SERVICE}" -n 50 --no-pager || true

printf '\nSafety env:\n'
grep -E 'BEAN_MOTION_ENABLED|BEAN_SENTIENCE_CLAIMED|BEAN_RUNTIME_MODE|BEAN_LLM_PROVIDER' /etc/bean/bean.env || true
