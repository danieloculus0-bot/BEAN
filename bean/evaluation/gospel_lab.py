"""Gospel of BEAN: bounded, read-only 80-book 1611 KJV textual evidence audit.

The source corpus is a pinned third-party transcription, not a scholarly
collation. External research links are not automatically authenticated.
"""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any

SOURCE_REPOSITORY = "aruljohn/Bible-kjv-1611"
SOURCE_COMMIT = "8ef066868ad1b7204d7be48658ea3bd1783d409b"
SOURCE_URL = f"https://github.com/{SOURCE_REPOSITORY}/tree/{SOURCE_COMMIT}"
EXPECTED_BOOKS = tuple("""Genesis|Exodus|Leviticus|Numbers|Deuteronomy|Joshua|Judges|Ruth|1 Samuel|2 Samuel|1 Kings|2 Kings|1 Chronicles|2 Chronicles|Ezra|Nehemiah|Esther|Job|Psalms|Proverbs|Ecclesiastes|Song of Solomon|Isaiah|Jeremiah|Lamentations|Ezekiel|Daniel|Hosea|Joel|Amos|Obadiah|Jonah|Micah|Nahum|Habakkuk|Zephaniah|Haggai|Zechariah|Malachi|Matthew|Mark|Luke|John|Acts|Romans|1 Corinthians|2 Corinthians|Galatians|Ephesians|Philippians|Colossians|1 Thessalonians|2 Thessalonians|1 Timothy|2 Timothy|Titus|Philemon|Hebrews|James|1 Peter|2 Peter|1 John|2 John|3 John|Jude|Revelation|1 Esdras|2 Esdras|Tobit|Judith|Wisdom of Solomon|Ecclesiasticus|Baruch|Letter of Jeremiah|Prayer of Azariah|Susanna|Bel and the Dragon|Prayer of Manasseh|1 Maccabees|2 Maccabees""".split("|"))
SCRIPTURE_REF = re.compile(r"^(.*?)\s+(\d+):(\d+)$")
YEAR_WORDS = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
              "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
              "twenty": 20, "twentie": 20, "thirty": 30, "thirtie": 30,
              "forty": 40, "fortie": 40, "fourtie": 40, "and": 0}
AGE_PATTERN = re.compile(r"(?P<age>(?:[A-Za-z]+\s+){1,5})y[e]?e?res\s+old\b", re.I)


class CorpusError(ValueError):
    """Incomplete, damaged, or untraceable source data."""


@dataclass(frozen=True)
class Corpus:
    verses: dict[str, str]
    books: tuple[str, ...]
    chapter_count: int
    sha256: str

    def verse(self, reference: str) -> str:
        if reference not in self.verses:
            raise CorpusError(f"missing verse {reference}")
        return self.verses[reference]


def _load_json(path: Path) -> Any:
    if not path.is_file():
        raise CorpusError(f"missing corpus file {path.name}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (UnicodeError, ValueError) as exc:
        raise CorpusError(f"malformed JSON {path.name}") from exc


def load_corpus(root: Path) -> Corpus:
    """Do not claim full-text ingestion unless 80 books and every chapter load."""
    names = _load_json(root / "Books.json")
    chapter_manifest = _load_json(root / "Books_chapter_count.json")
    if not isinstance(names, list) or tuple(names) != EXPECTED_BOOKS:
        raise CorpusError("expected exactly 80 named books including 14 Apocrypha books")
    if (not isinstance(chapter_manifest, list)
            or len(chapter_manifest) != 80
            or any(not isinstance(row, list) or len(row) != 2 for row in chapter_manifest)
            or [row[0] for row in chapter_manifest] != names
            or any(type(row[1]) is not int or row[1] < 1 for row in chapter_manifest)):
        raise CorpusError("invalid chapter manifest")
    expected_files = {"Books.json", "Books_chapter_count.json"} | {f"{name}.json" for name in names}
    actual_files = {p.name for p in root.glob("*.json")}
    if expected_files != actual_files:
        raise CorpusError(f"missing or unexpected book JSON files: {sorted(expected_files ^ actual_files)[:5]}")
    digest = hashlib.sha256()
    for name in sorted(expected_files):
        raw = (root / name).read_bytes()
        digest.update(name.encode() + b"\0" + len(raw).to_bytes(8, "big") + raw)
    verses = {}
    chapters = 0
    for name, (_, expected_chapters) in zip(names, chapter_manifest):
        book = _load_json(root / f"{name}.json")
        if (not isinstance(book, dict) or book.get("book") != name
                or str(book.get("chapter-count")) != str(expected_chapters)
                or not isinstance(book.get("chapters"), list)
                or len(book["chapters"]) != expected_chapters):
            raise CorpusError(f"invalid book {name}")
        for chapter_number, chapter in enumerate(book["chapters"], 1):
            if not isinstance(chapter, dict) or chapter.get("chapter") != chapter_number:
                raise CorpusError(f"nonsequential chapter in {name} {chapter_number}")
            source_verses = chapter.get("verses")
            if not isinstance(source_verses, list) or not source_verses:
                raise CorpusError(f"empty chapter {name} {chapter_number}")
            for verse_number, row in enumerate(source_verses, 1):
                if (not isinstance(row, dict) or row.get("verse") != verse_number
                        or not isinstance(row.get("text"), str)
                        or not row["text"].strip()):
                    raise CorpusError(f"missing/bad verse {name} {chapter_number}:{verse_number}")
                verses[f"{name} {chapter_number}:{verse_number}"] = html.unescape(row["text"]).strip()
            chapters += 1
    if len(verses) < 30000 or chapters != 1355:
        raise CorpusError("corpus too small for an 80-book edition")
    return Corpus(verses, tuple(names), chapters, digest.hexdigest())


def age_at_accession(text: str) -> int | None:
    """Read only explicit ages, including 1611 spellings."""
    match = AGE_PATTERN.search(text)
    if not match:
        return None
    tokens = match.group("age").lower().strip().split()
    if not tokens or any(token not in YEAR_WORDS for token in tokens):
        return None
    result = sum(YEAR_WORDS[token] for token in tokens)
    return result if result > 0 else None


def audited_cases(corpus: Corpus, catalog: dict) -> list[dict]:
    cases = catalog.get("cases")
    if not isinstance(cases, list) or not cases:
        raise CorpusError("case catalog missing")
    if len({c.get("id") for c in cases if isinstance(c, dict)}) != len(cases):
        raise CorpusError("duplicate or malformed case ID")
    findings = []
    for case in cases:
        if not isinstance(case, dict) or not isinstance(case.get("id"), str):
            raise CorpusError("invalid case")
        refs = case.get("references")
        if not isinstance(refs, list) or len(refs) < 2 or len(set(refs)) != len(refs):
            raise CorpusError("each case requires at least two distinct references")
        if any(not isinstance(ref, str) or not SCRIPTURE_REF.fullmatch(ref) for ref in refs):
            raise CorpusError("invalid scripture reference")
        quotes = {ref: corpus.verse(ref) for ref in refs}
        kind = case.get("kind")
        values = {}
        if kind == "same_event_numeric":
            if len(refs) != 2:
                raise CorpusError("numeric comparison requires exactly two refs")
            values = {ref: age_at_accession(quotes[ref]) for ref in refs}
            if any(value is None for value in values.values()):
                verdict = "insufficient_parsing_evidence"
            else:
                verdict = ("direct_textual_disagreement" if len(set(values.values())) > 1
                           else "textually_consistent_on_checked_attribute")
        elif kind in {"narrative", "chronology", "manuscript", "scientific"}:
            verdict = "review_required"
        else:
            raise CorpusError("unsupported candidate kind")
        sources = case.get("external_sources", [])
        if (not isinstance(sources, list)
                or any(not isinstance(s, dict) or not isinstance(s.get("url"), str)
                       or not s["url"].startswith("https://")
                       or not isinstance(s.get("perspective"), str) for s in sources)):
            raise CorpusError("invalid externally supplied provenance")
        findings.append({
            "case_id": case["id"], "question": case.get("question"), "kind": kind,
            "verdict": verdict, "parsed_values": values,
            "scripture_evidence": quotes, "external_sources": sources,
            "counterinterpretation": case.get("counterinterpretation", ""),
            "caution": ("Conflict is in this edition's wording, not proof against all possible "
                        "manuscript reconstructions or theological interpretations."),
        })
    return findings


def build_read_only_index(corpus: Corpus, database: Path) -> None:
    """Put verses in a separate retrievable SQLite database, never BEAN's memory DB."""
    database.parent.mkdir(parents=True, exist_ok=True)
    if database.exists():
        raise CorpusError("will not overwrite an existing research index")
    connection = sqlite3.connect(database)
    try:
        connection.execute("CREATE TABLE verses (ref TEXT PRIMARY KEY, book TEXT NOT NULL, "
                           "chapter INTEGER NOT NULL, number INTEGER NOT NULL, text TEXT NOT NULL)")
        for ref, value in corpus.verses.items():
            match = SCRIPTURE_REF.fullmatch(ref)
            assert match is not None
            connection.execute("INSERT INTO verses VALUES (?, ?, ?, ?, ?)",
                               (ref, match[1], int(match[2]), int(match[3]), value))
        connection.execute("CREATE INDEX verses_book_chapter ON verses(book, chapter, number)")
        connection.commit()
    finally:
        connection.close()


def analyze(root: Path, catalog_file: Path, *, sqlite_db: Path | None = None) -> dict:
    corpus = load_corpus(root)
    catalog = _load_json(catalog_file)
    findings = audited_cases(corpus, catalog)
    if sqlite_db is not None:
        build_read_only_index(corpus, sqlite_db)
    return {
        "schema": "bean.gospel_of_bean.v1", "edition": "KJV 1611 spelling, 80-book upstream transcription",
        "source_repository": SOURCE_REPOSITORY, "source_commit_declared": SOURCE_COMMIT,
        "source_url": SOURCE_URL, "source_checkout_verified_independently": False,
        "corpus_sha256": corpus.sha256, "books": len(corpus.books),
        "chapters": corpus.chapter_count, "verses": len(corpus.verses),
        "contains_apocrypha": True, "textual_edition_collation_with_1611_facsimile": "not_performed",
        "external_references_fetched_and_verified_by_lab": False,
        "claims_about_metaphysical_truth": "not_assessed", "cases": findings,
        "scope": ("Source-indexed preliminary review only; case hypotheses are human-curated. "
                  "No broad autonomous natural-language contradiction discovery has been shown."),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="BEAN read-only complete KJV research lab")
    parser.add_argument("--corpus", type=Path, required=True)
    parser.add_argument("--cases", type=Path, default=Path(__file__).resolve().parents[2]
                        / "experiments/gospel_of_bean/cases.json")
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--index", type=Path, default=None)
    args = parser.parse_args(argv)
    result = analyze(args.corpus, args.cases, sqlite_db=args.index)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: result[key] for key in
                      ("schema", "corpus_sha256", "books", "chapters", "verses")}, indent=2))
    for item in result["cases"]:
        print(item["case_id"], item["verdict"], item["parsed_values"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
