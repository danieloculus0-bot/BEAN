"""BEAN Core curiosity-to-skill bridge.

A native GoalCycle curiosity question selects a skill from a host-frozen
catalog. The same BEAN reasoning model writes source; Lab019 generates,
tests, and SHA-journals candidate artifacts. No new model or memory store.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re

from bean.optimization.skill_incubator import incubate_skill, NAME

SCHEMA = "bean.native_skill_catalog.v1"
SKILL_ID = re.compile(r"^[a-z][a-z0-9_:-]{1,63}$")


def load_skill_catalog(path):
    """Load a trusted host-authored curriculum, never paths supplied by goals."""
    config = Path(path).resolve(strict=True)
    raw = config.read_bytes()
    if len(raw) > 50000:
        raise ValueError("skill catalog too large")
    data = json.loads(raw.decode("utf-8"))
    if not isinstance(data, dict) or set(data) != {"schema", "skills"}:
        raise ValueError("invalid skill catalog envelope")
    if data["schema"] != SCHEMA or not isinstance(data["skills"], list):
        raise ValueError("unknown skill catalog")
    if not 1 <= len(data["skills"]) <= 32:
        raise ValueError("skill catalog must contain 1..32 entries")
    skills = {}
    for row in data["skills"]:
        if not isinstance(row, dict) or set(row) != {
                "skill_id", "name", "objective", "training_project", "holdout_project"}:
            raise ValueError("invalid skill entry")
        skill_id, name, objective = row["skill_id"], row["name"], row["objective"]
        if (not isinstance(skill_id, str) or not SKILL_ID.fullmatch(skill_id)
                or not isinstance(name, str) or not NAME.fullmatch(name)
                or not isinstance(objective, str) or not 12 <= len(objective) <= 4000):
            raise ValueError("invalid skill identity or objective")
        if skill_id in skills:
            raise ValueError("duplicate skill ID")
        if not isinstance(row["training_project"], str) or not isinstance(
                row["holdout_project"], str):
            raise ValueError("project paths must be host-authored strings")
        train = (config.parent / row["training_project"]).resolve(strict=True)
        holdout = (config.parent / row["holdout_project"]).resolve(strict=True)
        if train == holdout or not (train / "tests").is_dir() or not (
                holdout / "tests").is_dir():
            raise ValueError("training and holdout require separate test projects")
        skills[skill_id] = {
            "skill_id": skill_id, "name": name,
            "objective": objective, "training_project": train,
            "holdout_project": holdout,
        }
    return {"skills": skills, "sha256": hashlib.sha256(raw).hexdigest()}


class NativeCoreSkillWriter:
    """Use the model BEAN Core already owns, preserving actual provider identity."""

    def __init__(self, model):
        if not callable(getattr(model, "complete", None)):
            raise ValueError("BEAN Core needs an actual configured model")
        self.model = model
        self.model_id = None
        self.provider_kind = None

    def propose(self, task, original, history, iteration):
        from bean.learning.reasoning_service import _model_response

        failures = [
            {"iteration": x["iteration"], "outcome": x["outcome"],
             "training_failure": x.get("failure", "")[:300]}
            for x in history[-8:]
            if x.get("outcome") != "holdout_rejected"
        ]
        prompt = (
            "Produce a COMPLETE importable Python module for a new reusable "
            "BEAN skill. Reply with only source code, no Markdown or prose. "
            "Maintain the function API requested by the objective. "
            "Do not see, edit, or infer independent holdout test cases. "
            "Your previous training errors, if any, are supplied below.\n"
            "Objective: " + task +
            "\nIteration: " + str(iteration) +
            "\nPrior training history: " + json.dumps(failures) +
            "\nPlaceholder module:\n" + original
        )
        result, model_id, kind, _ = _model_response(
            self.model, prompt, "BEAN skill acquisition using Core model")
        self.model_id, self.provider_kind = model_id, kind
        if result.startswith(chr(96) * 3):
            lines = result.splitlines()
            result = "\n".join(lines[1:-1]).strip()
        if not result.strip():
            raise ValueError("empty model-created skill")
        return result.strip() + "\n"


def make_native_skill_experiment(core, *, catalog, journal_path, output,
                                 fallback=None, attempts=10):
    """Register a GoalCycle-compatible curiosity skill handler.

    Catalog is host-controlled. A goal can select a skill ID but cannot write
    paths, model names, executable test sources or credential arguments.
    """
    if not isinstance(catalog, dict) or not catalog.get("skills"):
        raise ValueError("validated skill catalog is required")
    if type(attempts) is not int or not 1 <= attempts <= 25:
        raise ValueError("invalid skill proposal budget")
    if fallback is not None and not callable(fallback):
        raise ValueError("fallback must be a previously registered action")

    def run_experiment(goal):
        detail = goal.get("action_detail")
        if not isinstance(detail, dict):
            return {"status": "unknown", "reason": "invalid_experiment_detail"}
        if detail.get("capability") != "native_skill_incubator":
            return (fallback(goal) if fallback else {
                "status": "unknown", "reason": "unsupported_experiment_capability"})
        if set(detail) - {"capability", "skill_id", "learning_context"}:
            return {"status": "unknown", "reason": "untrusted_skill_arguments"}
        skill_id = detail.get("skill_id")
        if not isinstance(skill_id, str) or skill_id not in catalog["skills"]:
            return {"status": "unknown", "reason": "skill_not_in_host_catalog"}
        if getattr(core, "model", None) is None:
            return {"status": "unverified", "reason": "no_live_core_model"}
        skill = catalog["skills"][skill_id]
        writer = NativeCoreSkillWriter(core.model)
        report = incubate_skill(
            project=skill["training_project"], holdout_project=skill["holdout_project"],
            name=skill["name"], task=skill["objective"],
            journal_path=journal_path, output=output, provider=writer,
            attempts=attempts)
        passed = report["skill_promotion_ready"]
        return {
            "status": "verified" if passed else "unverified",
            "schema": "bean.native_skill_experiment.v1",
            "skill_id": skill_id, "skill_name": skill["name"],
            "catalog_sha256": catalog["sha256"],
            "objective_sha256": report["objective"],
            "candidate_sha256": report.get("accepted_source"),
            "training_tests_sha256": report["tests_sha256"],
            "holdout_tests_sha256": report["holdout_tests_sha256"],
            "training_test_count": report.get("tests_passed"),
            "holdout_test_count": report.get("holdout_tests_passed"),
            "author_model": writer.model_id,
            "author_provider": writer.provider_kind,
            "created_executable_code": bool(report.get("skill_newly_created")),
            "source_archived_and_sha_journaled": passed,
            "installed_into_core": False,
            "model_weights_trained": False,
            "independent_outcome_verified": False,
            "skill_promotion_ready": passed,
            "incubation_status": report["status"],
            "evaluation_scope": "separate_host_authored_holdout_not_peer_benchmark",
        }
    return run_experiment


def propose_skill_from_curiosity(core, *, catalog, session_uuid):
    """Let BEAN's OWN configured model select a skill worth learning.

    Source questions come from the existing Core curiosity table. Available
    skill objectives and withheld tests are host-owned; the model chooses only
    IDs. GoalStateEngine stores the decision using its existing dedup and
    GoalCycle runs it on subsequent ticks. No self-generated Python runs here.
    """
    from bean.cognition.goal_state import GoalStateEngine
    from bean.memory.store import get_store
    from bean.learning.reasoning_service import _model_response

    if not isinstance(catalog, dict) or not isinstance(catalog.get("skills"), dict):
        raise ValueError("validated skill catalog required")
    if not isinstance(session_uuid, str) or not session_uuid:
        raise ValueError("session ID required")
    goals = GoalStateEngine()
    store = get_store()
    questions = [dict(row) for row in store.fetchall(
        "SELECT id,question FROM curiosity WHERE status='open' "
        "ORDER BY id DESC LIMIT 8")]
    if not questions:
        return {"status": "n/a", "reason": "no_open_curiosity"}
    # The existing SQLite history prevents repeatedly offering the model a
    # skill it has already attempted or queued, across sessions and restarts.
    existing = store.fetchall(
        "SELECT action_detail FROM cognition_goal_proposals "
        "WHERE action_type='run_experiment' "
        "AND goal_state='investigate_open_question'")
    used = set()
    for row in existing:
        try:
            detail = json.loads(row["action_detail"] or "null")
        except (ValueError, TypeError):
            continue
        if isinstance(detail, dict) and detail.get("capability") == "native_skill_incubator":
            used.add(detail.get("skill_id"))
    available = [item for key, item in sorted(catalog["skills"].items())
                 if key not in used]
    if not available:
        return {"status": "n/a", "reason": "no_unattempted_skills"}
    if getattr(core, "model", None) is None:
        return {"status": "unverified", "reason": "no_live_core_model"}

    # Keep the model's context bounded; do not give it withheld labels, test
    # source, paths or any capability beyond choosing a catalogued ID.
    choices = [{"skill_id": x["skill_id"], "objective": x["objective"][:180]}
               for x in available[:12]]
    queries = [{"question_id": q["id"], "question": q["question"][:250]}
               for q in questions if isinstance(q["question"], str)]
    if not queries:
        return {"status": "n/a", "reason": "no_valid_curiosity"}
    prompt = (
        "You are BEAN investigating unresolved questions from your OWN "
        "persistent curiosity memory. Choose at most one new skill whose "
        "purpose helps investigate one of these questions. Use your "
        "judgment; abstain if unrelated. Reply with ONLY a JSON object "
        "containing exactly skill_id and question_id. On abstention return "
        '{"skill_id":null,"question_id":null}.\n'
        "Unresolved questions: " + json.dumps(queries) + "\n"
        "Available independent skill objectives: " + json.dumps(choices)
    )
    try:
        response, model_id, provider_kind, _ = _model_response(
            core.model, prompt, "BEAN native curiosity and skill choice")
        if response.startswith(chr(96) * 3):
            response = "\n".join(response.splitlines()[1:-1]).strip()
        choice = json.loads(response)
    except (ValueError, RuntimeError, TypeError, KeyError):
        return {"status": "unverified", "reason": "invalid_model_choice"}
    if not isinstance(choice, dict) or set(choice) != {"skill_id", "question_id"}:
        return {"status": "unverified", "reason": "invalid_model_choice"}
    if choice["skill_id"] is None and choice["question_id"] is None:
        return {"status": "n/a", "reason": "model_abstained",
                "model_id": model_id, "provider": provider_kind}
    if (not isinstance(choice["skill_id"], str)
            or choice["skill_id"] not in {x["skill_id"] for x in choices}
            or type(choice["question_id"]) is not int
            or choice["question_id"] not in {q["question_id"] for q in queries}):
        return {"status": "unverified", "reason": "untrusted_model_selection"}
    selected_question = next(
        q for q in questions if q["id"] == choice["question_id"])
    generated = {
        "id": selected_question["id"], "question": selected_question["question"],
        "context": {"schema": "bean.cognition.skill_question.v1",
                    "skill_id": choice["skill_id"]}}
    proposals = goals.propose(session_uuid, [], [generated])
    return {
        "status": "proposed" if proposals else "n/a",
        "reason": "native_model_selected_skill" if proposals else "already_proposed",
        "proposal_id": proposals[0].proposal_id if proposals else None,
        "skill_id": choice["skill_id"],
        "question_id": choice["question_id"],
        "model_id": model_id, "provider": provider_kind,
        "catalog_sha256": catalog["sha256"],
        "selection_is_self_directed_but_catalog_host_authored": True,
        "skill_success_unverified_until_goal_executed": True}
