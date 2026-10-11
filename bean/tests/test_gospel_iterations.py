"""Lab 019-B synthetic regression; it does not verify ancient historicity."""
import copy
import json
from pathlib import Path

import pytest

from bean.evaluation.gospel_iterations import (
    SCHEMA, _safe_https_url, analyze_possibility, fetch_source, investigate,
)
from bean.evaluation.gospel_lab import CorpusError
from bean.tests.test_gospel_lab import small_corpus


def _case(cid, kind, texts, parsed=None):
    return {"case_id": cid, "kind": kind,
            "scripture_evidence": texts, "parsed_values": parsed or {}}


def _model(cid, kind, refs, **props):
    return {"id": cid, "literal_model": {"type": kind, "source_refs": refs, **props},
            "alternative_model": {"type": "other", "statement": "Competing interpretation",
                                  "status": "undetermined"},
            "research": [], "limits": "No independent historical attestation"}


def test_literal_same_event_two_ages_impossible_but_scribal_reconstruction_possible():
    case = _case("king", "same_event_numeric", {
        "2 Kings 8:26": "Two and twentie yeeres old",
        "2 Chronicles 22:2": "Fourtie and two yeeres old",
    }, {"2 Kings 8:26": 22, "2 Chronicles 22:2": 42})
    model = _model("king", "numeric_same_event", list(case["scripture_evidence"]))
    verdict = analyze_possibility(case, model)
    assert verdict.strict_joint_reading == "impossible"
    assert verdict.alternative_historical_scenario == "possible"
    assert verdict.historically_attested_event == "undetermined"


def test_historical_intervals_no_overlap_under_explicit_assumptions():
    texts = {"Matthew 2:1": "Herod", "Luke 2:2": "Quirinius"}
    case = _case("census", "chronology", texts)
    model = _model("census", "date_overlap", list(texts),
                   premises=[{"start_year": -4, "end_year": -4},
                             {"start_year": 6, "end_year": 6}])
    verdict = analyze_possibility(case, model)
    assert verdict.strict_joint_reading == "impossible"
    assert verdict.alternative_historical_scenario == "undetermined"
    assert verdict.historically_attested_event == "undetermined"
    model["literal_model"]["premises"][1] = {"start_year": -4, "end_year": -4}
    assert analyze_possibility(case, model).strict_joint_reading == "possible"


def test_narrative_possible_is_not_event_verified():
    texts = {"Matthew 27:5": "hanged himself", "Acts 1:18": "fell headlong"}
    case = _case("judas", "narrative", texts)
    model = _model("judas", "sequence_possible", list(texts), assumptions=["fall later"])
    result = analyze_possibility(case, model)
    assert result.strict_joint_reading == "possible"
    assert result.historically_attested_event == "undetermined"


def test_unstated_six_thousand_year_earth_not_attributed_to_scripture():
    texts = {"Genesis 1:1": "God created", "Genesis 1:5": "Day"}
    case = _case("age", "scientific", texts)
    model = _model("age", "unsupported_attribution", list(texts),
                   proposed_claim="Earth created 6000 years ago")
    result = analyze_possibility(case, model)
    assert result.strict_joint_reading == "not_applicable"
    assert result.historically_attested_event == "undetermined"


def test_network_allowlist_blocks_unrelated_servers_and_credentials():
    for value in [
        "http://www.icr.org/page", "https://127.0.0.1/",
        "https://localhost/", "https://example.com/",
        "https://user:pass@www.icr.org/", "https://www.icr.org:8080/",
        "https://www.icr.org/page#fragment",
    ]:
        with pytest.raises(CorpusError):
            _safe_https_url(value)
    assert _safe_https_url("https://www.icr.org/books/defenders/2310")


def test_all_disputes_have_formal_models_and_five_true_journal_iterations(tmp_path):
    corpus = small_corpus()
    case_packet = {
        "cases": [
            {"id": "age", "kind": "same_event_numeric",
             "references": ["2 Kings 8:26", "2 Chronicles 22:2"]},
            {"id": "death", "kind": "narrative",
             "references": ["Matthew 27:5", "Acts 1:18"]},
        ]}
    model_packet = {
        "schema": "bean.gospel_historical_models.v1",
        "cases": [
            _model("age", "numeric_same_event",
                   ["2 Kings 8:26", "2 Chronicles 22:2"]),
            _model("death", "sequence_possible",
                   ["Matthew 27:5", "Acts 1:18"], assumptions=["a later fall"]),
        ]}
    model_packet["cases"][0]["research"] = [
        {"url": "https://www.icr.org/books/defenders/2310",
         "claim": "A source says something", "role": "interpretation"},
        {"url": "https://www.historicalchristian.faith/doctrine/doctrines/ahaziah-age.html",
         "claim": "Secondary summary", "role": "counterargument"},
    ]
    looked_up = []

    def fake_source(url):
        looked_up.append(url)
        return {"transport": "http_response", "http_code": 200,
                "factual_claim_verified": False}

    report = investigate(corpus, case_packet, model_packet, rounds=5,
                         source_fetcher=fake_source)
    assert report["schema"] == SCHEMA
    assert report["rounds"] == 5
    assert report["catalogued_disputes"] == 2
    assert report["disputes_with_formal_assessment"] == 2
    assert report["dispute_coverage_pct"] == 100
    assert report["entire_bible_all_possible_disputes_discovered"] is False
    assert len(looked_up) == 2
    assert len(report["iterations"]) == 5
    assert [item["total_source_observations"] for item in report["iterations"]] == [
        1, 2, 2, 2, 2
    ]
    assert report["iterations"][0]["conclusions_changed"] == ["age", "death"]
    assert all(row["conclusions_changed"] == [] for row in report["iterations"][1:])
    assert all(row["historical_facts_independently_verified"] == 0
               for row in report["iterations"])
    assert report["gnostic_texts_in_historical_verdicts"] == 0
    assert report["final_assessments"]["age"]["strict_joint_reading"] == "impossible"
    assert report["final_assessments"]["death"]["strict_joint_reading"] == "possible"
    assert report["final_assessments"]["death"]["historically_attested_event"] == "undetermined"
    for item in report["iterations"]:
        assert set(item["cases"]) == {"age", "death"}
        assert all(not assessment["historical_event_verified"]
                   for assessment in item["cases"].values())
    # Add a dispute without adding its rival evidence model: must fail.
    incomplete = copy.deepcopy(model_packet)
    incomplete["cases"].pop()
    with pytest.raises(CorpusError, match="every dispute"):
        investigate(corpus, case_packet, incomplete)


def test_source_transport_never_means_verified_historical_facts():
    corpus = small_corpus()
    cases = {"cases": [{"id": "j", "kind": "narrative",
                        "references": ["Matthew 27:5", "Acts 1:18"]}]}
    model = _model("j", "sequence_possible", ["Matthew 27:5", "Acts 1:18"],
                   assumptions=["could occur sequentially"])
    model["research"] = [{"url": "https://www.icr.org/books/defenders/2310",
                          "claim": "Source claim", "role": "opinion"}]
    pack = {"schema": "bean.gospel_historical_models.v1", "cases": [model]}
    report = investigate(corpus, cases, pack, rounds=2,
                         source_fetcher=lambda url: {
                             "transport": "http_response", "http_code": 200,
                             "factual_claim_verified": False,
                         })
    assert report["source_observations"][0]["independent_historical_fact_proven"] is False
    assert report["source_observations"][0]["source_claim_authenticated"] is False
    assert report["independent_historical_source_semantic_validation"] is False
    assert report["historical_certainty_claimed"] is False


def test_source_attributed_context_does_not_automatically_prove_events(tmp_path):
    from bean.evaluation.gospel_iterations import read_documented_facts
    packet = {
        "schema": "bean.gospel_sourced_fact_context.v1",
        "source_verification_method": (
            "Text of cited public sources inspected by research assistant via web retrieval; "
            "interpretations cross-checked when feasible, not a BEAN autonomous validation "
            "or replicated experiment."),
        "records": [
            {"fact_id": "sun", "kind": "measurement_summary",
             "source_url": "https://science.nasa.gov/sun/facts/",
             "source_org": "NASA",
             "statement": "The solar system is about 4.6 billion years old.",
             "related_cases": ["creation"],
             "confidence_scope": "astronomical history",
             "contra": "Literary-day readings differ from literal formation timetables.",
             "evidence_weight": "established physical chronology"}
        ],
    }
    path = tmp_path / "facts.json"
    path.write_text(json.dumps(packet))
    parsed = read_documented_facts(path, valid_case_ids={"creation"})
    assert len(parsed["creation"]) == 1
    assert parsed["creation"][0]["record_id"] == "sun"
    assert not parsed["creation"][0]["autonomously_verified_by_BEAN"]
    assert not parsed["creation"][0]["experimentally_reproduced_by_BEAN"]
    packet["records"][0]["related_cases"] = ["unreferenced_case"]
    path.write_text(json.dumps(packet))
    with pytest.raises(CorpusError, match="unknown dispute"):
        read_documented_facts(path, valid_case_ids={"creation"})


def test_five_sessions_change_research_assignments_not_certainty():
    from bean.evaluation.gospel_iterations import _session_probe
    model = {"alternative_model": {"type": "other", "statement": "Other model"},
             "literal_model": {"type": "date_overlap", "source_refs": ["Matthew 2:1"]}}
    case = {"scripture_evidence": {"Matthew 2:1": "Herod"}}
    info = {"strict_joint_reading": "impossible", "limitations": "premise-dependent"}
    probes = [
        _session_probe(i, case, model, info, [], []) for i in range(1, 6)
    ]
    assert [x["activity"] for x in probes] == [
        "establish_primary_text",
        "test_external_source_access_and_documented_science",
        "attempt_counterinterpretation",
        "quantify_conditional_feasibility",
        "falsification_and_missing_evidence",
    ]
    assert probes[4]["certainty_increased_from_repetition_alone"] is False
    assert probes[1]["historical_fact_independently_attested_by_engine"] is False
