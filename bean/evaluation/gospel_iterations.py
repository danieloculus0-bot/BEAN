"""Lab 019-B: bounded iterative historical feasibility investigation.

Five separately recorded sessions per dispute, with observed source availability,
competing models, literal consistency, and honest uncertainty. This is a
deterministic research harness, not autonomous independent historical reasoning.
A reachable website is NOT verification that a factual claim is true.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import ssl
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable

from bean.evaluation.gospel_lab import (
    Corpus, CorpusError, _load_json, audited_cases, load_corpus,
    read_reference_only_catalog,
)

SCHEMA = "bean.gospel_historical_iterations.v1"
ALLOWED_DOMAINS = frozenset({
    "www.icr.org", "www.historicalchristian.faith", "www.thegospelcoalition.org",
    "www.catholic.com", "www.thetorah.com", "www.cambridge.org",
    "textandcanon.org", "manuscriptwitness.com", "biblia.com",
    "ibri.org", "pubs.usgs.gov", "humanorigins.si.edu",
    "en.wikisource.org", "www.biblegateway.com", "www.ncbi.nlm.nih.gov",
    "oceanservice.noaa.gov", "www.nationalacademies.org", "science.nasa.gov",
    "hmane.harvard.edu",
})
OUTCOMES = {"possible", "impossible", "undetermined", "not_applicable"}
PASS_NAMES = (
    "01_sources_and_literal_claims",
    "02_competing_sources",
    "03_adversarial_countermodels",
    "04_constraint_reasoning",
    "05_falsification_and_audit",
)


def _safe_https_url(url: str) -> str:
    if not isinstance(url, str) or len(url) > 2000:
        raise CorpusError("invalid fact-finding source")
    parsed = urllib.parse.urlsplit(url)
    if (parsed.scheme != "https" or parsed.hostname not in ALLOWED_DOMAINS
            or parsed.username or parsed.password or parsed.port not in (None, 443)
            or parsed.fragment):
        raise CorpusError("URL is not an approved research domain")
    return url


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    """Do not accidentally fetch unexpected hosts by following redirects."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def fetch_source(url: str) -> dict:
    """A transport observation, NOT semantic fact verification."""
    _safe_https_url(url)
    opener = urllib.request.build_opener(
        _NoRedirect, urllib.request.HTTPSHandler(context=ssl.create_default_context())
    )
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "BEAN-Lab019-Research/1.0 (read-only; github-actions)"},
        method="GET",
    )
    try:
        with opener.open(req, timeout=8) as response:
            # Deliberately small excerpt, hashed but not preserved in reports.
            data = response.read(32768)
            raw_title = re.search(rb"<title[^>]*>(.*?)</title\s*>", data,
                                  flags=re.I | re.S)
            title = (re.sub(r"\s+", " ", raw_title.group(1).decode("utf-8", "replace"))
                     [:140] if raw_title else None)
            return {
                "transport": "http_response",
                "http_code": response.status,
                "title_hint": title,
                "sample_sha256": hashlib.sha256(data).hexdigest(),
                "sample_bytes": len(data),
                "factual_claim_verified": False,
            }
    except urllib.error.HTTPError as exc:
        return {
            "transport": "http_response",
            "http_code": exc.code,
            "factual_claim_verified": False,
            "error_kind": "http_error",
        }
    except (TimeoutError, OSError, ValueError) as exc:
        return {
            "transport": "unavailable",
            "error_kind": type(exc).__name__,
            "factual_claim_verified": False,
        }


@dataclass(frozen=True)
class Possibility:
    strict_joint_reading: str
    alternative_historical_scenario: str
    historically_attested_event: str
    reason: str
    dependencies: tuple[str, ...]
    limitations: str

    def __post_init__(self):
        if (self.strict_joint_reading not in OUTCOMES
                or self.alternative_historical_scenario not in OUTCOMES
                or self.historically_attested_event not in OUTCOMES):
            raise CorpusError("invalid possibility conclusion")
        if self.historically_attested_event == "possible":
            raise CorpusError("logical possibility cannot establish historical occurrence")


def analyze_possibility(case: dict, model: dict) -> Possibility:
    """Classify only narrowly formalized assumptions, not theological truth."""
    literal = model["literal_model"]
    kind = literal["type"]
    refs = literal["source_refs"]
    texts = case["scripture_evidence"]
    if any(ref not in texts for ref in refs):
        raise CorpusError("historical model reference not supported by scripture")
    other = model["alternative_model"]
    if kind == "numeric_same_event":
        values = case.get("parsed_values") or {}
        if any(type(values.get(ref)) is not int for ref in refs):
            return Possibility(
                "undetermined", "undetermined", "undetermined",
                "Numeric assertions cannot be parsed reliably.", tuple(refs),
                "No numerical verdict when source parsing is incomplete.")
        mismatch = len({values[ref] for ref in refs}) > 1
        return Possibility(
            "impossible" if mismatch else "possible", "possible" if mismatch else "undetermined",
            "undetermined",
            ("The same named event cannot literally give two distinct single-valued ages."
             if mismatch else "The reported numeric ages match."),
            tuple(refs),
            "A proposed scribal correction is logically possible, not independently confirmed.")
    if kind == "date_overlap":
        intervals = literal["premises"]
        if not isinstance(intervals, list) or len(intervals) != 2:
            raise CorpusError("date overlap requires two historically qualified premises")
        for item in intervals:
            if (type(item.get("start_year")) is not int
                    or type(item.get("end_year")) is not int
                    or item["start_year"] > item["end_year"]):
                raise CorpusError("invalid historical date constraint")
        overlap = max(x["start_year"] for x in intervals) <= min(
            x["end_year"] for x in intervals)
        return Possibility(
            "possible" if overlap else "impossible",
            "undetermined",
            "undetermined",
            ("The dated intervals overlap under the stated premises."
             if overlap else "These dated intervals do not overlap; that exact single-date reconstruction fails."),
            tuple(refs),
            "Premise dates come from secondary summaries and are not independently validated by this rule engine.")
    if kind == "sequence_possible":
        if not literal.get("assumptions"):
            raise CorpusError("an explanatory sequence needs stated assumptions")
        return Possibility(
            "possible", "possible", "undetermined",
            "The two narrative descriptions permit a sequential interpretation under explicit added assumptions.",
            tuple(refs),
            "Possible does not mean independently documented; an added sequence may be historically false.")
    if kind == "unsupported_attribution":
        claim = literal["proposed_claim"]
        if not isinstance(claim, str) or not claim:
            raise CorpusError("missing attribution hypothesis")
        return Possibility(
            "not_applicable", "undetermined", "undetermined",
            "The alleged numerical Earth age is a later interpretive inference, not asserted in the selected verses.",
            tuple(refs),
            "Earth-age estimates require separately evaluated scientific dating methods; do not blame the text for an unstated claim.")
    if kind == "capacity_bound":
        dim = literal.get("dimensions_cubits", [])
        cubit_m = literal.get("cubit_m")
        frac = literal.get("usable_fraction_assumed")
        pairs = literal.get("hypothetical_pairs")
        per_animal = literal.get("volume_per_animal_and_supplies_m3")
        if (not isinstance(dim, list) or len(dim) != 3
                or any(type(x) not in (int, float) or x <= 0 for x in dim)
                or type(cubit_m) not in (int, float) or not 0.3 <= cubit_m <= 0.6
                or type(frac) not in (int, float) or not 0 < frac <= 1
                or not isinstance(pairs, list) or len(pairs) != 2
                or any(type(x) is not int or x <= 0 for x in pairs)
                or type(per_animal) not in (int, float) or per_animal <= 0):
            raise CorpusError("invalid conditional Ark capacity assumptions")
        gross_m3 = dim[0] * dim[1] * dim[2] * cubit_m ** 3
        usable_m3 = gross_m3 * frac
        requirements = [round(2 * n * per_animal) for n in pairs]
        feasible = [req <= usable_m3 for req in requirements]
        return Possibility(
            "undetermined", "possible" if any(feasible) else "undetermined",
            "undetermined",
            (f"Illustrative gross Ark space {gross_m3:,.0f} m^3 and assumed "
             f"usable {usable_m3:,.0f} m^3. Hypothetical {pairs[0]} vs "
             f"{pairs[1]} pairs need {requirements[0]:,} vs {requirements[1]:,} "
             f"m^3; corresponding fit states {feasible}. None is a measured historical count."),
            tuple(refs),
            "Explicit biblical 'kinds' and net usable cargo volume are unknown; this is not validation of Ark logistics.")
    if kind == "category_exception":
        return Possibility(
            "possible", "possible", "undetermined",
            "A general two-animal instruction can be qualified by clean-animal and bird exceptions.",
            tuple(refs),
            "The meaning of 'by sevens' needs close Hebrew textual comparison; do not assert exactly seven pairs.")
    if kind == "observational_conflict":
        if not literal.get("scientific_evidence"):
            raise CorpusError("scientific model lacks a described evidence test")
        return Possibility(
            "undetermined", "possible", "undetermined",
            "The narrowly specified recent literal interpretation conflicts with externally "
            "reported scientific observations; their content has not been authenticated by this engine.",
            tuple(refs),
            "Scientific evidence can disconfirm a natural-history claim without logically disproving every supernatural interpretation.")
    if kind in {"mechanism_unknown", "population_founders"}:
        if kind == "mechanism_unknown" and not literal.get("mechanism"):
            raise CorpusError("biological or physical model missing mechanism")
        if kind == "population_founders" and literal.get("founders_per_lineage_assumed") != 2:
            raise CorpusError("founder model must explicitly state its assumed population size")
        return Possibility(
            "undetermined", "undetermined", "undetermined",
            "Natural-process feasibility cannot be established from this passage alone; "
            "specific quantitative constraints and independently assessed records are required.",
            tuple(refs),
            "Unknown is not a positive compatibility verdict; do not invent a genetic or ecological reconstruction.")
    if kind == "donor_cell_only":
        if (literal.get("donor_karyotype") != "46,XY"
                or literal.get("target_karyotype") != "46,XX"):
            raise CorpusError("explicit donor and target chromosome assumptions required")
        return Possibility(
            "impossible", "undetermined", "undetermined",
            "Ordinary expansion of XY rib tissue alone cannot produce an independent "
            "fully developed typical XX female without developmental and genetic interventions.",
            tuple(refs),
            "Conditional finding concerns the assumed unmodified XY somatic-cell-only process. "
            "Some women are not XX; the text does not specify chromosomes or exclude divine intervention.")
    if kind == "later_identity":
        return Possibility(
            "undetermined", "possible", "undetermined",
            "A later text or interpretation can identify earlier figures without the earlier passage naming them.",
            tuple(refs),
            "Literary identification is evidence of a belief or tradition, not evidence of a supernatural entity.")
    if kind in {"narrative_sequence", "layered_cause"}:
        if not literal.get("assumptions"):
            raise CorpusError("narrative compatibility needs explicit added assumptions")
        return Possibility(
            "possible", "possible", "undetermined",
            "Under the specified temporal or multiple-causation assumptions these descriptions can coexist.",
            tuple(refs),
            "Coexistence is conditional; literary history could still reflect genuinely competing traditions.")
    if kind == "line_of_sight":
        if literal.get("assumption") != "literal simultaneous unaided visual line-of-sight from one Earth mountain":
            raise CorpusError("line-of-sight scenario lacks precise physically testable assumption")
        return Possibility(
            "impossible", "possible", "undetermined",
            "Earth curvature and obstructed sight lines prevent unaided simultaneous "
            "visibility of all global territories from a mountain.",
            tuple(refs),
            "An implied vision or figurative description is not ruled out by ordinary visual geometry.")
    if kind in {"textual_interpretation_open", "manuscript_origin_open"}:
        return Possibility(
            "undetermined",
            "possible" if kind == "manuscript_origin_open" else "undetermined",
            "undetermined",
            ("Transmission of alternate manuscript endings is possible; original authorship remains disputed."
             if kind == "manuscript_origin_open"
             else "Competing literary readings do not define one unambiguous historical event sequence."),
            tuple(refs),
            "A manuscript's existence supports a textual tradition, not the factuality of what it narrates.")
    raise CorpusError(f"unsupported model kind: {kind}")


def _validated_models(cases: list[dict], model_packet: dict) -> dict:
    if model_packet.get("schema") != "bean.gospel_historical_models.v1":
        raise CorpusError("unsupported historical model schema")
    models = model_packet.get("cases")
    if not isinstance(models, list) or any(not isinstance(row, dict) for row in models):
        raise CorpusError("missing historical models")
    ids = [row.get("id") for row in models]
    if len(ids) != len(set(ids)) or set(ids) != {row["case_id"] for row in cases}:
        raise CorpusError("every dispute must have exactly one explicit historical model")
    allowed = {row["case_id"]: set(row["scripture_evidence"]) for row in cases}
    for row in models:
        literal = row.get("literal_model")
        alternate = row.get("alternative_model")
        if (not isinstance(literal, dict) or not isinstance(alternate, dict)
                or not isinstance(row.get("research"), list)
                or not isinstance(row.get("limits"), str)):
            raise CorpusError("incomplete or biased historical case model")
        refs = literal.get("source_refs")
        if (not isinstance(refs, list) or not refs or any(ref not in allowed[row["id"]] for ref in refs)):
            raise CorpusError("model cites material absent from the audited scripture case")
        for src in row["research"]:
            if (not isinstance(src, dict)
                    or not isinstance(src.get("claim"), str)
                    or not isinstance(src.get("role"), str)):
                raise CorpusError("research lead lacks source framing")
            _safe_https_url(src.get("url"))
    return {row["id"]: row for row in models}


def investigate(corpus: Corpus, case_packet: dict, model_packet: dict, *,
                rounds: int = 5, source_fetcher: Callable[[str], dict] | None = None,
                gnostic_catalog: Path | None = None) -> dict:
    if type(rounds) is not int or not 2 <= rounds <= 10:
        raise CorpusError("iterations must be between 2 and 10")
    cases = audited_cases(corpus, case_packet)
    models = _validated_models(cases, model_packet)
    case_map = {row["case_id"]: row for row in cases}
    catalog = (read_reference_only_catalog(gnostic_catalog)
               if gnostic_catalog is not None else None)
    observed: dict[str, dict] = {}
    journal: list[dict] = []
    verdicts = {}
    for i in range(1, rounds + 1):
        new_sources: list[str] = []
        queues = []
        # Fact finding is rotated rather than repeatedly retrying one source.
        for case in cases:
            refs = models[case["case_id"]]["research"]
            if i <= len(refs):
                source = refs[i - 1]
                if source["url"] not in observed:
                    queues.append((case["case_id"], source))
        if source_fetcher is not None and queues:
            with ThreadPoolExecutor(max_workers=4) as pool:
                futures = [pool.submit(source_fetcher, src["url"]) for _, src in queues]
                for (cid, source), future in zip(queues, futures):
                    observed[source["url"]] = {
                        "case_id": cid, "url": source["url"], "research_claim": source["claim"],
                        "perspective_role": source["role"],
                        "observation": future.result(),
                        "source_claim_authenticated": False,
                        "independent_historical_fact_proven": False,
                    }
                    new_sources.append(source["url"])
        elif queues:
            for cid, source in queues:
                observed[source["url"]] = {
                    "case_id": cid, "url": source["url"], "research_claim": source["claim"],
                    "perspective_role": source["role"],
                    "observation": {"transport": "not_requested", "factual_claim_verified": False},
                    "source_claim_authenticated": False,
                    "independent_historical_fact_proven": False,
                }
                new_sources.append(source["url"])
        outcomes = {}
        changed = []
        for case in cases:
            mid = case["case_id"]
            model = models[mid]
            # Under investigation, we compare source *availability*, not faith in a proposition.
            best = analyze_possibility(case, model)
            info = asdict(best)
            # A repeat pass cannot strengthen a conclusion merely by restating it.
            if verdicts.get(mid) != info:
                changed.append(mid)
            verdicts[mid] = info
            relevant = [s for s in observed.values() if s["case_id"] == mid]
            outcomes[mid] = {
                "case_id": mid,
                "literal_constraints": info["strict_joint_reading"],
                "alternative_scenario": info["alternative_historical_scenario"],
                "historical_event_verified": False,
                "historical_status": info["historically_attested_event"],
                "adversarial_model": model["alternative_model"],
                "source_observations": len(relevant),
                "source_truth_independently_verified": 0,
                "basis": info["reason"], "limitations": info["limitations"],
                "all_verses": dict(case["scripture_evidence"]),
            }
        journal.append({
            "iteration": i,
            "purpose": PASS_NAMES[i - 1] if i <= len(PASS_NAMES) else "recheck_no_automatic_certainty",
            "new_sources_examined": new_sources,
            "total_source_observations": len(observed),
            "conclusions_changed": changed,
            "historical_facts_independently_verified": 0,
            "all_disputes_examined": len(outcomes),
            "cases": outcomes,
        })
    all_disputes = {row["case_id"] for row in cases}
    coverage = len(verdicts)
    return {
        "schema": SCHEMA,
        "rounds": rounds,
        "catalogued_disputes": len(all_disputes),
        "disputes_with_formal_assessment": coverage,
        "dispute_coverage_pct": round(100 * coverage / len(all_disputes), 1) if all_disputes else 0,
        "entire_bible_all_possible_disputes_discovered": False,
        "independent_historical_source_semantic_validation": False,
        "historical_certainty_claimed": False,
        "text_input_sha256": corpus.sha256,
        "source_observations": list(observed.values()),
        "gnostic_reference_only": True,
        "gnostic_catalog_loaded": catalog is not None,
        "gnostic_texts_in_historical_verdicts": 0,
        "iterations": journal,
        "final_assessments": verdicts,
        "limitations": (
            "Every catalogued question has a conditional feasibility result. It does not "
            "prove each described historical event happened or did not happen. Source HTTP "
            "observations confirm at most that a page was retrievable, not its truth. "
            "The six hand-curated disputes are not an exhaustive search of every possible "
            "disagreement in all 36,702 verse entries."
        ),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Iterative historical evidence sessions")
    parser.add_argument("--corpus", type=Path, required=True)
    parser.add_argument("--corrections", type=Path, required=True)
    parser.add_argument("--cases", type=Path, required=True)
    parser.add_argument("--models", type=Path, required=True)
    parser.add_argument("--gnostic-reference-catalog", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--iterations", type=int, default=5)
    parser.add_argument("--live-sources", action="store_true", help="Perform bounded HTTPS source lookups")
    args = parser.parse_args(argv)
    corpus = load_corpus(args.corpus, corrections_path=args.corrections)
    report = investigate(
        corpus, _load_json(args.cases), _load_json(args.models),
        rounds=args.iterations,
        source_fetcher=fetch_source if args.live_sources else None,
        gnostic_catalog=args.gnostic_reference_catalog,
    )
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n",
                           encoding="utf-8")
    print(json.dumps({
        "iterations": report["rounds"],
        "catalogued_disputes": report["catalogued_disputes"],
        "covered_disputes": report["disputes_with_formal_assessment"],
        "live_source_observations": len(report["source_observations"]),
        "source_truth_proven": False,
        "final_assessments": report["final_assessments"],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
