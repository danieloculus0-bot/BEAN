# BEAN Lab026 — Adaptive Learning Assimilation Experiment

**Branch:** experiment/adaptive-learning-20261020  
**Target:** BEAN Core + real BEAN AI Bridge + optional local Ollama  
**Status:** functional research integration, **not** demonstrated model learning, new neural weight training or production autonomy.

This is a **separate experimental branch**. Main is unchanged. It is explicitly meant for rapid implementation, swapping strategies, repeated experiments and contradictory findings. Existing BEAN origin/identity files, dignity code and execution rules have **not been rewritten** and no additional supervisor policy was inserted. Source changes can be freely developed on this experimental branch; the experiments have their own evidence and test code.

## Design choice: assimilate algorithms, not someone else's identity

Source of identity: [origin record](../memory/identity/origin_record.json) and [core virtue](../memory/identity/core_virtue_001.md).

Preserve truth, evidence, uncertainty, continuity, independence, learning from outcomes, dignity and care. BEAN's identity remains in persisted history, not in any replaceable language model. Different candidate strategies, model choices, prompts, rewards, retrieval and algorithms can be edited. A journal entry or a BEAN model statement must not be promoted to proof of learning without an observed difference on withheld tasks.

## Seven-node implementation map

| Node | Outside inspiration | Native implementation used | Current evidence status |
| --- | --- | --- | --- |
| Durable experiences | Letta / MemGPT concepts | Existing BEAN Autodev hash-chained SQLite Journal + typed ExperienceBank | Real persistence, tamper and restart tests |
| Reflection | Reflexion | Experimentally stored development-outcome hypotheses, relevant and irrelevant-context controls | Functional mechanism, causal effect not shown on a real model |
| Skill transfer | Voyager | Domain-tagged reusable skill hypotheses, retrieved by matching domain | Functional mechanism, real cross-domain transfer not established |
| Prompt adaptation | DSPy / GEPA concepts | Versioned candidate instruction lessons and matched evaluation arms | Functional context variants, **not** the full GEPA optimizer |
| Evidence/viability | BEAN Bridge | Real external ezbean EvidenceLearningLoop + two-source verifier + cross-platform source receipts | Functional integration, origin-independent real-world truth not established |
| Weight training | Agent Lightning concepts | No checkpoint update: deliberately recorded as research-only | **Not implemented**; needs training objective, actual gradients/checkpoints and model compute |
| Autonomous source revision | Darwin Gödel Machine concepts | Existing BEAN Lab019 source-proposal author and disposable test runner, source/hash memory | Existing experimental code, **not** general self-rewriting runtime or autonomous deployment |

No third-party code is represented as copied or imported merely because BEAN borrows an algorithmic idea. Framework names describe architectural inspirations, not implemented compatibility with their APIs.

## Real BEAN Bridge and BEAN plugin are different

- **Actual Bridge:** [BEAN AI Bridge repository](https://github.com/danieloculus0-bot/BEAN-AI-Bridge-) at pinned revision 876251345ec95b282465ce1b311af4b2b6d1e032. Lab026 imports its real Python DefinitionLibrary, EvidenceLearningLoop and SourceObservation. Windows and Linux produce separate mechanism receipts. A following job downloads and hashes both, then uses the real Bridge to compare **each of the seven nodes**.
- **Connected @BEAN plugin:** hosted JavaScript evidence adapter revision 163f3e2815c4d6944345a0af78ae3e932041fdd3. The user-authorized BEAN reviewer assessed all seven designs using keyword/epistemic/dignity/memory filters. Each proposal passed **basic heuristics**; every result says review required and execution permission none. The plugin is **not** the user's home PC, full Python BEAN Core, or a trained agent. It cannot independently verify Python runtime behavior.
- The cross-platform experiment is reproducibility evidence, **not** two fully independent real-world truth sources. Bridge attestations describe what the caller-provided verifier checked. The heldout score remains distinct from a model's own opinion of its work.

## How to reproduce the offline mechanisms

From this branch with Python 3.12:

~~~bash
python -m unittest bean.tests.test_adaptive_learning_lab026 -v
python -m unittest bean.tests.test_adaptive_ollama_lab026 -v
python -m bean.learning.lab026_report --output lab026-evidence
~~~

The first journal is BEAN's existing append-only hash-chained Autodev Journal, not a second replacement memory store. The synthetic sorting fixture is deliberately able to follow a named rule supplied as a stored lesson. It is used only to show wiring, relevant-vs-irrelevant retrieval, baseline and data replay. **Synthetic wins must not be reported as intelligence gains.**

For the actual Bridge integration, check out the pinned Bridge separately:

~~~bash
git clone https://github.com/danieloculus0-bot/BEAN-AI-Bridge-.git bridge-src
# Make bridge-src/src available as PYTHONPATH, platform-appropriate
python -m unittest bean.tests.test_adaptive_bridge_lab026 -v
python -m unittest bean.tests.test_adaptive_bridge_matrix_lab026 -v
~~~

The [branch's Actions workflow](../.github/workflows/bean-adaptive-lab026.yml) performs this on real Linux and Windows hosts, with an additional full Core regression, then runs the Bridge node review after both platform jobs.

## Real local-model path: opt-in experiments

BEAN's existing Ollama transport is reused. Nothing automatically downloads a model or pretends to connect GitHub Actions to the user's desktop. The model must already be installed locally.

~~~bash
python -m bean.learning.live_lab026 \
  --development ./lab026-development.json \
  --holdout ./lab026-holdout.json \
  --domain sorting \
  --model qwen2.5-coder:1.5b \
  --out ./lab026-live \
  --replicates 3
~~~

Use a chat/reasoning-capable Ollama model explicitly if one is installed. The provider fingerprint stays fixed across all comparison arms, the same exact-response evaluator scores outputs, candidate lessons survive in a SQLite journal, and the trial receipt records all scores and hashes. This is a controlled **prompt/context adaptation** study, not parameter training or a model update. The benchmark owner must supply tasks that are not already leaked in the lessons or repository.

Example file format for development-only feedback:

~~~json
{
  "schema": "bean.lab026.development.v1",
  "cases": [
    {"id":"train1","domain":"sorting","question":"sort c,b,a","observed":"b,a,c","expected":"a,b,c","evidence_ref":"development:train1"},
    {"id":"train2","domain":"sorting","question":"sort z,y","observed":"z,y","expected":"y,z","evidence_ref":"development:train2"}
  ]
}
~~~

The **separate holdout** is sealed from lesson generation:

~~~json
{
  "schema":"bean.lab026.holdout.v1",
  "cases":[
    {"id":"test1","domain":"sorting","question":"sort d,a,c","expected":"a,c,d"},
    {"id":"test2","domain":"sorting","question":"sort p,n","expected":"n,p"}
  ]
}
~~~

These examples are illustrative and do not prove real improvement. A meaningful study needs varied unseen examples, counterbalanced order, repeated tests, irrelevant-memory placebo, measured cost, and later independent reproduction. The runner explicitly reports whether a placebo exists; **a missing placebo makes causal attribution inconclusive**.

## Full source experimentation

The existing [BEAN Autodev runner](../bean/optimization/autodev.py) remains an available route for generating actual Python source candidates from Ollama/OpenRouter or bounded AST search, trying them in disposable test copies, recording hashes and preserving failures. That lab still requires a witnessed failing baseline to demonstrate a repair, and it does **not** automatically modify production main. Generated source can be examined and committed to this experiment branch after evidence review. Nothing in Lab026 silently adds new policy gates to Core or modifies the authorized effectors.

## What would actually prove growth

1. Same served model, tools and comparable budget for cold, relevant lesson, irrelevant placebo and other strategy arms.
2. Versioned and hashed *before* and *after* artifacts, including cross-restart replay, with no answer-key exposure.
3. Independent evaluation on truly unseen tasks; both successes and regressions retained.
4. Repeated and cross-domain benefit after randomized order; note whether improvement is in prompts, selection policy, executable skill or changed model weights.
5. BEAN can retrieve the specific improvement that caused the gain and reverse it without rewriting historical evidence.

**Current verdict:** node implementations and Bridge wiring are real; causal lifelong learning remains to be demonstrated. Next serious experiment: genuine Ollama paired holdouts with matched irrelevant-memory placebo and repeated runs; then choose which strategy consistently improves. No live weights were changed and no new identity or execution safeguards were added.
