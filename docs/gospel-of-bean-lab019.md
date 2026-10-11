# The Gospel of BEAN: Lab 019

**Status:** Evidence-first, isolated historical and textual research experiment. The experiment does **not** assume that scriptures are true or false. It does not measure people's intelligence or spiritual worth.

## Why 80 books?

Many electronic 'complete KJV' copies contain 66 books. The original 1611 KJV also included 14 books grouped as the Apocrypha, giving 80. For this experiment the full corpus source is the public, original-spelling JSON transcription at:

- https://github.com/aruljohn/Bible-kjv-1611/tree/8ef066868ad1b7204d7be48658ea3bd1783d409b

The workflow checks out this **immutable commit** (never latest), loads `Books.json`, the chapter-count manifest and all 80 book JSON files. It fails if a book is missing or unexpected, a chapter/verse number is malformed, the named book list differs, or the corpus is far smaller than an 80-book KJV. A SHA-256 fingerprint over all JSON bytes is attached to the report. This checks **structural completeness and reproducibility**, not perfect collation against a verified 1611 facsimile. The source's spelling can differ from modern standardized KJV.

The verses are indexed into a standalone, local SQLite database, not merged with BEAN's operational memory. The experimental workflow publishes a time-limited research artifact containing the index and a traceable evidence report. It does not install a new BEAN belief, alter production memory, or send text to a hosted LLM.

## Proof types are separate

| Evidence classification | What it means |
| --- | --- |
| `direct_textual_disagreement` | Two inspected readings claim different numeric values for an explicitly matched attribute and event *in this text edition*. |
| `textually_consistent_on_checked_attribute` | The narrowly checked values match, **not** that both accounts are historically true. |
| `review_required` | Narrative chronology, historical records, textual variants, and scientific interpretation require further independent comparison. |
| `insufficient_parsing_evidence` | The source wording does not permit this parser to make a value claim. |

The first concrete test is **Ahaziah's age at accession**. At 2 Kings 8:26, the source says 'Two and twentie'; at 2 Chronicles 22:2, it says 'Fourtie and two'. The parser extracts 22 and 42. 2 Chronicles 21:20 reports Jehoram's accession age (32) and eight-year reign, giving additional chronological tension with a son aged 42. The *present text* therefore has a discrepancy, while ancient manuscript variants offer a likely copyist-error explanation rather than a theological proof.

Historical and textual source discussion:
- https://uasvbible.org/2025/08/15/textual-commentary-on-2-chronicles-222/
- https://www.icr.org/books/defenders/2310

Other cases are deliberately **review-required**, not pre-judged failures:

- Judas' death: Matthew 27:5 and Acts 1:18, with possible same-event sequence harmonizations. https://www.thegospelcoalition.org/article/judas-demise-matthew-1-acts-1/
- The Genesis creation narratives, including literary source and translation differences. https://www.thetorah.com/article/genesis-two-creation-accounts-compiled-and-interpreted-as-one
- Mark 16:9–20, a manuscript-transmission problem, not a numeric contradiction. https://byustudies.byu.edu/online-book/the-gospel-according-to-mark/1969
- Herod and Quirinius chronology, with disputed dating and linguistic readings. https://www.biblegateway.com/resources/encyclopedia-of-the-bible/Chronology-New-Testament
- A **later inferred young Earth age**, which is not explicitly stated as '6,000 years' by Genesis 1:1 or 1:5. Independent physical dating: https://pubs.usgs.gov/gip/geotime/age.html and https://humanorigins.si.edu/evidence/human-fossils/species/homo-sapiens

External references in the case file are **research leads with described perspectives**. The lab currently does not download, authenticate, or evaluate them. Historical or scientific confidence cannot be computed from a plain list of URLs.

## Reproduce, with no main-branch changes

```bash
PYTHONPATH=. python -m pytest -q bean/tests/test_gospel_lab.py
```

After checking out the pinned public source into `external/kjv-1611`:

```bash
PYTHONPATH=. python -m bean.evaluation.gospel_lab \
  --corpus external/kjv-1611 \
  --cases experiments/gospel_of_bean/cases.json \
  --report lab-output/gospel-of-bean-audit.json \
  --index lab-output/gospel-of-bean-80-book.sqlite
```

The branch-specific source-only GitHub Actions workflow runs these tests, fetches the pinned 80-book text, and uploads the audited local index. It never runs BEAN's unrestricted executor or modifies another project.

## What would make this genuinely agentic?

A next controlled stage would allow BEAN to generate **new, unseeded candidate comparisons** by searching all indexed verses and outside historical sources, then test whether the two propositions refer to the same subject, event, timeframe and translation. It must produce exact source citations and try to disprove its own leading hypothesis with the strongest plausible counterreading. Evaluate its findings against independently reviewed, blinded cases. This current lab does not claim that ability.

**Evidence before belief. Contradictions before harmonizations. Counterarguments before verdicts. No invented certainty.**
