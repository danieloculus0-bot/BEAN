# BEAN Lab 020 — Real model-produced Core repair, October 11 2026

## Verified run

Original research run: https://github.com/danieloculus0-bot/BEAN/actions/runs/38109612791

The challenge used the real production source bean/optimization/selection.py. Its existing duplicate check compared raw identifiers, so semantically matching labels with different capitalization, surrounding whitespace, or casefold-equivalent Unicode could be recorded twice. The original module passed **11 of 14** independently authored development contract checks.

| Generator / iteration | Model served | Development score | Result |
| --- | --- | --- | --- |
| LLM round 0 | nvidia/nemotron-3-ultra-550b-a55b:free | **14 / 14** | Valid source proposal |
| LLM round 1 | OpenRouter free route, invalid model response | 0 / 14 evaluated | Rejected (source syntax) |
| LLM round 2 | nvidia/nemotron-3-super-120b-a12b:free | **14 / 14** | Different valid source proposal |
| AST brute-force comparator | BEAN ASTBruteForce | At most 11 / 14 | Zero validated repairs across **25** trials |

The selected first-round model source SHA-256 was
521c39138cc271600be5527085aaaa1b3f8d6573e5c6c404db615c734d202fb6.
Its 14/14 result was independently evaluated in a job without model credentials. An additional seven never-feedback identity cases were run only during final selection. The selected proposal passed **7/7**, returning verdict **LLM_REPAIR_VALIDATED_ON_FRESH_HOLDOUT**.

The original generator output is available as GitHub Actions artifact lab020-gen0. The production candidate in this PR keeps the model's strip().casefold() uniqueness method and original output spelling, with a small formatting/transcription cleanup; it is not represented as an identical-bytes copy of the model artifact. This PR imports all 21 independent development and holdout regressions directly into Core's full cross-platform CI.

## Scientific limits

This demonstrates an LLM writing a bounded repair to real BEAN Core, preserving the public API under existing and new checks. It is **not proof of model weight learning** or general recursive code improvement. Across three requests the free routing gateway served different models; the returned feedback counts apply to distinct models, so changes across iterations cannot establish individual-model learning. The test source was not in the prompt but is visible in a public research repository, not a cryptographically sealed blind benchmark.

The original Lab020 research branch has a **Windows-only test harness source-newline hashing defect**; Windows protocol CI did not pass, although its Linux protocol tests, independent code evaluation and fresh holdout did. This review PR must independently pass all Linux/Windows Core regressions. It does not promote the experiment's original workflow or assert a green Windows run that did not occur.

No workplace or private data, payment fallback, model key, generated arbitrary code execution in a key-bearing job, or permission to self-merge was used.

Evidence: https://github.com/danieloculus0-bot/BEAN/pull/51
