"""Continue real Nemotron experiment using immutable pre-rate-limit BEAN state.

No re-training, no re-selection, no old holdout replay. Download archive from
the original Actions run, hash-verify exact report, source calls and SQLite
journal, then evaluate four genuinely new task instances with ONE request per
arm. The original selected policy stays frozen through SQLite recovery.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
import os
from pathlib import Path
import shutil

from bean.learning import BEANReasoningSkills, ExperienceBank, TrialCase
from .live_reasoning_transfer import LiveProviderError
from .nemotron_self_derived_transfer import (
    MODEL, RecordingNemotron, correct,
)

ORIGINAL_RUN = 40212952629
ORIGINAL_SHA256 = {
    "report.json": "9ec544a6df5b2e0671e30513b7510056d1c0442f281e48ed068c67b9423ed6ab",
    "experience.sqlite3": "f5f24ddbba9a1d6362327f099f77eeeb77cadb47ea9013b5c33ffc4af95e997a",
    "provider_calls.jsonl": "4661425fc7afacbf03b9c4996857628cc8d64be06d7b957eadb6299c11d35ab1",
}

# None of these exact questions appeared in either original partial trial.
FRESH_HOLDOUT = (
    TrialCase("new-20261025-orchid-a", "orchid-routing",
              "ORCHID-7 for tags P7 U2 W9. Return key.", "WPU"),
    TrialCase("new-20261025-orchid-b", "orchid-routing",
              "ORCHID-7 for tags A4 K8 B1. Return key.", "KAB"),
    TrialCase("new-20261025-orchid-c", "orchid-routing",
              "ORCHID-7 for tags D3 F6 M9. Return key.", "MFD"),
    TrialCase("new-20261025-orchid-d", "orchid-routing",
              "ORCHID-7 for tags C5 Y1 S8. Return key.", "SCY"),
)


def run(*, source, output, key, model_factory=RecordingNemotron):
    source, output = Path(source), Path(output)
    output.mkdir(parents=True, exist_ok=True)
    if any(output.iterdir()):
        raise FileExistsError("Recovery results must not overwrite earlier evidence")
    manifest = {}
    for filename, expected_sha in ORIGINAL_SHA256.items():
        b = (source / filename).read_bytes()
        actual = sha256(b).hexdigest()
        if actual != expected_sha:
            raise ValueError("Source experiment data hash mismatch: " + filename)
        manifest[filename] = {"sha256": actual, "bytes": len(b)}
    original = json.loads((source / "report.json").read_text())
    if (original.get("model_requested") != MODEL
            or original.get("model_served") != MODEL
            or original.get("status") != "partial_failed"
            or original.get("requests") != 13):
        raise ValueError("Unexpected original trial provenance")
    prior = original.get("domains") or []
    if (len(prior) != 1 or prior[0].get("name") != "orchid-routing"
            or prior[0].get("selected_strategy") != "prompt"
            or prior[0].get("selection", {}).get("selection", {}).get("arm") != "prompt"
            or prior[0].get("selection", {}).get("trial", {}).get("scores") !=
            {"cold": 0, "placebo": 0, "reflection": 0, "skill": 1, "prompt": 2}):
        raise ValueError("Original selection and controls do not match source")
    from bean.learning.experimental import question_fingerprint
    old_questions = {
        entry["question_sha256"] for entry in (
            prior[0]["selection"]["trial"]["records"]
        )
    }
    # The original archive may have incomplete holdout calls without source
    # journal receipts. Compare exact questions to all preregistered originals.
    from .nemotron_self_derived_transfer import DOMAINS
    domain = next(d for d in DOMAINS if d.name == "orchid-routing")
    old_questions.update(question_fingerprint(x.public_question) for x in
                         (*domain.demonstrations, domain.validation,
                          *domain.selection, *domain.holdout))
    fresh = {question_fingerprint(x.public_question) for x in FRESH_HOLDOUT}
    if fresh & old_questions or len(fresh) != len(FRESH_HOLDOUT):
        raise ValueError("New held-out prompts overlap previous evidence")

    shutil.copyfile(source / "experience.sqlite3", output / "experience.sqlite3")
    (output / "source_manifest.json").write_text(json.dumps({
        "original_run": ORIGINAL_RUN,
        "original_artifact_id": 12606531457,
        "original_git_revision": "3e0b932b40b1d85babd8324b42e7cd65bb305c39",
        "source": manifest,
        "original_selection": "prompt",
        "source_trial_hash": prior[0]["selection"]["selection"]["source_trial_hash"],
    }, indent=2, sort_keys=True) + "\n")
    if not key:
        status = {"status": "blocked_no_api_key", "new_calls": 0,
                  "new_holdout_scores": None, "model": MODEL,
                  "original_run": ORIGINAL_RUN}
        (output / "result.json").write_text(json.dumps(status, indent=2) + "\n")
        return status
    bank = ExperienceBank(output / "experience.sqlite3")
    model = model_factory(key, model=MODEL, output=output)
    result = {
        "schema": "bean.nemotron.batched_recovery.v1",
        "status": "in_progress", "model": MODEL, "original_run": ORIGINAL_RUN,
        "old_provider_calls": 13, "new_calls": 0,
        "new_holdout_scores": None,
        "source_policy": "prompt_selected_from_original_real_provider_development_trial",
        "weight_training": False,
        "fresh_questions": [x.task_id for x in FRESH_HOLDOUT],
    }
    try:
        bean = BEANReasoningSkills(bank)
        restored = bean.decide(
            domain="orchid-routing", task_ref="frozen-recovery-before-holdout",
            query=FRESH_HOLDOUT[0].public_question)
        if restored["selected_strategy"] != "prompt":
            raise ValueError("Recovered BEAN selection differs from original")
        result["restored_decision"] = restored
        result["journal_events_before"] = len(bank.journal.events())
        out = bean.evaluate_holdout(
            domain="orchid-routing", cases=FRESH_HOLDOUT,
            model=model, judge=correct, batched=True)
        scores = out["trial"]["scores"]
        result.update({
            "status": "completed_real_batched_holdout",
            "new_calls": len(model.calls),
            "new_holdout_scores": scores,
            "holdout_receipt": out["trial"],
            "journal_events_after": len(bank.journal.events()),
            "model_served": model.calls[0]["model_served"] if model.calls else None,
            "delta_cold": scores["adaptive"] - scores["cold"],
            "delta_placebo": scores["adaptive"] - scores["placebo"],
            "interpretation": (
                "Genuine model responses to four distinct new instances "
                "using frozen BEAN prompt memory from the original partial run. "
                "No real-world knowledge learning, model weight updates or "
                "new rule induction in this resumed phase."),
        })
        (output / "result.json").write_text(
            json.dumps(result, indent=2, sort_keys=True) + "\n")
        return result
    except Exception as exc:
        result.update({
            "status": "partial_failed", "new_calls": len(model.calls),
            "error": type(exc).__name__ + ": " + str(exc)[:160]})
        (output / "result.json").write_text(
            json.dumps(result, indent=2, sort_keys=True) + "\n")
        raise
    finally:
        bank.close()


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--source", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    result = run(source=args.source, output=args.output,
                 key=os.environ.get("OPENROUTER_API_KEY"))
    print(json.dumps({
        "status": result["status"], "new_calls": result["new_calls"],
        "new_holdout_scores": result.get("new_holdout_scores"),
        "delta_cold": result.get("delta_cold"),
        "delta_placebo": result.get("delta_placebo"),
        "model": result["model"],
    }, sort_keys=True))
    if result["status"] != "completed_real_batched_holdout":
        raise SystemExit(2)


if __name__ == "__main__":
    main()
