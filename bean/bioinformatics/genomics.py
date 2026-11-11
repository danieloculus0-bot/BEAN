"""Small, offline-first and evidence-aware BEAN genomics workbench.

Gene-locus analysis, not whole-genome alignment, gene discovery, RNA-seq
inference, off-target prediction, wet-lab planning, or phenotype validation.
All changes are virtual; all measured expression must be supplied as data.
Use accession version IDs and retain provenance in experiment receipts.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from difflib import SequenceMatcher
import hashlib
import json
from pathlib import Path
import re
from urllib.parse import urlencode
from urllib.request import Request, urlopen

DNA = set("ACGTN")
# Curated accession associations, supported by the indicated public NCBI records.
# Other references remain Unknown instead of being guessed from sequence text.
KNOWN_ACCESSIONS = {
    "AY769356.1": {"gene": "FLC", "locus": "AT5G10140", "organism": "Arabidopsis thaliana",
                   "ecotype": "Wassilewskija", "source": "https://www.ncbi.nlm.nih.gov/nuccore/AY769356.1"},
    "AY769357.1": {"gene": "FLC", "locus": "AT5G10140", "organism": "Arabidopsis thaliana",
                   "ecotype": "Bs-1", "source": "https://www.ncbi.nlm.nih.gov/nuccore/AY769357.1"},
}

# Nucleotide code -> amino acid, standard nuclear genetic code.
_TABLE = dict(zip(
    ["TTT", "TTC", "TTA", "TTG", "TCT", "TCC", "TCA", "TCG", "TAT", "TAC", "TAA", "TAG", "TGT", "TGC", "TGA", "TGG",
     "CTT", "CTC", "CTA", "CTG", "CCT", "CCC", "CCA", "CCG", "CAT", "CAC", "CAA", "CAG", "CGT", "CGC", "CGA", "CGG",
     "ATT", "ATC", "ATA", "ATG", "ACT", "ACC", "ACA", "ACG", "AAT", "AAC", "AAA", "AAG", "AGT", "AGC", "AGA", "AGG",
     "GTT", "GTC", "GTA", "GTG", "GCT", "GCC", "GCA", "GCG", "GAT", "GAC", "GAA", "GAG", "GGT", "GGC", "GGA", "GGG"],
    "FFLLSSSSYY**CC*WLLLLPPPPHHQQRRRRIIIMTTTTNNKKSSRRVVVVAAAADDEEGGGG"
))


def clean_dna(seq: str) -> str:
    seq = re.sub(r"\s+", "", seq).upper()
    if not seq or any(ch not in DNA for ch in seq):
        raise ValueError("Expected a nonempty DNA sequence containing only A, C, G, T or N")
    return seq


def parse_fasta(text: str) -> dict[str, dict]:
    """Return accession-keyed sequences; headers are not trusted gene identities."""
    result: dict[str, dict] = {}
    key, header, chunks = None, None, []
    def save():
        if key is not None:
            if key in result:
                raise ValueError(f"Duplicate FASTA identifier: {key}")
            seq = clean_dna("".join(chunks))
            result[key] = {"header": header, "dna": seq, "sha256": hashlib.sha256(seq.encode()).hexdigest()}
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith(">"):
            save()
            header = line[1:].strip()
            key = header.split(maxsplit=1)[0] if header else None
            if not key:
                raise ValueError("FASTA record has no identifier")
            chunks = []
        else:
            if key is None:
                raise ValueError("FASTA sequence without header")
            chunks.append(line)
    save()
    if not result:
        raise ValueError("No FASTA records supplied")
    return result


def fetch_ncbi(accessions: list[str], *, opener=urlopen) -> dict[str, dict]:
    """Fetch accession-version FASTA from NCBI EFetch; no sequence is inferred."""
    if not (1 <= len(accessions) <= 6) or any(not re.fullmatch(r"[A-Za-z]{1,4}_?\d+\.\d+", a) for a in accessions):
        raise ValueError("Supply 1-6 explicit accession.version identifiers")
    url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?" + urlencode({
        "db": "nuccore", "id": ",".join(accessions), "rettype": "fasta", "retmode": "text"})
    req = Request(url, headers={"User-Agent": "BEAN-Genomics/0.1 (educational research; github.com/danieloculus0-bot/BEAN)"})
    with opener(req, timeout=20) as response:
        data = response.read(1_000_001)
    if len(data) > 1_000_000:
        raise ValueError("Reference too large for bounded gene-level workbench")
    records = parse_fasta(data.decode("utf-8"))
    if set(records) != set(accessions):
        raise ValueError("Returned accession identifiers did not match request")
    for key in records:
        records[key]["source"] = f"https://www.ncbi.nlm.nih.gov/nuccore/{key}"
    return records


def describe(seq: str) -> dict:
    s = clean_dna(seq)
    return {"length_nt": len(s), "gc_fraction": round((s.count("G") + s.count("C")) / len(s), 6),
            "ambiguous_n": s.count("N"), "starts_with_ATG": s.startswith("ATG"),
            "terminal_stop": s[-3:] in {"TAA", "TGA", "TAG"},
            "length_multiple_of_three": len(s) % 3 == 0,
            "gene_identity": "Unknown without accession annotation or reference alignment"}


def translate(seq: str) -> str:
    seq = clean_dna(seq)
    return "".join(_TABLE.get(seq[i:i + 3], "X") for i in range(0, len(seq) - 2, 3))


def compare(a: str, b: str) -> dict:
    """Small-locus exact matching/difference inventory; NOT a phylogenetic aligner."""
    a, b = clean_dna(a), clean_dna(b)
    if max(len(a), len(b)) > 10_000:
        raise ValueError("Compare only gene-sized sequences (<=10,000 nt); use validated genome aligners for larger data")
    matcher = SequenceMatcher(a=a, b=b, autojunk=False)
    changes = []
    conserved = []
    for tag, x1, x2, y1, y2 in matcher.get_opcodes():
        if tag == "equal":
            if x2 - x1 >= 3:
                conserved.append({"a_start_1based": x1 + 1, "b_start_1based": y1 + 1, "length_nt": x2 - x1})
        else:
            changes.append({"kind": tag, "a_range_1based_half_open": [x1 + 1, x2 + 1],
                            "b_range_1based_half_open": [y1 + 1, y2 + 1],
                            "a": a[x1:x2], "b": b[y1:y2]})
    return {"a_length_nt": len(a), "b_length_nt": len(b), "identical": a == b,
            "differences": changes, "conserved_blocks_min3": conserved,
            "method": "difflib exact block matching (heuristic, non-evolutionary)",
            "alignment_quality": "Unknown; repetitive sequences may have ambiguous match positions"}


def virtual_substitution(seq: str, *, position: int, alternate: str) -> dict:
    """Model one coding-strand base substitution only; no phenotype prediction."""
    seq = clean_dna(seq)
    alternate = clean_dna(alternate)
    if len(alternate) != 1 or alternate == "N" or not 1 <= position <= len(seq):
        raise ValueError("Specify an in-range one-base alternative (A/C/G/T)")
    old = seq[position - 1]
    if old == alternate or old == "N":
        raise ValueError("Reference must be a known base and alternate must differ")
    new = seq[:position - 1] + alternate + seq[position:]
    i = (position - 1) // 3
    codon = seq[i * 3:i * 3 + 3]
    mutated = new[i * 3:i * 3 + 3]
    before, after = translate(codon), translate(mutated)
    effect = ("unresolved_partial_codon" if len(codon) != 3 else
              "start_loss" if i == 0 and codon == "ATG" and mutated != "ATG" else
              "stop_gain" if after == "*" and before != "*" else
              "stop_loss" if before == "*" and after != "*" else
              "synonymous" if before == after else "amino_acid_change")
    return {"position_1based": position, "reference": old, "alternate": alternate,
            "codon_before": codon, "codon_after": mutated, "amino_acid_before": before,
            "amino_acid_after": after, "coding_effect": effect, "mutated_sequence_sha256": hashlib.sha256(new.encode()).hexdigest(),
            "phenotype": "Unknown", "splicing_effect": "Unknown", "off_target_effect": "Not assessed",
            "status": "in_silico_hypothesis_only"}


def splice(seq: str, exons: list[tuple[int, int]]) -> dict:
    """Join annotated plus-strand exon ranges (1-based inclusive). NOT splice-site prediction."""
    seq = clean_dna(seq)
    if not exons:
        raise ValueError("Provide annotated exon coordinates")
    joined = []
    last = 0
    for start, end in exons:
        if not (1 <= start <= end <= len(seq)) or start <= last:
            raise ValueError("Exons must be ordered, disjoint and lie inside the plus-strand sequence")
        joined.append(seq[start - 1:end])
        last = end
    cdna = "".join(joined)
    return {"exons_1based_inclusive": exons, "spliced_dna": cdna, "rna": cdna.replace("T", "U"),
            "translated_if_CDS": translate(cdna), "isoform": "candidate from supplied exon coordinates",
            "observed_rna_isoform": "Unknown (requires transcript evidence)"}


def expression(control: list[float], treatment: list[float], *, units: str) -> dict:
    """Descriptive observed measurement comparison, not RNA-seq statistics."""
    import math
    if not control or not treatment or units not in {"TPM", "FPKM", "normalized_counts", "arbitrary_units"}:
        raise ValueError("Supply two nonempty replicate groups and explicit measurement units")
    if any(type(x) not in (int, float) or not math.isfinite(x) or x < 0 for x in control + treatment):
        raise ValueError("Expression values must be finite nonnegative measurements")
    c, t = sum(control) / len(control), sum(treatment) / len(treatment)
    ratio = None if c == 0 else t / c
    return {"control_mean": c, "treatment_mean": t, "control_n": len(control), "treatment_n": len(treatment),
            "units": units, "fold_change": ratio, "direction": "Unknown" if ratio is None else
            ("higher" if ratio > 1 else "lower" if ratio < 1 else "unchanged"),
            "statistical_significance": "Not assessed", "causal_activation_or_suppression": "Unknown",
            "measurement_status": "caller_supplied_not_independently_verified"}


def record_experiment(path: Path, case: dict) -> dict:
    """Append an immutable-by-convention receipt with duplicate evidence suppression."""
    required = {"experiment_id", "question", "prediction", "observation", "status", "source_refs"}
    if not required.issubset(case) or not case["experiment_id"] or not isinstance(case["source_refs"], list):
        raise ValueError(f"Experiment requires {sorted(required)}")
    if case["status"] not in {"simulated", "observed", "failed", "unknown"}:
        raise ValueError("Use simulated, observed, failed or unknown status")
    payload = json.dumps(case, sort_keys=True, ensure_ascii=True, separators=(",", ":"))
    digest = hashlib.sha256(payload.encode()).hexdigest()
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            if json.loads(line).get("sha256") == digest:
                return {"sha256": digest, "deduplicated": True, "path": str(path)}
    row = {"schema": "bean.genomics.experiment.v1", "sha256": digest,
           "recorded_utc": datetime.now(timezone.utc).isoformat(), "case": case}
    with path.open("a", encoding="utf-8") as out:
        out.write(json.dumps(row, sort_keys=True) + "\n")
    return {"sha256": digest, "deduplicated": False, "path": str(path)}


def demo() -> dict:
    """Explicitly synthetic toy gene, not an observed organism or genome."""
    original = "ATGAAACCCGGGTAA"
    alternate = "ATGAAATCCGGGTAA"
    return {"schema": "bean.genomics.demo.v1", "data_class": "synthetic",
            "reference": describe(original), "comparison": compare(original, alternate),
            "virtual_change": virtual_substitution(original, position=7, alternate="T"),
            "splice_model": splice("ATGAAAGTACCCCGGGTAA", [(1, 6), (11, 19)]),
            "expression_example": expression([10., 12., 11.], [4., 5., 6.], units="TPM"),
            "limitations": ["No gene ID inferred from sequence", "No biological splicing prediction", "No real expression measured"]}


def main() -> None:
    parser = argparse.ArgumentParser(description="BEAN evidence-aware gene locus workbench")
    parser.add_argument("--demo", action="store_true", help="Run transparent synthetic demonstration")
    parser.add_argument("--fasta", type=Path, help="FASTA file containing one or two gene loci")
    parser.add_argument("--accessions", nargs="+", help="Fetch 1-6 versioned NCBI accessions, online only")
    parser.add_argument("--out", type=Path, help="Optional result JSON path")
    parser.add_argument("--variant", help="Virtual base substitution on first sequence, e.g. 7:T (1-based)")
    parser.add_argument("--exons", help="Known plus-strand exon ranges on first sequence, e.g. 1-6,11-19")
    parser.add_argument("--expression-json", type=Path, help="JSON with measured control/treatment arrays and units")
    parser.add_argument("--ledger", type=Path, help="Optional append-only experiment JSONL path")
    a = parser.parse_args()
    if a.demo:
        if a.fasta or a.accessions or a.variant or a.exons or a.expression_json:
            parser.error("--demo cannot be combined with sequence or measurement options")
        result = demo()
    elif bool(a.fasta) == bool(a.accessions):
        parser.error("Choose exactly one of --demo, --fasta, or --accessions")
    else:
        records = parse_fasta(a.fasta.read_text(encoding="utf-8")) if a.fasta else fetch_ncbi(a.accessions)
        result = {"schema": "bean.genomics.sequence_analysis.v1", "data_class": "reference_sequence",
                  "records": {k: {"header": v["header"], "sha256": v["sha256"],
                                     "source": v.get("source", "caller_supplied_fasta"),
                                     "description": describe(v["dna"]),
                                     "curated_identity": KNOWN_ACCESSIONS.get(k, "Unknown")} for k, v in records.items()},
                  "comparison": None, "gene_identity": "Accession annotation where curated, otherwise Unknown"}
        if len(records) == 2:
            left, right = list(records.values())
            result["comparison"] = compare(left["dna"], right["dna"])
        first = next(iter(records.values()))["dna"]
        if a.variant:
            m = re.fullmatch(r"([1-9]\d*):([ACGT])", a.variant.upper())
            if not m:
                parser.error("--variant must be 1-based position:base, such as 7:T")
            result["virtual_change"] = virtual_substitution(first, position=int(m[1]), alternate=m[2])
        if a.exons:
            coords = []
            for token in a.exons.split(","):
                m = re.fullmatch(r"([1-9]\d*)-([1-9]\d*)", token)
                if not m:
                    parser.error("--exons must be comma-separated 1-based inclusive ranges")
                coords.append((int(m[1]), int(m[2])))
            result["splice_model"] = splice(first, coords)
        if a.expression_json:
            measured = json.loads(a.expression_json.read_text(encoding="utf-8"))
            result["expression_observations"] = expression(measured["control"], measured["treatment"], units=measured["units"])
    if a.ledger:
        case = {"experiment_id": "bean-genomics-" + hashlib.sha256(json.dumps(result, sort_keys=True).encode()).hexdigest()[:16],
                "question": "Can the workbench analyze the provided gene-sized sequences?",
                "prediction": "Deterministic parsing and descriptive analysis; no phenotype prediction",
                "observation": result, "status": "simulated" if a.demo else "observed",
                "source_refs": [] if a.demo else ([f"https://www.ncbi.nlm.nih.gov/nuccore/{x}" for x in a.accessions] if a.accessions else [str(a.fasta)])}
        result["ledger_receipt"] = record_experiment(a.ledger, case)
    rendered = json.dumps(result, indent=2, sort_keys=True)
    if a.out:
        a.out.parent.mkdir(parents=True, exist_ok=True)
        a.out.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)


if __name__ == "__main__":
    main()
