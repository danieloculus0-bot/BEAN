"""BEAN peer developer: revise a real model patch after independent CI failure.

The host supplies a hash-pinned prior model candidate and a verifier receipt,
not hidden test files or a human-authored fix. Only a NEW model-authored source
revision is emitted; generated code is never executed with provider secrets.
"""
from __future__ import annotations
import argparse
import difflib
import json
import os
from pathlib import Path
import re
from urllib.request import urlopen

from bean.evaluation import bridge_peer_live_author as base

PRIOR_RUN = 38109084399
RECEIPT = "bean.core.bridge.feedback-revision.v1"


def evidence_inputs(original, oracle_digest, prior_folder, result_folder):
    proposal_file = Path(prior_folder) / "candidate.json"
    author_file = Path(prior_folder) / "author-receipt.json"
    verdict_file = Path(result_folder) / "verify-receipt.json"
    candidate = json.loads(proposal_file.read_text(encoding="utf-8"))
    author_receipt = json.loads(author_file.read_text(encoding="utf-8"))
    verdict = json.loads(verdict_file.read_text(encoding="utf-8"))
    if (candidate.get("schema") != "bean.novel-repair.v1"
        or candidate.get("base_commit") != base.BRIDGE_SHA
        or candidate.get("challenge_commit") != base.CHALLENGE_SHA
        or candidate.get("path") != str(base.TARGET)
        or candidate.get("source_sha256") != base.sha(original)
        or candidate.get("oracle_sha256") != oracle_digest
        or not isinstance(candidate.get("replacement"), str)
        or candidate.get("replacement_sha256") != base.sha(candidate["replacement"])
        or author_receipt.get("status") != "candidate_drafted_not_tested"
        or author_receipt.get("candidate_sha256") != base.sha(proposal_file.read_bytes())
        or author_receipt.get("replacement_sha256") != candidate["replacement_sha256"]):
        raise ValueError("prior model candidate has invalid source or provenance")
    if (verdict.get("schema") != "bean.novel-repair.receipt.v1"
        or verdict.get("phase") != "verify"
        or verdict.get("result") != "rejected"
        or verdict.get("suite_passed") is not False
        or not verdict.get("baseline", {}).get("normal_passed")
        or not verdict.get("baseline", {}).get("oracle_red")
        or verdict.get("diff", {}).get("replacement_sha256") != candidate["replacement_sha256"]):
        raise ValueError("no matching independently failed prior candidate")
    return candidate, verdict, base.sha(verdict_file.read_bytes())


def feedback_summary(verdict):
    """Only bounded failure categories, NOT the evaluator's test source."""
    excerpt = str(verdict.get("test_tail", ""))[-3000:]
    symbols = sorted(set(re.findall(r"test_[a-z_]{10,90}", excerpt)))
    signals = [word for word in ("rma", "production", "shipment", "window", "date")
               if word in excerpt.lower()]
    if not symbols and "FAILED" not in excerpt:
        raise ValueError("no witnessed code-test failure evidence")
    failures = re.search(r"FAILED \(failures=(\d+)", excerpt)
    result = ("Your PREVIOUS patch passed Python syntax but independently "
              "FAILED its original cross-platform Bridge tests; it was NOT "
              "promoted. Repair remaining invariant violations, not just "
              "one reporting domain. Preserve evidence and coverage semantics. "
              "Never modify tests. ")
    if failures:
        result += "Failed assertion count: " + failures.group(1) + ". "
    if signals:
        result += "Remaining affected test categories: " + ", ".join(signals) + ". "
    if symbols:
        result += "Evaluator test identifiers (no test source): " + ", ".join(symbols[:5])
    return result[:900]


def revision(*, bridge, challenge, previous, verification, out, key,
             request_fn=urlopen):
    report = {
        "schema": RECEIPT, "phase": "model_revision",
        "prior_run": PRIOR_RUN, "status": "not_attempted",
        "attempted_requests": 0, "candidate_sha256": None,
        "source_commit": base.BRIDGE_SHA, "challenge_commit": base.CHALLENGE_SHA,
    }
    try:
        original, oracle_hash = base.inputs(bridge, challenge)
        prior, verdict, verdict_hash = evidence_inputs(
            original, oracle_hash, previous, verification
        )
        prior_source = prior["replacement"]
        feedback = feedback_summary(verdict)
        report.update(prior_candidate_sha256=base.sha((Path(previous)/"candidate.json").read_bytes()),
                      prior_replacement_sha256=base.sha(prior_source),
                      verifier_receipt_sha256=verdict_hash,
                      feedback_sha256=base.sha(feedback),
                      failure_category_count=len(re.findall(r"test_[a-z_]+", feedback)))
        for model in (base.ROUTE, base.BACKUP):
            report["attempted_requests"] += 1
            try:
                text, metadata = base.call_model(
                    key, prior_source, feedback=feedback,
                    request_fn=request_fn, model=model
                )
                new_source, _ = base.apply_edits(prior_source, base.parse_plan(text))
                if new_source == original:
                    raise ValueError("revision reverted to unchanged original")
                # The independent Bridge verifier measures all changes against
                # the original pinned source, not the previous model response.
                changed = sum(line.startswith(("+ ", "- ")) for line in
                              difflib.ndiff(original.splitlines(), new_source.splitlines()))
                if changed > 100:
                    raise ValueError("cumulative edit exceeds 100 source lines")
                new_candidate = {
                    "schema": "bean.novel-repair.v1",
                    "base_commit": base.BRIDGE_SHA,
                    "challenge_commit": base.CHALLENGE_SHA,
                    "path": str(base.TARGET),
                    "source_sha256": base.sha(original),
                    "oracle_sha256": oracle_hash,
                    "replacement_sha256": base.sha(new_source),
                    "changed_lines": changed,
                    "model": metadata["model_requested"],
                    "provider": "openrouter",
                    "replacement": new_source,
                }
                base.save(out / "candidate.json", new_candidate)
                report.update(status="revised_candidate_not_tested",
                              candidate_sha256=base.sha((out/"candidate.json").read_bytes()),
                              replacement_sha256=base.sha(new_source),
                              changed_lines=changed, **metadata)
                return report
            except ValueError as exc:
                report.update(status="invalid_model_revision",
                              last_rejection=str(exc)[:120])
            except RuntimeError as exc:
                report.update(status="provider_unavailable",
                              last_rejection=str(exc)[:120])
                break
        return report
    except Exception as exc:
        report.update(status="invalid_prior_evidence",
                      last_rejection=type(exc).__name__ + ": " + str(exc)[:140])
        return report
    finally:
        base.save(out / "revision-receipt.json", report)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--bridge", type=Path, default=Path("_bridge"))
    ap.add_argument("--challenge", type=Path, default=Path("_challenge"))
    ap.add_argument("--previous", type=Path, default=Path("_prior"))
    ap.add_argument("--verification", type=Path, default=Path("_failed"))
    ap.add_argument("--out", type=Path, default=Path("_revision"))
    args = ap.parse_args()
    report = revision(
        bridge=args.bridge, challenge=args.challenge, previous=args.previous,
        verification=args.verification, out=args.out,
        key=os.environ.get("OPENROUTER_API_KEY", "")
    )
    print(json.dumps(report, sort_keys=True, indent=2))
    return 0 if report["status"] == "revised_candidate_not_tested" else 1


if __name__ == "__main__":
    raise SystemExit(main())
