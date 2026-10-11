"""Behavioral tests for the complete-verses screening loop."""
from bean.evaluation.gospel_lab import Corpus, CorpusError
from bean.evaluation.gospel_wholebook import PASS_RULES, RULES, screen_corpus


def fixture():
    return Corpus(
        {
            "Genesis 1:1": "In the beginning God created the heaven and earth.",
            "Genesis 1:5": "The evening and morning were the first day.",
            "Genesis 6:15": "The length of the arke shall be three hundred cubits.",
            "Genesis 6:19": "Two of every sort shall come into the arke.",
            "Genesis 7:19": "All high hills under the whole heaven were covered.",
            "Genesis 2:21": "And he took one of his ribs.",
            "Job 1:6": "And Satan came also among them.",
            "Revelation 12:9": "That old serpent, called the devil and Satan.",
            "2 Chronicles 22:2": "Fourtie and two yeeres old was Ahaziah.",
            "Romans 8:1": "There is therefore now no condemnation.",
        }, ("Genesis", "Job", "Revelation", "2 Chronicles", "Romans"), 8, "test-hash"
    )


def test_every_verse_passed_through_five_distinct_rule_groups():
    corpus = fixture()
    result = screen_corpus(corpus)
    assert len(result["passes"]) == 5
    assert len(set(x["name"] for x in result["passes"])) == 5
    assert all(x["verses_examined"] == len(corpus.verses) for x in result["passes"])
    assert all(x["historical_claims_verified"] == 0 for x in result["passes"])
    assert len(result["all_screened_candidate_entries"]) == result["verses_flagged"]
    assert result["verses_flagged"] + result["verses_not_flagged"] == len(corpus.verses)
    assert result["verse_entries_examined_each_pass"] == len(corpus.verses)
    assert result["all_possible_inaccuracies_discovered"] is False
    assert result["every_historical_claim_adjudicated"] is False
    assert len(RULES) >= 15
    assert len(PASS_RULES) == 5


def test_full_review_queue_no_hidden_truncation_and_source_refs_preserved():
    data = fixture()
    report = screen_corpus(data, comparison_case_refs={
        "serpent_question": ["Job 1:6", "Revelation 12:9"],
        "ark_question": ["Genesis 6:15", "Genesis 6:19"]})
    refs = {q["reference"] for q in report["all_screened_candidate_entries"]}
    assert "Genesis 6:15" in refs
    assert "Genesis 7:19" in refs
    assert "Job 1:6" in refs
    assert "Revelation 12:9" in refs
    assert "2 Chronicles 22:2" in refs
    assert "Romans 8:1" not in refs
    assert len(report["formal_dispute_links"]) == 2
    assert all(link["status"] == "requires_conditional_model"
               for link in report["formal_dispute_links"])
    assert not any(link["subject_event_identity_independently_proven"]
                   for link in report["formal_dispute_links"])
    assert all(entry["review"] == "not_individually_adjudicated"
               for entry in report["all_screened_candidate_entries"])


def test_missing_named_verse_fails_closed():
    try:
        screen_corpus(fixture(), comparison_case_refs={"nope": ["Genesis 13:4"]})
    except CorpusError as error:
        assert "lacks indexed scripture" in str(error)
    else:
        raise AssertionError("missing reference silently accepted")


def test_false_positive_cannot_be_reported_as_historical_disproof():
    sample = Corpus({"1 Kings 1:1": "King David was old and stricken in yeeres.",
                     "1 Kings 1:2": "And his seruants asked how he slept."},
                    ("1 Kings",), 1, "test")
    result = screen_corpus(sample)
    for row in result["all_screened_candidate_entries"]:
        assert row["hypothesis_status"] == "candidate_only"
        assert row["review"] == "not_individually_adjudicated"
    assert not result["verse_semantics_fully_understood"]


def test_discovers_unseeded_cross_book_regnal_ages_without_pretending_identity_proven():
    from bean.evaluation.gospel_wholebook import mine_cross_book_accession_age_pairs
    corpus = Corpus({
        "2 Kings 8:26": "Two and twentie yeeres old was Ahaziah when he began to reigne.",
        "2 Chronicles 22:2": "Fourtie and two yeeres old was Ahaziah when he began to reigne.",
        "1 Kings 4:2": "Other commentary about a different person without an accession.",
    }, ("2 Kings", "2 Chronicles", "1 Kings"), 3, "fixture")
    links = mine_cross_book_accession_age_pairs(corpus)
    assert len(links) == 1
    assert links[0]["candidate_name"] == "ahaziah"
    assert {links[0]["age_a"], links[0]["age_b"]} == {22, 42}
    assert links[0]["verdict"] == "review_required"
    assert links[0]["same_historical_person_verified"] is False
    assert links[0]["same_event_verified"] is False
    assert links[0]["proven_inaccuracy"] is False
