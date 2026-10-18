# PEMDAS: Preview-First Language Processing Model

**Originator:** Daniel Boone (GitHub: [@danieloculus0-bot](https://github.com/danieloculus0-bot))  
**Recorded:** 2026-10-18  
**Status:** User-originated research specification; **not implemented, trained, benchmarked, or established as novel**  
**Intended project:** BEAN, including potential future host-specific reading and evidence-retrieval adapters  
**Document identifier:** BEAN-LP-PEMDAS-001 · Draft v0.1

## Thesis

Do not treat reading acceleration as a demand to compress away content. **Preview the entire visible information field cheaply, recognize salient actors and actions, build a relevance map, and only then allocate expensive detailed reading.** When every paragraph is relevant, read them all, but exploit the context established by the first pass.

This method is intended to preserve access to original evidence, not replace it with lossy paraphrases.

## Origin: the observed human method

Daniel described a recurring voluntary strategy used when reading technical material:

1. Survey the page or entire screen extremely quickly, sampling multiple text regions or paragraphs before reading them in sequence.
2. Identify **nouns and verbs first**: what entities are present and what those entities do.
3. Classify likely relevance, location, and relationships among paragraphs. Scan is useful even when **all** paragraphs turn out to matter.
4. Revisit and read relevant passages with the advantage of prior exposure and a spatial/semantic map.
5. Distill and retain important relationships and details while keeping access to the complete original text.

In the 2026-10-18 conversation, Daniel reported that surveying five paragraphs could take less than a second and could make subsequent reading feel at least twice as fast. These are **first-person estimates, not timed measurements or established performance results**.

## User-defined PEMDAS mnemonic

These labels are *the originator's mnemonic*, not standard grammatical abbreviations or the mathematical order-of-operations rule:

| Marker | User-assigned class | Information sought |
|---|---|---|
| **P** | **Noun** | Primary entities, subjects, objects, topics |
| **E** | **Pronoun** | Referents, continuity, who/what a term points to |
| **M** | **Verb** | Actions, processes, changes, decisions |
| **D** | **Adverb** | Manner, timing, intensity, frequency |
| **A** | **Adjective** | Properties, qualifiers, classifications |
| **S** | **Everything else** | Syntax, relations, punctuation, connective and logical operators |

**Attention rule:** Although PEMDAS is the mnemonic order, the **practical scan prioritizes nouns and verbs together** to form an *entity/action skeleton*. Pronouns and modifiers refine it. No token category is automatically unimportant.

**Non-negotiable semantic safeguard:** Scan and deep-read must protect negation, quantifiers, conditional terms, exceptions, scope, units, dates, and relational words, even when they fall in “S” (e.g., *not*, *unless*, *only*, *except*, *before*, *without*, *all*, *some*). These can invert a requirement or conclusion.

## Proposed four-stage architecture

### 1. PREVIEW: cheap field survey

- Segment a source into its original ordered paragraphs, headings, tables, and regional spans, retaining stable source offsets.
- Identify preliminary noun and verb candidates and salient signals: titles, numbers, entities, action terms, constraints, negations, anomalies.
- Survey across the **whole visible field**, including early and late regions; do not merely read the opening passage and assume the rest is irrelevant.
- Construct a small **relevance map** with passage IDs, tentative topics, entity/action anchors, and uncertainty markers. This map is an index, **not the source of truth**.

### 2. PRIME: relevance and risk allocation

- Relate the map to the current question, user intent, prior verified context, and information gaps.
- Assign each region a provisional status: **read now / inspect around it / defer but retain**.
- Boost potentially decisive passages, e.g., safety instructions, legal conditions, contradictory evidence, numbers, or caveats, regardless of grammatical class.
- Permit **read everything** as a normal outcome. The scan can still help by orienting the detailed pass.

### 3. PROCESS: targeted complete reading

- Deep-read selected source passages **with surrounding context** and sentence-level logical relations.
- Resolve pronouns and cross-paragraph dependencies; expand neighboring passages whenever the preview created ambiguity.
- When completeness matters (technical requirements, regulatory evidence, safety, legal text, audit findings), perform an exhaustive check or full read rather than relying on the preview.
- Do not claim a fact from preview anchors alone. Return to primary text before important assertions.

### 4. PRESERVE: evidence-grounded retention

- Save only **derived relevance indexes and supported findings** to the memory layer, with exact reference IDs and original offsets.
- Preserve full source material (or a stable link and immutable digest when retention is permitted) separately from compact working memory.
- Track which paragraphs were actually deep-read, which were previewed only, and what remains unchecked.
- Allow future follow-up questions to revisit all original regions, including deferred ones.

## Candidate implementation contract (not yet code)

Input:
- Source text or structured document, stable source ID, paragraph/region boundaries.
- Current task/question, completeness requirement and available computational budget.

Output:
- Paragraph-level preview map with entity/action anchors, related referents, critical operator flags, relevance hypotheses and confidence/unknown status.
- Proposed deep-read plan with paragraph offsets and explicit escalation rules.
- Read-coverage ledger and evidence-linked findings after processing.

Pseudo-flow:

```text
regions = preserve_source_and_segment(document)
preview = survey_all_regions_for_entities_actions_and_risks(regions)
plan = prioritize(preview, user_question, completeness_risk)
read = inspect_original_regions(plan, include_context=True)
if coverage_required or logical_uncertainty or contradictions:
    read = expand_or_read_all(regions, read)
return findings_with_source_offsets(read), coverage_ledger(regions, read)
```

No claim that a conventional POS tagger alone can achieve the reported human speedup. The possible mechanism is **two-pass orientation and allocation**, not magical compression or automatic token reduction.

## Falsifiable experiments

Compare on the **same held-out documents and question set**:

- **Baseline A:** Sequential full-context read.
- **Baseline B:** Conventional chunking, semantic retrieval, then context expansion.
- **Candidate C:** PEMDAS preview, relevance/risk plan, then selective or exhaustive full read.

Collect:
1. End-to-end latency, model input tokens, compute and retrieval costs, including the overhead of preview.
2. Recall of decisive requirements, contradictions, negations, exceptions, figures, and scoped conditions.
3. Unsupported assertion rate, coverage honesty, answer quality and ability to recover deferred facts.
4. Performance on *all paragraphs relevant* versus *sparse relevance* tasks.
5. Stability on unfamiliar subjects and deliberately misleading noun-verb skeletons.

Include ablations: remove POS cues; remove global survey; remove risk operators; remove the first pass entirely. Test technical documentation, prose, tabular sources, safety instructions, and cross-referenced specifications using **synthetic or permission-cleared data**.

**Success is not a faster preview alone.** Improvement must be measured as faster or cheaper **end-to-end correct answers**, without unacceptable missed evidence. If the first pass increases total cost or errors, report the negative result.

## Distinction and limitations

- Standard POS tagging, skim reading, preview reading, attention allocation, hierarchical retrieval and coarse-to-fine document processing already exist. PEMDAS should **not** be represented as an independently verified new scientific discovery.
- Human introspection is a hypothesis source, not evidence of mechanisms inside cognition or neural networks.
- The method is task-dependent. Dense requirements may favor exhaustive reading from the start.
- Linguistic labels are often ambiguous; multiword entities, passive voice, ellipsis, and languages other than English need explicit handling.
- This document establishes a dated, versioned statement in Git history. It is **not** proof of patentability, exclusivity, authorship of underlying established ideas, legal clearance, or a substitute for a prior-art/IP review.
- Publicly disclosing technical details can affect patent strategies in some jurisdictions. Seek qualified counsel **before** disclosing non-public implementation details intended for patent protection.
- BEAN's software redistribution terms are separate from this research-document notice; third-party rights and any employment or contributor agreements must be respected.

## Attribution and rights notice

**Original specification text © 2026 Daniel Boone. All rights reserved**, to the extent the stated author holds the relevant rights. The method is documented as a **proposed research approach originated and described by Daniel Boone** in a 2026-10-18 conversation. Attribution is not a claim to own generally known grammatical categories or all instances of relevance-guided reading.

No patent grant, exclusive method license, trademark registration, or third-party rights are asserted by this note. This document **does not grant a blanket redistribution or commercial software license** for BEAN.

## Promotion gate

Promote beyond a research proposal only after a reproducible implementation, regression tests, held-out comparisons, failure analysis and evidence of a meaningful measured benefit. Until then, label any public demo **experimental proposal**.
