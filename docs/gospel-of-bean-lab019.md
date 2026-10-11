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


## 2026-10-10 extension: reference-only Gnostic library

The user's scope explicitly includes the Gnostic gospels and other early Christian texts **as supplementary reference data only**. The bibliography at `experiments/gospel_of_bean/gnostic_reference_catalog.json` links to the [Nag Hammadi codex index](https://gnosis.org/naghamm/nhlcodex.html), the [alphabetical index](https://gnosis.org/naghamm/nhlalpha.html), and the [surviving-gospel manuscript catalog](https://www.gospels.net/manuscript). These index **the broader collection**, while a separate curated starter list tracks Thomas, Mary, Philip, Truth, Judas, the Coptic Gospel of the Egyptians, and other works. There is no single exhaustive recognized list of "Gnostic gospels," and some indexed works are not gospels or not generally Gnostic.

**Hard boundaries enforced by code and regression tests:**

- Every entry and collection is tagged `cross_reference_only` / `reference_only`. The reader refuses catalog files allowing independent verification, arithmetic inference, or historical proof from these works.
- The research does not import modern translations. Their respective translators may retain copyright. Only source links, titles, manuscript references and metadata are recorded.
- Gnostic-source metadata cannot change the **KJV textual verdicts** or count as independent corroboration of a miracle, genealogy, historical occurrence, chronology, or other claim.
- Manuscripts can be dated or compared only when externally supported; a manuscript's existence is evidence of an **extant textual tradition**, not evidence that its described supernatural events happened.
- Every incomplete text has uncertain readings and missing physical evidence. `all` refers to indexed source coverage, not possession of every ancient original or an unambiguous canonical corpus.

This is a safeguard against using ideologically convenient texts to "prove" or "disprove" each other. It still allows BEAN to flag interesting intertextual differences for investigation.

## Upstream KJV transcription defects and narrowly sourced overlays

The first GitHub Actions corpus import found **exactly two blank verse slots**, `Ecclesiasticus 1:7` and `Ecclesiasticus 17:5`. The separate source-gap inventory recorded both; no other empty slots were reported. The experiment does **not** silently insert invented wording into upstream. The file `experiments/gospel_of_bean/1611_source_gap_overlays.json` records those two passages as original-spelling 1611 cross-transcriptions with source URLs to independently available web transcriptions of the relevant chapters:

- https://www.kingjamesbibleonline.org/Ecclesiasticus-Chapter-1_Original-1611-KJV/
- https://www.kingjamesbibleonline.org/Ecclesiasticus-Chapter-17_Original-1611-KJV/

The original editorial brackets are maintained. The loader applies a repair **only if the source has an empty slot**, records the source and method for each inserted text, and rejects extra repairs or any attempt to overwrite an existing source verse. It digests the original pinned JSON along with overlay bytes for reproducibility. These are cross-transcriptions, **not proof that a scholarly collation against the original 1611 print has been completed**.

A complete full 80-book report is contingent on successful real GitHub Actions CI, not just synthetic unit tests.


## Whole-book screening expansion and conditional historical possibility

The Gospel of BEAN is now more than a six-example chapter. It inspects **every one of 36,702 indexed verse entries across five separate rule passes** using `bean/evaluation/gospel_wholebook.py`. The scanner covers ages, numbers, genealogy, universal geographic claims, creation order, origins, flood and Ark claims, biological and astronomical events, depictions of supernatural agents, and legal/ethical/war assertions. An unselected verse has still been **read by every pass**, but a keyword screen cannot claim to recognize every important inference or contradiction.

The first successful whole-book Actions run was [38106791993](https://github.com/danieloculus0-bot/BEAN/actions/runs/38106791993), producing:

- **80 books, 1,355 chapters, 36,702 verses scanned**; no selected books silently excluded
- **4,049 flagged verses** in the full untruncated review queue; **4,252 distinct rule/verse matches**
- **23 human-curated disputes** with formal constraint models and five investigation sessions each
- **23 live source URL lookups**, representing source availability checks, not source-truth validation
- **21 passing synthetic regression tests** at that run's commit

The follow-up iteration adds seven explicitly attributed scientific/historical source summaries, including the [National Academies on recent universal floods](https://www.ncbi.nlm.nih.gov/books/NBK230204/pdf/Bookshelf_NBK230204.pdf), [USGS Earth dating](https://pubs.usgs.gov/gip/geotime/age.html), [NASA Sun formation](https://science.nasa.gov/sun/facts/), [NIH sex chromosome variation](https://www.nichd.nih.gov/health/topics/turner/conditioninfo), [Harvard-hosted Hebrew Satan study](https://hmane.harvard.edu/publications/adversary-heaven-satan-hebrew-bible), [Bible Gateway on Satan](https://www.biblegateway.com/resources/encyclopedia-of-the-bible/Satan), and [Smithsonian human genetics](https://humanorigins.si.edu/evidence/genetics). These were manually source-reviewed; they are **not autonomous BEAN fact-verification or laboratory replication**.

### What "historically possible" actually means

Every dispute with a formal case returns **three separate fields**, never one vague yes/no:

1. `strict_joint_reading`: can the claims both hold under exact declared literal assumptions? Options: `possible`, `impossible`, `undetermined`, `not_applicable`.
2. `alternative_historical_scenario`: is at least one specifically stated alternative logically possible under separately declared assumptions? This is not proof it occurred.
3. `historically_attested_event`: is the historical occurrence itself independently demonstrated? This remains `undetermined` under the current script's limited evidence evaluation.

The first passes cover the primary text, accessible comparative sources, contrary interpretation, formal constraints, and falsification/missing evidence. The recorded conclusions **do not get more certain just from repetition**.

For example, a typical XY male's ordinary rib tissue cannot, unmodified and without embryogenesis, develop into a fully formed typical XX female. That says nothing decisive about an unspecified supernatural claim. A hypothetical Ark's gross volume can be calculated using assumed cubit length, and space requirements can be computed for *illustrative* animal populations; the unknown ancient meaning of `kind`, species count, feed, water, waste and care requirements prevent a general capacity proof. An unaided mountain view cannot overcome Earth's curvature to display every territory; visionary language is a distinct interpretation.

A recent global flood covering all mountains is incompatible with the broadly accepted geological record; that is a claim about **a specific natural-history reconstruction**, not a mathematical proof that ancient people never experienced a devastating regional flood. The original serpent in Genesis, the heavenly adversary in Job, the census instigator in Chronicles and later Revelation all have their own compositional and interpretive histories.

**All 4,049 flags remain non-adjudicated until their individual textual context and real external evidence are compared.** There is no claim that the project identified 4,049 inaccuracies, examined every possible theological interpretation, proved supernatural beings existed, or disproved all religious beliefs.

### Reproduce the combined workflow

Run isolated [Gospel of BEAN CI](https://github.com/danieloculus0-bot/BEAN/actions/workflows/gospel-of-bean-evidence-lab.yml) on the experiment branch to reproduce the corpus index, five passes across all verse entries, and five recorded research sessions for all formal disputes. Review the archived JSON and SQLite evidence outputs. Merge is intentionally not authorized; the latest enhanced research session must pass GitHub CI independently.
