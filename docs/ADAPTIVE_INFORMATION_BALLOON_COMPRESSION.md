# BEAN Information Balloon: adaptive lossless compression research

Status: experimental only. No live data ingest, runtime memory replacement, elevated information access, production learning-weight update or retention-policy override.

Code: bean/optimization/information_balloon.py
Tests: bean/tests/test_information_balloon.py
Study: python experiments/information_balloon/run.py --output balloon-study.json
CI: .github/workflows/information-balloon.yml

## Research objective: remove working weight without discarding information

Given authorized source records and explicit budget B (compressed shelf bytes),
budget C (active context bytes), and minimum query recall tau:

1. Retain exact recoverable source bytes, with independently checked SHA-256.
2. Find reversible candidate codec(s) that keep the whole shelf within B.
3. When a codec can meet B, prefer the **least measured encoding work** over ever-larger ratios.
4. Show BEAN the most relevant evidence references in C, and independently measure the fraction of expected references retrieved.
5. Fail explicitly if a required constraint cannot be met. Preserve every omitted ID, negative result, full evidence receipt and immutable cold original.

Compression does NOT provide permission to read additional source systems. This only maximizes the amount of already-authorized information accessible in a bounded working memory.

## Why this is a valid experiment, and what theory actually says

- Information Bottleneck, Tishby/Pereira/Bialek (2000): information about a relevant objective should survive bottleneck compression. https://arxiv.org/abs/physics/0004057
- Rate-distortion approach to databases: compressed indexing and content-based retrieval are coupled, and retrieval distortion must be assessed explicitly. IEEE Transactions on Information Theory 50(6), 2004: https://doi.org/10.1109/TIT.2004.828068
- Bottleneck-Minimal Indexing for Generative Document Retrieval (Du/Xiu/Tanaka-Ishii, ICML 2024): indexes should preserve task-relevant information; measure that separately from full-document byte fidelity. https://proceedings.mlr.press/v235/du24j.html
- Minimum Description Length (Rissanen, 1978): a shorter data file is not a true win if its model/dictionary costs more than the savings. We count BEAN's dictionary, version and header in package size. https://doi.org/10.1016/0005-1098(78)90005-5
- Weissman Score: created for the TV show Silicon Valley by Tsachy Weissman and Vinith Misra, but it is a genuine ratio/time comparison. IEEE Spectrum: https://spectrum.ieee.org/a-madefortv-compression-metric-moves-to-the-real-world . The original logarithm-of-time formula depends on chosen units and can misbehave near one. Our diagnostic is explicitly a **Weissman-style variant**, not the canonical score:

  Wstar = (ratio / reference_ratio) * log(1 + reference_ms/1ms) / log(1 + candidate_ms/1ms).

  This is secondary to exact integrity and the defined budget/recall goal. It is not a universal leaderboard score.
- NIST FIPS 198-1: HMAC is a keyed mechanism for message authentication: https://csrc.nist.gov/pubs/fips/198-1/final . SHA-256 alone detects accidental corruption against an independently trusted digest but does not authenticate an attacker-controlled replacement of BOTH data and digest.

Research outcomes from these studies motivate testing, NOT a claim that our encoder beats theory or has academic novelty.

## What BEAN actually devises and iteratively measures

BEAN's experimental recipe proposer learns a byte-token dictionary from the training partition only: repeated 4, 6, 8 or 12 byte n-grams, with 8, 16 or 32 candidate entries. The dictionary is a reversible escape-coded transform placed before zlib. It is self-describing, and accounts for dictionary overhead. BEAN mutates token width, dictionary size and compression level, compares against standard zlib/bz2/lzma/raw controls, and measures real package bytes and encode times.

It stores each trial's recipe, training/tuning hashes, objective, measured result and failure. Only a correctly decoded candidate gets an eligible score. It uses disjoint training, tuning and held-out subsets: the final heldout is assessed **once** after candidate selection. No learned neural model is implied by this procedural optimizer.

Limitations: local adaptive recipe search is not proof of global minimality, an entropy bound or a general-purpose novel compressor. Timing is local to the CI machine. Three synthetic seeds do not demonstrate real-world generalization or perpetual self-improvement.

## Exact data-integrity and retention policy

The compressed working shelf is NEVER the only copy of evidence. The source remains authoritative.

- Source bytes are saved in content-addressed, write-once cold files before a candidate is committed.
- Every codec/package is versioned, carries a source digest and fully included dictionary, rejects malformed headers, truncated/concatenated compressed streams, size-bound violations and exact recovery differences.
- Optional HMAC-SHA256 with an externally protected key authenticates the archive; the key is never written to the package or Github. Trusted external manifest digests may also anchor integrity.
- The retention trial reopens BOTH cold source and packed candidate and compares exact bytes before issuing a write-once receipt.
- No existing source or candidate is silently overwritten or removed by compression. A failed candidate leaves the cold source intact.
- If the working budget excludes any record, every excluded ID is recorded. A partial shelf is NOT called complete.
- Active context retains source references (IDs and hashes). It is allowed to be summarized, and reports recall versus expected matches. The original contents remain individually recoverable.
- Enterprise data retention expirations, access control, consent and legally required secure deletion remain responsibilities of the host system. This experiment does not implement that lifecycle. No independent authorization is granted to obtain more data.

## Measurements and clear failure criteria

Report full source hash, bytes and record counts, independent training/tuning/holdout sizes, actual package bytes, elapsed milliseconds and exact recovery, chosen recipe, all failed trials, which records fit, source references, query-recall fractions, and the worker/commit. The CI job stores full experiment JSON receipts, not a fabricated success score.

Falsifiers: even one byte mismatch; authentication with a wrong key; missing evidence after restart; compression recipes losing to ordinary gzip on the objective; a context window too small to recover expected references; or a persistent reduction in holdout retrieval quality.

Next requirement before merging into main: recreate actual ledger JSONL and Q-state patterns with synthetic data, rebuild BEAN Core from packages, run blinded retrieval tests, and measure memory, CPU and storage cost on representative Jetson/older hardware. No production migration until those results exist.
