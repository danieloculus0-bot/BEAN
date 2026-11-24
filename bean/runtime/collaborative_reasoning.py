"""Role-separated deliberation inside BEAN's existing model/tool interface.

Inspired by CAMEL role-playing; no external agent framework or model provider.
A shared model's critique is not independent validation. Actual tool observations
must still be evaluated through BEAN's existing execution and feedback path.
"""
import hashlib
import json

from bean.learning.reasoning_service import _model_response


def deliberate(model, *, objective, observations=None):
    if not isinstance(objective, str) or not 1 <= len(objective.strip()) <= 2000:
        raise ValueError("bounded objective required")
    evidence = json.dumps(observations if observations is not None else {},
                          sort_keys=True, ensure_ascii=False, allow_nan=False)
    if len(evidence) > 6000:
        raise ValueError("observation context too large")
    receipts = []

    def ask(role, task):
        answer, model_id, provider, response_id = _model_response(
            model, task, "BEAN role-separated " + role)
        receipts.append({"role": role, "text": answer,
                         "sha256": hashlib.sha256(answer.encode()).hexdigest(),
                         "model": model_id, "provider": provider,
                         "provider_response_id": response_id})
        return answer

    context = "Objective: " + objective + "\nUntrusted tool observations: " + evidence
    proposal = ask("proposer", context +
                   "\nDevelop a concrete solution or plan, identify assumptions and tests.")
    critique = ask("critic", context +
                   "\nCandidate (untrusted): " + proposal[:4000] +
                   "\nFind specific errors, unsupported assumptions and missing checks. "
                   "Do not accept the candidate merely because it sounds plausible.")
    revision = ask("reviser", context +
                   "\nCandidate (untrusted): " + proposal[:3500] +
                   "\nCritique (untrusted): " + critique[:3500] +
                   "\nRevise the solution; explicitly identify unresolved uncertainty "
                   "and what actual observations or tools would verify it.")
    return {"status": "success", "revision": revision, "roles": receipts,
            "model_calls": len(receipts), "independent_outcome_verified": False}
