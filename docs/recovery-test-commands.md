# Recovery Validation Commands

Run these from the repo root before merging `chatgpt-brain-0.13-recovery` into `main`.

```bash
python3 bean/tests/test_runtime_proof.py
python3 bean/tests/test_wisdom_module.py
python3 bean/tests/test_reasoning_module.py
python3 bean/tests/test_openai_provider.py
python3 bean/tests/test_speculative_logic.py
bash scripts/run_brain_smoke_tests.sh
```

Then run a source scan over the software-only brain packages:

```bash
grep -R "execute_motion\|GPIO\|RPi\|pigpio\|serial" bean/wisdom bean/reasoning bean/speculation || true
```

Expected result:

- Tests pass.
- Any source-scan hit is reviewed before merge.
- Runtime proof reports `motion_enabled=False`.
- Runtime proof reports `sentience_claimed=False`.
- No physical motion execution is added by this branch.
