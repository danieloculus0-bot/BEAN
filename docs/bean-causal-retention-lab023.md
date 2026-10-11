# BEAN Lab023: Causal Retention, Not Just More Code

**Status:** research experiment. This lab is designed to fail honestly. It
does not establish artificial general intelligence, model-weight updates,
unattended production autonomy, or guaranteed improvement.

## The next threshold

BEAN has previously written candidate repairs across unrelated tasks and kept
source-hashed attempt histories. That is not sufficient evidence of transferable
learning. This experiment tests the missing causal question:

> After training on three tasks, does restarting BEAN with only its saved
> general lessons improve performance on *different* tasks over the same model
> run without those lessons?

## Procedure

1. **Model proposals:** BEAN Lab021's existing author requests fresh source
   for three public training tasks: intervals, graph dependencies, inventory.
   Training source is not executed in the job holding the model API key.
2. **Independent supervision:** the existing Lab021 grader runs synthetic
   development cases with no provider key. Source is checked against its
   original SHA256 receipt.
3. **Learning:** the external coding model receives the public specification,
   its candidate, and aggregate development passes. It generates a short
   transferable hypothesis without seeing individual expected answers or
   hidden tests. BEAN's actual append-only SQLite Journal saves each claim,
   source digest and score. The journal closes and reopens before use.
4. **Transfer:** a *different job/process* reads and verifies the persistent
   journal. For each fresh repair challenge from the existing neutral agent
   arena, BEAN uses the same specified provider and source, once with no
   history and once with learned notes. Task ordering is counterbalanced.
   Model-produced files are saved as SHA256-bound candidates, not executed.
5. **Blind evaluation:** Windows and Linux credential-free jobs check
   receipt hashes, reject missing candidates, confirm comparable model
   identity, execute withheld tests and publish both scores and failures.

The withheld objectives are an as-of revision ledger and a transitive
permission graph, distinct from the original interval, dependency-order and
inventory exercises. These tasks are already public in the repository; their
tests are *not* supplied to the author. This is only a controlled pilot, not
a claim the problems are unknowable or that BEAN discovered them.

## Reproduce

Push normal changes to the experiment branch to run the Windows/Linux offline
preflight. To explicitly authorize another live model study **before this
workflow is on main**, push a commit whose message includes [lab023-live].
After the workflow is promoted to main, manual workflow_dispatch also works.
The model stages require the existing OpenRouter secret; absent credentials
or available provider quota must NOT be interpreted as learning success.

Local contract tests (mock author is explicitly a fake, NOT an AI result):

    python -m pip install pytest
    python -m pytest bean/tests/test_lifelong_transfer_lab023.py -v

Inspect the workflow artifacts:

- lab023-training-authors: original candidate byte hashes and author receipts
- lab023-development-score: credential-free scores from training
- lab023-persisted-learning: actual SQLite journal and restart proof
- lab023-unseen-author-candidates: cold and memory-arm model sources
- lab023-independent-verdict-* : independent Windows/Linux final report

## Predeclared grading

- **INCONCLUSIVE**: model or source absent, model identities do not agree,
  incomplete evidence, or verified lessons insufficient to proceed.
- **NOT_DEMONSTRATED**: both arms are comparable but learned notes failed
  to improve both tasks without regressions.
- **POSITIVE_CAUSAL_RETENTION_PILOT**: at least one new task shows more
  withheld test passes after memory restoration and the other does not regress,
  with both candidate sets present and same served model per task.

Even a positive pilot must be replicated on more unseen task families,
multiple randomized runs and an equally long *irrelevant-memory placebo*
before making strong claims about a transferable capability. More context,
order effects, stochastic model outputs and contamination of public tasks
remain possible confounds. A failure is preserved, not rewritten as a pass.

This experiment uses BEAN's real hash-chained Journal and existing coding
author, but relies on external models for programming/reflection. No
checkpoint weights are modified. No generated candidate is executed in a job
with OpenRouter credentials. No source is automatically promoted to main.

**Production promotion gate:** independently replicated positive effect,
a no-memory and placebo ablation, unseen task distributions, documented cost
per improvement, full cross-platform evidence, and scoped review.

## First live attempt: capacity-limited, not an intelligence result

The run on October 10, 2026 (local time), [38111995546](https://github.com/danieloculus0-bot/BEAN/actions/runs/38111995546), passed the Ubuntu and Windows laboratory contract tests. The live training-author step attempted all three tasks but received **HTTP 429** from OpenRouter for all three requests. The independent development report correctly showed **0/174** candidate passes, while the deliberately defective code baseline was 57/174. The learning stage therefore had zero legitimate candidates or lessons, and no transfer holdout ran. **Classification: inconclusive due to provider rate limiting.** Changing to another free-model route does not necessarily bypass platform-wide free-tier limits. No provider credits were purchased. The live workflow now requires explicit activation on its branch to avoid silently exhausting shared quotas.


## Local Ollama fallback (no OpenRouter quota required)

BEAN Lab023 now supports the genuine local Ollama API for model-generated
source and reflections. The existing BEAN append-only Journal persists its
lessons, and the independent Lab021 and arena graders check results.
The model identity is recorded; if a different provider is used in one arm,
the holdout is inconclusive. Local Ollama does NOT retrain model weights.

For Windows PowerShell, install and start Ollama from https://ollama.com,
then from a freshly updated BEAN repository run:

    ollama pull qwen2.5-coder:1.5b
    python -m bean.evaluation.lab023_ollama all --out .\bean-lab023-local

The model download is approximately 1 GB. The output directory must be new
and empty. Keep the generated local SQLite database, grading outputs, and
proposals out of source control.

The GitHub workflow at .github/workflows/bean-lab023-ollama.yml can also
run a REAL Ollama model on a temporary hosted Ubuntu runner (the smaller
qwen2.5-coder:0.5b model, approximately 398 MB), then carry its artifacts
to separate credential-free Linux and Windows evaluator jobs. Trigger the
real stages on the experiment branch with an explicitly labeled commit
[lab023-ollama-live]; ordinary pushes run offline contract tests only.

The hosted Ollama is independent of the user's local PC: a standard cloud
GitHub runner cannot connect to the Ollama server on their Windows machine.
The provider selection is explicit, and no OpenRouter credit is consumed
by the Ollama path. Performance still depends on CPU, GPU, and RAM.

Real local-inference trial is opt-in, independently scored, and retains failure evidence.


### Automatic OpenRouter-to-Ollama switchover

For local experiments, this command tries OpenRouter only if a key is set,
but starts/restarts the **entire** trial on installed local Ollama whenever the
cloud author returns HTTP 429 (or reflections cannot supply enough verified
lessons). If remote requests fail partway through transfer with 429, all
cloud artifacts are discarded and BEAN starts the local experiment from a
clean state. This prevents an invalid comparison of cold and memory arms
using different model backends.

    python -m bean.evaluation.lab023_ollama auto --out .\bean-lab023-auto

Unlike the hosted GitHub alternative, this automatic mode requires the
local Ollama server and chosen model if the cloud service is unavailable.
Only explicit local model artifacts carry the Ollama provider identity.


## Genuine Ollama hosted pilot outcome, run 38112389946

The October 10 local-time pilot used Ollama qwen2.5-coder:0.5b running
inside GitHub Actions, with NO OpenRouter credits. Both Linux and Windows
passed all offline provider and BEAN journal regression tests.

- All three training proposals were generated by the actual local model.
- Independent development: 56/174 test passes, versus 57/174 for the
  known-broken original source. **No training improvement demonstrated.**
- Model wrote three short reflections; BEAN stored and reopened them
  successfully with a stable SHA256 journal tip. No neural weights changed.
- On the two new challenges, the cold-context arm passed 4 held-out tests
  and the retained-context arm passed 6, but the experiment had missing
  candidates and did not establish identical served-model receipts for
  every pair. Both independent Linux and Windows judges classified the
  result **INCONCLUSIVE**, not a learned advantage.
- The exact log, immutable model attempts and independent verdict
  artifacts are linked to
  https://github.com/danieloculus0-bot/BEAN/actions/runs/38112389946

The missing candidates are informative: a 0.5B local coder can struggle
with a full-module Python repair contract. Try the documented 1.5B or a
larger local coder, capture provider identity even when candidate parsing
fails, and repeat independent holdouts before promotion. Never relabel
a missing candidate as a pass.
