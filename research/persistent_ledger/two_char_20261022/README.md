# BEAN two-character ledger research (2026-10-22)

**Status:** isolated measured synthetic storage/replay experiment. No Core integration, policy change, production deployment, or demonstrated reinforcement learning.

## Why
Test whether eight typed, two-character value references per observation (16 ASCII bytes per row) offer recoverable, efficient memory alongside the existing BEAN Information Balloon and SQLite/hash-chained event ledger. Compare full reference table + body costs, not just raw 16-character strings.

## Existing architecture reused conceptually
- BEAN's append-only ledger and replay + source-preserving principles from `research/PERSISTENT_LEDGER.md`.
- Information Balloon's measured compressor/recovery discipline and the original 3,000-episode research in PR #147.
- No new Q updates here, and no substitution for current `bean/optimization/portfolio_ledger.py`.

## Results (3,000 records and 24,000 values per condition)
| Condition | JSON+gzip | Two-char+gzip | One-byte dictionary+gzip | Hierarchical two-char+gzip |
| --- | ---: | ---: | ---: | ---: |
| Four values/slot | 15,140 B | 8,609 B | 7,131 B | 10,499 B |
| 24 values/slot | 57,709 B | 25,112 B | 17,675 B | 45,284 B |
| 80 values/slot | 112,537 B | 37,730 B | 25,758 B | 63,733 B |

All 9,000 synthetic original-value events passed exact decoding and SQLite-close/restart chain replay. Gzip roundtrip, duplicate-event rejection, symbol-validation, numeric-slot capacity failure and a hash-chain tamper canary also passed. The original values and full event receipts were saved as a separate conversation-attached 1.63 MB gzip JSONL plus a SQLite database, NOT committed into this public GitHub branch. This branch retains reproducible aggregate measurements and comparison receipts only.

**Critical findings:** Two-character dictionaries beat gzip-compressed JSON in all three synthetic 3,000-row workloads, but conventional one-byte dictionaries beat two-character encoding in all three, and Bzip2 beat it for some workloads. A four-tier parent/reference DAG remained lossless but increased storage in all three. For very small datasets, the two-character dictionary overhead caused substantial regressions. The 16-byte stream is not the fully loaded package.

## Reproducibility limits
- Inputs are deterministic synthetic inspection-attribute strings; not customer or workplace data.
- Each row contains eight attributes. Slot alphabets alternate uppercase, lowercase, decimal digits, and symbol pairs. Mixed-case pairs are invalid within a single two-character token. A single ASCII space is a pattern wildcard in experiments, never an omitted source value.
- Dictionaries are fixed per scenario; the highest-cardinality numeric slots were 80 values, below the 100-code two-digit capacity.
- Four-level graph nodes are `(parent_ref, four-character segment)` with two-byte leaf addresses; all four segments are recovered to reconstruct the exact 16-character record.
- The comparison is storage-only with local Python timing observations. It does NOT establish semantic reasoning gain, memory accuracy advantage, speed advantage, Q-learning gain, independent source truth or Jetson savings.
- The complete tested script, SQLite event database, 9,000 per-event value records, the 12 comparison receipts, compressed source/control archives, hashes and scoreboards are packaged as a downloadable zip attachment in the originating ChatGPT conversation. The root code is not copied into this branch, so rerunning this GitHub branch alone cannot reproduce the full test.
- `scoreboard.json` includes source/code hashes and digest of the separate event archive, and `comparison_events.jsonl` keeps twelve hash-linked measured summary observations. Neither is a replacement for the full 9,000-value archive.

## Research conclusion
Use two-character codes as a **human-readable symbolic address and relationship namespace** if the query/navigation payoff is demonstrated. For tight storage, encode those same dictionary IDs into dense binary bytes or bit-packed references underneath. The next meaningful benchmark is indexed associative retrieval accuracy and time against a conventional SQLite/indexed baseline, not another ratio-only compression victory.
