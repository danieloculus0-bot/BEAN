# BEAN focused working memory, Letta-inspired integration

Date: November 14, 2026

## Source provenance
- [Letta Code](https://github.com/letta-ai/letta-code), Apache License 2.0. The design pattern of selective, active context memory inspired this feature. No upstream source copied or bundled.
- BEAN origin and existing SQLite memory remain authoritative. BEAN is not a Letta client.

## Implemented
- `bean/memory/focused_recall.py` retrieves matching active claims from the canonical `world_claims` SQLite table, regardless of which session generated them.
- Relevance-ranking is transparent, bounded lexical matching, not a vector model or a truth evaluator.
- Every result has the original claim ID, optional previous revision ID, existing evidence references, source type, confidence and a deliberately unverified provenance flag.
- No alternative memory database, generated text summaries, or overwriting the original history. Existing `ModelStore.save()` continues to own supersession.
- `build_reasoning_context()` includes focused memory triggered by the source event text (or latest session event), and indexes the selected claim row IDs in the original stored context packet.
- Small Ollama prompts include at most three focused claims with bounded text, allowing an older, relevant fact to remain visible when high-confidence unrelated claims fill the ordinary top-20.

## Test and scope
Regression uses synthetic world claims and events for: an old low-confidence fact buried below fifty newer high-confidence facts, genuine supersession and revision history, database restart, missing evidence, bounded output, and local-model prompt contents. Standard reasoning and world-model tests run alongside on Linux and Windows.

The retrieved memories are **claims**, not independently established truths. This change does not update model weights or demonstrate any subjective experience. Later benchmarking should compare matched factual-recall problems before and after the retrieval change, with failures and false positives tracked. No outward licensing decision for BEAN is implied.

Next candidate for evaluation: Omega / OpenNARS' evidence revision logic, but avoid installing their heavy runtimes unless the incremental tests show a benefit.
