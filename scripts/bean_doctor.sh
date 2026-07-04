#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

echo "==> Python compile check"
python3 -m compileall -q bean bean_run.py

echo "==> Boot readiness with temp DB"
python3 -m bean.runtime.boot_readiness --temp

echo "==> Core smoke tests"
bash scripts/run_brain_smoke_tests.sh

echo "BEAN doctor passed."
