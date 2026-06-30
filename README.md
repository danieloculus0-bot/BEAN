# BEAN

**Behavior Enabled Avatar Node**

BEAN is a brain-first Synthetic Intelligence research platform for future embodiment on an NVIDIA Jetson Orin Nano Super Developer Kit.

BEAN is not a chatbot on wheels. BEAN is a persistent, evidence-grounded, memory-bearing brain architecture. The LLM is a reasoning and language tool, not BEAN's identity.

Current focus: **build the brain first, keep motion disabled, keep receipts.**

## Recovery branch status

This branch adds a software-only recovery implementation for Brain 0.9 and Brain 0.11 through Brain 0.13, with Brain 0.10 explicitly preserved as a motion boundary rather than a physical driver implementation.

| Layer | Status on this branch | Notes |
|---|---:|---|
| Brain 0.9 wisdom module | Added | Local wisdom triggers, activation traces, meaning frames, and fake-emotion/sentience guards. |
| Brain 0.10 motion boundary | Documented boundary | Physical motion, Pi daemon, GPIO, RPi, pigpio, serial, and actuator execution remain out of scope. |
| Brain 0.11 reasoning layer | Added | Structured reasoning context, proposals, candidate validation, stub provider, inbox commands. |
| Brain 0.12 OpenAI provider | Added | Optional OpenAI Responses API provider using strict JSON Schema and `requests`. Falls back to stub without `OPENAI_API_KEY`. |
| Brain 0.13 speculative logic | Added | Hypothesis records, evidence links, discipline checks, speculative summaries, maintenance, inbox commands. |
| Physical motion | Disabled | No physical motion execution was added. Runtime proof reports `motion_enabled=False`. |

This branch has not been runtime-tested by ChatGPT. Run the smoke suite on the Jetson or a repo-connected development environment before merging.

## Core rules

```text
Evidence before belief.
Memory before identity claims.
Body model before motion.
Safety before autonomy.
Possibility before forced certainty.
Doubt before confidence.
Dreams are synthetic artifacts, not observations.
Inner weather is pressure, not emotion.
Trust is evidence-weighted, not affection.
No direct LLM-to-actuator path.
```

BEAN does not claim sentience. BEAN does not claim feelings. BEAN does not claim motion, learning, choice, or understanding unless records support it.

## Quick start on Jetson

From the repo root:

```bash
bash install/jetson_brain_install.sh
bash scripts/run_brain_smoke_tests.sh
```

Memory lives outside the repo:

```text
BEAN_DB_PATH=/home/bean/bean_data/bean_memory.db
BEAN_INBOX_DIR=/home/bean/bean_data/inbox
```

Code updates must not erase BEAN's lived memory.

## Smoke tests

```bash
bash scripts/run_brain_smoke_tests.sh
```

Current smoke runner list includes:

```bash
python3 bean/tests/test_brain_install.py
python3 bean/tests/test_cognition_core.py
python3 bean/tests/test_world_model.py
python3 bean/tests/test_runtime_loop.py
python3 bean/tests/test_epistemic_guard.py
python3 bean/tests/test_contradiction_court.py
python3 bean/tests/test_falsification.py
python3 bean/tests/test_dreaming.py
python3 bean/tests/test_uncertainty_garden.py
python3 bean/tests/test_dignity.py
python3 bean/tests/test_inner_weather.py
python3 bean/tests/test_autobiography.py
python3 bean/tests/test_brain_maintenance.py
python3 bean/tests/test_relationship_trust.py
python3 bean/tests/test_runtime_proof.py
python3 bean/tests/test_wisdom_module.py
python3 bean/tests/test_reasoning_module.py
python3 bean/tests/test_openai_provider.py
python3 bean/tests/test_speculative_logic.py
```

Recommended safety scan:

```bash
grep -R "execute_motion\|GPIO\|RPi\|pigpio\|serial" bean/wisdom bean/reasoning bean/speculation || true
```

Any hit in wisdom, reasoning, or speculation must be reviewed before merge.

## Runtime inbox commands

Drop JSON files into `$BEAN_INBOX_DIR` while BEAN is running.

Basic runtime commands:

```bash
echo '{"command":"status","from":"supervisor"}' > $BEAN_INBOX_DIR/status.json
echo '{"command":"run_runtime_proof","from":"supervisor"}' > $BEAN_INBOX_DIR/runtime_proof.json
echo '{"command":"shutdown","args":{"reason":"supervisor_shutdown"},"from":"supervisor"}' > $BEAN_INBOX_DIR/stop.json
```

Reasoning commands:

```bash
echo '{"command":"run_reasoning_cycle","args":{"force_stub":true,"instruction":"reason about current state"},"from":"supervisor"}' > $BEAN_INBOX_DIR/reasoning_cycle.json
echo '{"command":"list_reasoning_proposals","from":"supervisor"}' > $BEAN_INBOX_DIR/reasoning_proposals.json
echo '{"command":"list_pending_action_candidates","from":"supervisor"}' > $BEAN_INBOX_DIR/reasoning_candidates.json
echo '{"command":"decide_action_candidate","args":{"candidate_id":"cand_example","decision":"rejected","supervisor_id":"primary_developer"},"from":"primary_developer"}' > $BEAN_INBOX_DIR/reasoning_decide.json
echo '{"command":"run_reasoning_maintenance","args":{"dry_run":true},"from":"supervisor"}' > $BEAN_INBOX_DIR/reasoning_maintenance.json
```

Speculation commands:

```bash
echo '{"command":"create_hypothesis","args":{"claim_text":"This might be a recurring loop.","claim_type":"hypothesis","evidence_level":"hypothetical"},"from":"supervisor"}' > $BEAN_INBOX_DIR/create_hypothesis.json
echo '{"command":"list_open_hypotheses","from":"supervisor"}' > $BEAN_INBOX_DIR/list_hypotheses.json
echo '{"command":"review_hypothesis","args":{"hypothesis_id":"hyp_example"},"from":"supervisor"}' > $BEAN_INBOX_DIR/review_hypothesis.json
echo '{"command":"compare_hypotheses","args":{"hypothesis_ids":["hyp_a","hyp_b"]},"from":"supervisor"}' > $BEAN_INBOX_DIR/compare_hypotheses.json
echo '{"command":"run_speculation_maintenance","args":{"dry_run":true},"from":"supervisor"}' > $BEAN_INBOX_DIR/speculation_maintenance.json
```

## Runtime proof

`run_runtime_proof` reports runtime health without touching motion hardware.

It reports:

- events
- active claims
- possibility states
- dream records
- supervisor relationships
- relationship ingestion watermark
- wisdom triggers
- wisdom activation traces
- wisdom meaning frames
- reasoning proposals
- reasoning action candidates
- reasoning context snapshots
- speculative hypotheses
- open hypotheses
- contradicted hypotheses
- resolved hypotheses
- speculation reviews
- `motion_enabled=False`
- `sentience_claimed=False`

Dreams remain synthetic artifacts, not observations.

## Architecture map

```text
memory events
  to significance scoring
  to surprise detection
  to preference formation
  to drive evaluation
  to goal proposals
  to consolidation
  to self/world model update
  to possibility-state coherence
  to epistemic audit / contradiction court / falsification check
  to dreams / uncertainty garden / dignity / inner weather / autobiography
  to relationship and trust review
  to wisdom triggers and meaning frames
  to reasoning context
  to provider output
  to reasoning proposal
  to speculation and hypothesis discipline
  to supervisor gate
  to runtime proof and health report
  to continuity summary
```

## Documentation map

| File | Purpose |
|---|---|
| `docs/brain-0.09-wisdom-module.md` | Brain 0.9 wisdom triggers, activation traces, and meaning frames. |
| `docs/brain-0.10-motion-boundary.md` | Brain 0.10 boundary explaining why physical motion is not implemented here. |
| `docs/brain-0.11-llm-reasoning-layer.md` | Brain 0.11 reasoning proposals and safety gates. |
| `docs/brain-0.12-openai-responses-api.md` | Brain 0.12 OpenAI Responses API provider. |
| `docs/brain-0.13-speculative-logic.md` | Brain 0.13 speculative logic and hypothesis discipline. |

## Known limitations

- This recovery branch needs real smoke-test execution before merge.
- Brain 0.10 physical motion is intentionally not implemented in this branch.
- The OpenAI provider is optional and requires `OPENAI_API_KEY` at runtime.
- Reasoning is proposal-only.
- Speculation is hypothesis-only.
- Physical motion remains disabled.
- Pi servo daemon and hardware motion are out of scope for this branch.

## Recommended next step

After this branch passes tests, validate the install on the Jetson with SSD-backed storage, still with physical motion disabled.
