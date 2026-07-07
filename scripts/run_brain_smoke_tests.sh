#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

TESTS=(
  bean/tests/test_brain_install.py
  bean/tests/test_cognition_core.py
  bean/tests/test_world_model.py
  bean/tests/test_runtime_loop.py
  bean/tests/test_epistemic_guard.py
  bean/tests/test_contradiction_court.py
  bean/tests/test_falsification.py
  bean/tests/test_dreaming.py
  bean/tests/test_uncertainty_garden.py
  bean/tests/test_dignity.py
  bean/tests/test_inner_weather.py
  bean/tests/test_autobiography.py
  bean/tests/test_brain_maintenance.py
  bean/tests/test_relationship_trust.py
  bean/tests/test_runtime_proof.py
  bean/tests/test_wisdom_module.py
  bean/tests/test_reasoning_layer.py
  bean/tests/test_speculative_logic.py
  bean/tests/test_origin_covenant.py
  bean/tests/test_boot_readiness.py
)

for test_file in "${TESTS[@]}"; do
  if [[ ! -f "$test_file" ]]; then
    echo "SKIP missing test: $test_file"
    continue
  fi
  echo "==> python3 $test_file"
  python3 "$test_file"
done

echo "BEAN brain smoke tests passed."
