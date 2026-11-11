# BEAN gene-locus research workbench | 2026-11-10

**Implementation:** `bean/bioinformatics/genomics.py`; tests in `tests/test_genomics.py`.
**Status:** independently exercised with synthetic data and a mocked NCBI fetch; **live NCBI fetch, full genome comparison, experimental expression validation, and BEAN Core inference integration not verified**. This code lives in BEAN's source tree. The separate ChatGPT-hosted BEAN memory adapter and Render/Perplexity MCP endpoint do not execute it.

## Execute

Run a transparent self-test with synthetic DNA, a hypothetical base change, annotated exon joining, fictitious expression measurements, and an append-only provenance record:

```bash
python -m unittest discover -s tests -p 'test_genomics.py' -v
python -m bean.bioinformatics.genomics --demo --out demo.json --ledger experiments/genomics.jsonl
```

When a network-enabled local Core Python environment can reach NCBI EFetch, request two versioned public **Arabidopsis thaliana FLC (AT5G10140)** locus accessions for Wassilewskija and Bs-1 ecotypes:

```bash
python -m bean.bioinformatics.genomics --accessions AY769356.1 AY769357.1 --out flc_comparison.json --ledger experiments/genomics.jsonl
```

Alternatively, supply a local FASTA file (`--fasta samples.fasta`). With one or two sequences, optionally add `--variant 7:T` to compute a purely virtual codon consequence on the *first* sequence, `--exons 1-6,11-19` for **user-annotated plus-strand exons** of that sequence, and `--expression-json expression.json` for measured replicates, in the format `{"control":[10,12,11],"treatment":[4,5,6],"units":"TPM"}`. These coordinates and measurement values are illustrative only; **do not reuse them as FLC annotations or FLC observations**.

## Computational scope and data quality

| Capability | Current mechanism | Evidence boundary |
|---|---|---|
| Read DNA and identify genes | Validate IUPAC A/C/G/T/N FASTA, compute length/GC/hash, optional curated ID mapping for two verified FLC NCBI accessions | Raw sequence alone **cannot** identify a gene; unknown genes remain `Unknown` until reference alignment/annotation |
| Compare genomes | Gene-sized exact-block comparison and variant inventory with conserved segments, bounded to 10k nt | **Not whole-genome comparison**, not a phylogenetically defensible alignment; repetitive DNA may align ambiguously |
| Model modifications | One hypothetical coding-strand base substitution and genetic-code consequence | Not CRISPR design, edit efficiency, splicing/off-target or phenotype prediction |
| Study expression and splicing | Descriptive fold change from **supplied** expression measurements; join **supplied** exon coordinates | No unsupported inference of natural isoforms, causal transcription regulation, significance or RNA-seq measurements |
| Research | Source-linked accession information and literature below; BEAN's connected evidence tools can triage host-supplied statements | Heuristic audit cannot authenticate sources or certify conclusions |
| Track experiments | Local append-only JSONL with SHA-256 content digests, statuses, provenance and duplicate suppression | No automatic synchronization with ChatGPT BEAN notes, Jetson SQLite, or Perplexity MCP |

## Evidence-based plant research question

**Question:** How does FLC vary across natural Arabidopsis ecotypes, and what does that variation imply about flowering and transcript processing?

**Established:** NCBI records `AY769356.1` and `AY769357.1` identify FLC/AT5G10140 in two *A. thaliana* ecotypes. FLC is a MADS-box transcription factor and established floral repressor. Published work describes FLC expression repression through vernalization, alternative RNA splicing at the FLC/COOLAIR locus, and diverse FLC orthologs and promoters across related species.

**Hypothesis, not result:** Ecotype sequence differences might correlate with flowering regulation. Which bases differ, whether natural splice isoforms differ, expression changes, and any phenotype remain **Unknown** until raw sequences and independently sourced transcript/phenotype observations are analyzed. The tool does not manufacture those missing values.

### Public source references

- NCBI FLC gene, ID 830878: https://www.ncbi.nlm.nih.gov/gene/830878
- NCBI FLC sequence, Wassilewskija: https://www.ncbi.nlm.nih.gov/nuccore/AY769356.1
- NCBI FLC sequence, Bs-1: https://www.ncbi.nlm.nih.gov/nuccore/AY769357.1
- PlantTFDB protein and expression annotation: https://planttfdb.gao-lab.org/tf.php?did=AT5G10140.1&sp=Ath
- Wu, Jia & Hu (2026), *Environmental control of flowering through alternative splicing of FLC and COOLAIR*, DOI:10.1016/j.bbrc.2026.153877
- Evolutionary conservation of FLC cold-induced antisense transcripts (2014): https://pmc.ncbi.nlm.nih.gov/articles/PMC4109010/

### BEAN connector evidence round

The hosted BEAN claim-audit heuristic returned `approved` on a carefully sourced claim, **without independent truth verification**. The comparison heuristic returned `insufficient` and a difference flag because separately sourced statements had different wording; this is *not* a demonstrated scientific contradiction. No local Python Core event, neural training update, or biological measurement occurred in that evidence round.

### Experiment receipt and limits

The synthetic case is a **proof of code execution**, not a wet-lab or natural sequence observation. Preserve the JSONL record even when later real data contradict an initial hypothesis. Add new receipts for failures and unanswered questions, not retroactive substitutions. The format is separate from native Core's SQLite/SHA memory.
