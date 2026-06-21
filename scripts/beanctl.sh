#!/usr/bin/env bash
# Convenience wrapper for common BEAN Brain 0.2 operations.

set -euo pipefail

CMD="${1:-help}"
ROOT="${BEAN_HOME:-/home/bean/BEAN}"
PY="$ROOT/.venv/bin/python3"

case "$CMD" in
  status)
    "$PY" "$ROOT/scripts/bean_status.py"
    ;;
  backup)
    "$PY" "$ROOT/scripts/bean_backup.py"
    ;;
  test)
    cd "$ROOT"
    "$PY" bean/tests/test_brain_install.py
    ;;
  start)
    sudo systemctl start bean.service
    ;;
  stop)
    sudo systemctl stop bean.service
    ;;
  restart)
    sudo systemctl restart bean.service
    ;;
  service)
    sudo systemctl status bean.service --no-pager
    ;;
  logs)
    journalctl -u bean.service -n 100 --no-pager
    ;;
  follow)
    journalctl -u bean.service -f
    ;;
  help|*)
    cat <<'MSG'
BEAN control helper

Commands:
  beanctl.sh status   Print DB/runtime status
  beanctl.sh backup   Backup BEAN memory DB
  beanctl.sh test     Run brain install smoke test
  beanctl.sh start    Start bean.service
  beanctl.sh stop     Stop bean.service
  beanctl.sh restart  Restart bean.service
  beanctl.sh service  Show systemd status
  beanctl.sh logs     Show recent service logs
  beanctl.sh follow   Follow service logs
MSG
    ;;
esac
