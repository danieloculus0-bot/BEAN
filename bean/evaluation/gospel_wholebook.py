"""Lab 019-C: exhaustive mechanical verse screening, not exhaustive fact adjudication.

Every available verse entry is inspected in five distinct screening passes.
Rules nominate claims for further research; they never certify supernatural
truth, historical impossibility, a contradiction, or a person's faith.
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path

from bean.evaluation.gospel_lab import (
    Corpus, CorpusError, load_corpus, _load_json, read_reference_only_catalog,
    age_at_accession,
)

SCHEMA = "bean.gospel_wholebook_screen.v1"

# Text matching intentionally broad, with false positives expected.
# Historical evidence may only enter at case-level peer-reviewed adjudication.
RULES = (
    ("numeric_age_lifespan", "chronology", r"\b(?:yeeres?|yeares?|years?)\s+old\b|\b(?:hundred|hundreth)\s+and\s+\w+\s+yeeres\b",
     "Age or lifespan claims; verify named subject and dates"),
    ("numeric_count_dimensions", "quantity", r"\b(?:cubits?|thousand|hundred|hundreth|million|myriads?|talents?|shekels?)\b",
     "Numerical claim that may need historical or arithmetic constraints"),
    ("universal_scope", "geography", r"\b(?:all\s+the\s+earth|whole\s+earth|whole\s+world|all\s+the\s+world|every\s+country|every\s+nation|vnder\s+the\s+whole\s+heauen|under\s+the\s+whole\s+heaven)\b",
     "Claims of universality, possibly idiomatic or regional"),
    ("days_creation", "natural_history", r"\b(?:first|second|third|fourth|fift|fifth|sixth|seuenth|seventh)\s+day\b|\b(?:euening|evening)\s+and\s+the\s+morning\b",
     "Creation or calendar order; not automatically literal 24-hour duration"),
    ("creation_origin", "natural_history", r"\b(?:creat(?:ed|ion)|formed?\s+man|made\s+man|made\s+the\s+earth|made\s+the\s+heauen|maker\s+of\s+heauen)\b",
     "Origin claim; specify the proposed physical mechanism"),
    ("flood_water", "geology", r"\b(?:arke|ark|flood|deluge|fountaines?\s+of\s+the\s+great\s+deepe|wind(?:owes|ows)\s+of\s+heauen)\b",
     "Flood or Ark description; distinguish local versus global hypotheses"),
    ("genealogy_parentage", "ancestry", r"\b(?:begat|begate|begotten|sonne\s+of|daughter\s+of|wife\s+of|father\s+of|mother\s+of)\b",
     "Named ancestry assertion; chronology and identity must be established"),
    ("miraculous_birth", "biology", r"\b(?:virgin|conceiued|conceived|barren|wombe|womb|quickened)\b",
     "Reproductive or birth claim; classify as ordinary or supernatural"),
    ("biological_miracle", "biology", r"\b(?:raised\s+from\s+the\s+dead|rise\s+from\s+the\s+dead|resurrect|reuiued|revived|healed\s+of|lep[er|ros]|blinde?\s+receiued|blind\s+receive)\b",
     "Biological claims, including miracles not testable retrospectively"),
    ("talking_nonhuman", "biology", r"\b(?:serpent\s+said|asse\s+said|donkey\s+said|beast\s+spake|beast\s+spoke)\b",
     "Non-human speech; literal or figurative interpretive question"),
    ("astronomical_sun", "physics", r"\b(?:sunne?\s+stood\s+still|sun\s+stood\s+still|moon\s+stood|starres?\s+fell|sunne?\s+was\s+darkened)\b",
     "Astronomical event proposal; modern mechanics versus literary language"),
    ("angel_spirit_satan", "supernatural", r"\b(?:satan|lucifer|serpent|deuill|devil|dragon|angell?|angel|demon|evil\s+spirit|euil\s+spirit)\b",
     "Supernatural or symbolic figure; original context and later identity differ"),
    ("supernatural_act", "supernatural", r"\b(?:miracle|walked\s+on\s+the\s+sea|walked\s+on\s+the\s+water|waters?\s+were\s+diuided|waters?\s+were\s+divided|turn(?:ed)?\s+to\s+blood)\b",
     "Natural-law conflict needs a precisely specified testable claim"),
    ("legal_ethics", "social_history", r"\b(?:bondmen|bondwoman|slaues?|slaves?|servants?|stoned\s+with\s+stones|put\s+to\s+death|sell\s+your|buy\s+a\s+servant)\b",
     "Claims concerning slavery, punishments and social practice; investigate actual legal context"),
    ("war_violence", "social_history", r"\b(?:slew\s+all|slay\s+all|utterly\s+destroy|destroy\s+all|men\s+and\s+women\s+and\s+children|little\s+ones|spared\s+none)\b",
     "War and command narrative requires source, genre and scope classification"),
)
PASS_RULES = (
    ("01_chronology_and_counts", {"numeric_age_lifespan", "numeric_count_dimensions",
                                 "genealogy_parentage", "days_creation"}),
    ("02_origins_physical_world", {"universal_scope", "creation_origin", "flood_water",
                                 "astronomical_sun"}),
    ("03_biology_and_ecology", {"miraculous_birth", "biological_miracle", "talking_nonhuman"}),
    ("04_agents_ethics_miracles", {"angel_spirit_satan", "supernatural_act",
                                 "legal_ethics", "war_violence"}),
    ("05_cross_check_all_flags", {row[0] for row in RULES}),
)
COMPILED = {name: re.compile(regex, re.I) for name, _, regex, _ in RULES}



def _named_accession_age(text: str) -> tuple[str, int] | None:
    """Discover similar dated accession texts; do not infer same historic king."""
    if not re.search(r"\bbegan\s+to\s+reign[e]?\b", text, flags=re.I):
        return None
    age = age_at_accession(text)
    if age is None:
        return None
    # Early-modern spelling, and both "Name was X years old" / "X old was Name".
    patterns = (
        r"\b(?:yeeres?|yeares?|years?)\s+old\s+was\s+([A-Z][a-z]{2,})\b",
        r"\b([A-Z][a-z]{2,})\s+was\s+[^.!?;:]{1,55}?\b(?:yeeres?|yeares?|years?)\s+old\b",
    )
    for pattern in patterns:
        match = re.search(pattern, text)
        if match and match[1].lower() not in {"and", "king", "lord", "god", "also"}:
            return match[1].lower(), age
    return None


def mine_cross_book_accession_age_pairs(corpus: Corpus) -> list[dict]:
    """Unseeded, cross-book comparison of *possible* same-king dates."""
    named: dict[str, list[tuple[str, int]]] = collections.defaultdict(list)
    for ref, text in corpus.verses.items():
        name_age = _named_accession_age(text)
        if name_age is not None:
            name, age = name_age
            named[name].append((ref, age))
    links = []
    for name, rows in sorted(named.items()):
        for i, (ref1, age1) in enumerate(rows):
            for ref2, age2 in rows[i + 1:]:
                book1, book2 = (ref.rsplit(" ", 1)[0] for ref in (ref1, ref2))
                if book1 == book2 or age1 == age2:
                    continue
                links.append({
                    "candidate_name": name, "reference_a": ref1, "age_a": age1,
                    "reference_b": ref2, "age_b": age2,
                    "hypothesis": "different accession ages if this is the same ruler and event",
                    "same_historical_person_verified": False,
                    "same_event_verified": False,
                    "verdict": "review_required",
                    "proven_inaccuracy": False,
                })
    return sorted(links, key=lambda row: (
        row["candidate_name"], row["reference_a"], row["reference_b"]
    ))


def screen_corpus(corpus: Corpus, *, comparison_case_refs: dict[str, list[str]] | None = None,
                  gnostic_reference_catalog: Path | None = None) -> dict:
    """Pass every verse through every pass rule; retain each rule match."""
    if not corpus.verses:
        raise CorpusError("whole-book screening requires an indexed corpus")
    reference_only = (read_reference_only_catalog(gnostic_reference_catalog)
                      if gnostic_reference_catalog is not None else None)
    if comparison_case_refs is not None:
        for refs in comparison_case_refs.values():
            if not isinstance(refs, list) or any(ref not in corpus.verses for ref in refs):
                raise CorpusError("a proposed case lacks indexed scripture")
    labels = {name: {"category": category, "limitation": limitation}
              for name, category, _, limitation in RULES}
    by_verse: dict[str, set[str]] = collections.defaultdict(set)
    passes: list[dict] = []
    for pname, names in PASS_RULES:
        hits = 0
        matches = collections.Counter()
        for ref, text in corpus.verses.items():
            for name in sorted(names):
                if COMPILED[name].search(text):
                    hits += 1
                    matches[name] += 1
                    by_verse[ref].add(name)
        passes.append({
            "name": pname,
            "verses_examined": len(corpus.verses),
            "raw_rule_hits": hits,
            "rule_frequencies": dict(sorted(matches.items())),
            "historical_claims_verified": 0,
            "independent_refutation_performed": False,
        })
    # Every flagged verse is retained for human review, rather than clipping a
    # priority sample and silently calling the remainder reviewed.
    queue = []
    books = collections.Counter()
    for ref in corpus.verses:
        if ref not in by_verse:
            continue
        rule_names = sorted(by_verse[ref])
        book = ref.rsplit(" ", 1)[0]
        books[book] += 1
        queue.append({
            "reference": ref,
            "book": book,
            "categories": rule_names,
            "text_sha256": hashlib.sha256(corpus.verses[ref].encode()).hexdigest(),
            "review": "not_individually_adjudicated",
            "hypothesis_status": "candidate_only",
        })
    age_parallel_candidates = mine_cross_book_accession_age_pairs(corpus)
    indexed_refs = comparison_case_refs or {}
    crosslinks = [
        {
            "case_id": case_id, "references": refs,
            "rules_detected_at_references": {
                ref: sorted(by_verse.get(ref, set())) for ref in refs},
            "subject_event_identity_independently_proven": False,
            "status": "requires_conditional_model",
        }
        for case_id, refs in sorted(indexed_refs.items())
    ]
    return {
        "schema": SCHEMA, "source_corpus_sha256": corpus.sha256,
        "books_examined": len(corpus.books),
        "chapters_known": corpus.chapter_count,
        "verse_entries_examined_each_pass": len(corpus.verses),
        "passes": passes,
        "verses_flagged": len(by_verse),
        "verses_not_flagged": len(corpus.verses) - len(by_verse),
        "rule_hits_unique_verse_pairs": sum(len(v) for v in by_verse.values()),
        "review_queue_entries": len(queue),
        "flagged_verses_by_book": dict(sorted(books.items())),
        "all_screened_candidate_entries": queue,
        "formal_dispute_links": crosslinks,
        "automatically_mined_age_parallels": age_parallel_candidates,
        "unseeded_age_parallel_candidates": len(age_parallel_candidates),
        "gnostic_reference_catalog_loaded": reference_only is not None,
        "gnostic_sources_used_to_confirm_claims": 0,
        "all_possible_inaccuracies_discovered": False,
        "verse_semantics_fully_understood": False,
        "every_historical_claim_adjudicated": False,
        "limitations": (
            "100% coverage of indexed verse entries by fixed keyword rules, "
            "not an exhaustive logical contradiction or historical-accuracy audit. "
            "False positives and uncaptured claims are expected. No flagged item "
            "becomes historical proof until individually sourced, adversarially "
            "tested, and independently checked."
        ),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Whole KJV fixed-rule screening lab")
    parser.add_argument("--corpus", type=Path, required=True)
    parser.add_argument("--corrections", type=Path, required=True)
    parser.add_argument("--cases", type=Path, required=True)
    parser.add_argument("--gnostic-reference-catalog", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args(argv)
    corpus = load_corpus(args.corpus, corrections_path=args.corrections)
    cases = _load_json(args.cases)["cases"]
    refs = {row["id"]: row["references"] for row in cases}
    result = screen_corpus(corpus, comparison_case_refs=refs,
                           gnostic_reference_catalog=args.gnostic_reference_catalog)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n",
                           encoding="utf-8")
    print(json.dumps({k: result[k] for k in (
        "books_examined", "chapters_known", "verse_entries_examined_each_pass",
        "verses_flagged", "verses_not_flagged", "rule_hits_unique_verse_pairs",
        "review_queue_entries")}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
