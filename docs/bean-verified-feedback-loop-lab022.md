# BEAN Lab022: Evidence-led revision of model-authored code

## Actual input evidence

Core [run 38109084399](https://github.com/danieloculus0-bot/BEAN/actions/runs/38109084399) produced a genuinely model-authored nine-line change to the Bridge's Midnight RMA Paradox. Its sealed cross-platform verifier rejected the change. The Ubuntu job ran 106 tests with five failures remaining (RMA and production date-window invariance). This partial repair is NOT considered a success.

## Model-independent feedback cycle

This lab retrieves the original Core model candidate and actual independently failed Ubuntu CI receipt from that specific run using read-only cross-run GitHub Actions artifact access. The revision author checks the SHA of the pinned Bridge source and oracle, the prior candidate, the original model receipt and the independent verifier receipt before doing any inference.

The author passes the PREVIOUS REAL MODEL-WRITTEN SOURCE and a bounded, sanitized summary of remaining failure categories to an OpenRouter free model. It asks for another arbitrary JSON source edit plan and accepts no hard-coded patch. It writes a chained evidence receipt with previous candidate hashes and the independent failure receipt hash. It never executes model-authored code in its credential-bearing job.

Separate Linux and Windows runners have NO model secret or GitHub write permission. They rerun the Bridge's original red baseline, all existing tests, the untouched original Midnight oracle and 540 additional metamorphic invariance comparisons (60 fixed and 120 fresh scenarios, three properties each). A candidate must pass on BOTH platforms to count.

The human-authored control in [Bridge PR #22](https://github.com/danieloculus0-bot/BEAN-AI-Bridge-/pull/22) remains unmerged and never appears in the model prompt. No model-written patch is automatically merged or deployed.

## Scope limits

This is one genuine model revision from persisted, independently tested failure feedback, not an indefinite self-learning daemon or generalized model-level intelligence. The inputs are synthetic; they do not establish the site's official business-calendar semantics. Saved run artifacts are pinned for reproducibility, but do not yet constitute cross-run automatically selected memory. A future durable queue should generalize case selection and stopping conditions.

## Tests

Offline Python tests (no hosted-model access required):

    python -m pytest bean/tests/test_bridge_peer_live_author.py bean/tests/test_bridge_feedback_revision.py -q

The new workflow is designed to execute its first real feedback-driven revision when this lab is safely merged to Core main.
