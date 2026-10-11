"""Synthetic offline regression tests. Their success is not biblical/historical proof."""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from bean.evaluation.gospel_lab import (
    Corpus, CorpusError, EXPECTED_BOOKS, age_at_accession,
    analyze, audited_cases, build_read_only_index, load_corpus,
)


def small_corpus():
    verses = {
        "2 Kings 8:26": "Two and twentie yeeres old was Ahaziah when he began to reigne.",
        "2 Chronicles 22:2": "Fourtie and two yeeres old was Ahaziah, when he began to reigne.",
        "Matthew 27:5": "And he went and hanged himselfe.",
        "Acts 1:18": "And falling headlong, he burst asunder.",
    }
    return Corpus(verses, ("2 Kings", "2 Chronicles", "Matthew", "Acts"), 4, "synthetic")


def test_age_parser_1611_spelling():
    assert age_at_accession("Two and twentie yeeres old was Ahaziah") == 22
    assert age_at_accession("Fourtie and two yeeres old was Ahaziah") == 42
    assert age_at_accession("Thirtie and two yeeres old was he") == 32
    assert age_at_accession("Ahaziah reigned in Jerusalem one year") is None
    assert age_at_accession("Unknown fifty yeeres old") is None


def test_real_numeric_tension_in_synthetic_test_is_not_metaphysical_verdict():
    cases = {"cases": [{
        "id": "king_age", "question": "age?", "kind": "same_event_numeric",
        "references": ["2 Kings 8:26", "2 Chronicles 22:2"],
        "counterinterpretation": "manuscript difference",
    }]}
    result = audited_cases(small_corpus(), cases)[0]
    assert result["parsed_values"] == {"2 Kings 8:26": 22, "2 Chronicles 22:2": 42}
    assert result["verdict"] == "direct_textual_disagreement"
    assert "not proof" in result["caution"]


def test_narrative_divergence_is_not_forced_into_contradiction():
    cases = {"cases": [{"id": "judas", "kind": "narrative",
                        "references": ["Matthew 27:5", "Acts 1:18"]}]}
    assert audited_cases(small_corpus(), cases)[0]["verdict"] == "review_required"


def test_missing_verse_and_fake_external_source_fail():
    cases = {"cases": [{"id": "bad", "kind": "narrative",
                        "references": ["Matthew 27:5", "John 1:1"]}]}
    with pytest.raises(CorpusError, match="missing verse"):
        audited_cases(small_corpus(), cases)
    cases["cases"][0]["references"] = ["Matthew 27:5", "Acts 1:18"]
    cases["cases"][0]["external_sources"] = [{"url": "http://untrusted.invalid", "perspective": "bogus"}]
    with pytest.raises(CorpusError, match="externally supplied"):
        audited_cases(small_corpus(), cases)


def test_unabridged_gate_rejects_incomplete_books(tmp_path):
    (tmp_path / "Books.json").write_text(json.dumps(list(EXPECTED_BOOKS)))
    (tmp_path / "Books_chapter_count.json").write_text(
        json.dumps([[name, 1] for name in EXPECTED_BOOKS]))
    with pytest.raises(CorpusError, match="missing or unexpected"):
        load_corpus(tmp_path)


def fake_large_corpus(root: Path):
    # Intentional synthetic text; checks only technical completeness logic.
    (root / "Books.json").write_text(json.dumps(list(EXPECTED_BOOKS)))
    counts = []
    for name in EXPECTED_BOOKS:
        chapters = 17 if name in EXPECTED_BOOKS[:75] else 16
        counts.append([name, chapters])
        book = {"book": name, "chapter-count": str(chapters), "chapters": [
            {"chapter": ch, "verses": [
                {"verse": v, "text": f"fixture {v}"} for v in range(1, 26)]
            } for ch in range(1, chapters + 1)]}
        (root / f"{name}.json").write_text(json.dumps(book))
    # 75 * 17 + 5 * 16 = 1355 chapters, with 33875 entirely fictional verses.
    (root / "Books_chapter_count.json").write_text(json.dumps(counts))


def test_full_fixture_proves_structural_gate_only(tmp_path):
    fake_large_corpus(tmp_path)
    corpus = load_corpus(tmp_path)
    assert len(corpus.books) == 80
    assert corpus.chapter_count == 1355
    assert len(corpus.verses) == 33875
    assert len(corpus.sha256) == 64
    path = tmp_path / "Judith.json"
    book = json.loads(path.read_text())
    book["chapters"][0]["verses"][6]["verse"] = 8
    path.write_text(json.dumps(book))
    with pytest.raises(CorpusError, match="missing/bad verse"):
        load_corpus(tmp_path)


def test_sqlite_retrieval_does_not_overwrite(tmp_path):
    path = tmp_path / "scripture.sqlite"
    build_read_only_index(small_corpus(), path)
    with sqlite3.connect(path) as con:
        assert con.execute("SELECT text FROM verses WHERE ref=?",
                           ("Matthew 27:5",)).fetchone()
    with pytest.raises(CorpusError, match="will not overwrite"):
        build_read_only_index(small_corpus(), path)


def test_complete_synthetic_report_keeps_uncertainty(tmp_path):
    fake_large_corpus(tmp_path)
    cases_path = tmp_path.parent / "catalog.json"
    cases_path.write_text(json.dumps({"cases": [{
        "id": "narrative", "kind": "narrative",
        "references": ["Genesis 1:1", "Genesis 1:2"],
    }]}))
    report = analyze(tmp_path, cases_path)
    assert report["books"] == 80 and report["chapters"] == 1355
    assert report["cases"][0]["verdict"] == "review_required"
    assert report["external_references_fetched_and_verified_by_lab"] is False
    assert report["textual_edition_collation_with_1611_facsimile"] == "not_performed"
