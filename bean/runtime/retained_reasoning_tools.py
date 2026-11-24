"""Make already implemented native reasoning skills callable in GoalCycle.

The ExperienceBank remains authoritative. No model-authored source is imported,
no external model is authorized, and provisional digital policies do not gain
hardware or external-action permissions.
"""
from hashlib import sha256

from bean.optimization.autodev import canonical


def list_policies(core, *, domain, limit=10):
    """Discover applicable measured policies by domain, not opaque IDs."""
    if not isinstance(domain, str) or not domain.strip() or len(domain) > 100:
        raise ValueError("domain required")
    if type(limit) is not int or not 1 <= limit <= 20:
        raise ValueError("limit must be 1..20")
    matches = []
    for event in reversed(core.bank.journal.events()):
        if event["kind"] != "trial":
            continue
        row = event["data"]
        if row.get("domain") != domain.strip().casefold():
            continue
        decision = row.get("decision")
        if not isinstance(decision, dict):
            continue
        experiment = row.get("experiment")
        if experiment == "bean.native.active_hypothesis.v1":
            if decision.get("status") != "provisional_rule" or not decision.get("selected_rule"):
                continue
            records = decision.get("records") or []
            if not records:
                continue
            dimensions = len(records[0]["sensors"])
            kind = "hypothesis"
            policy = decision["selected_rule"]
        elif experiment == "bean.native.discovered_transfer.v1":
            if decision.get("selected") not in ("source_rule", "stay_0"):
                continue
            dimensions = decision["sensor_dimensions"]
            kind = "transfer"
            policy = decision["selected"]
        else:
            continue
        matches.append({"receipt_id": sha256(canonical(row)).hexdigest(),
                        "kind": kind, "domain": row["domain"],
                        "sensor_dimensions": dimensions, "policy": policy,
                        "task_ref": row.get("task_ref"),
                        "source_ref": row.get("source_ref"),
                        "independent_validation": False})
        if len(matches) >= limit:
            break
    return {"policies": matches, "count": len(matches)}


def register_retained_reasoning(orchestrator):
    """Expose actual existing implementations, not a second skill ledger."""
    core = orchestrator.core

    def automatic(args, task_ref):
        return core.reason_auto(domain=args["domain"], task_ref=task_ref,
                                query=args["query"], allow_provider=False)

    def strategy(args, task_ref):
        return core.decide(domain=args["domain"], task_ref=task_ref,
                           query=args["query"])

    def discover(args, task_ref):
        return list_policies(core, **args)

    def apply(args, task_ref):
        if set(args) != {"kind", "receipt_id", "sensors"}:
            raise ValueError("kind, receipt_id and sensors required")
        if args["kind"] == "hypothesis":
            return core.use_discovered_analogy(
                receipt_id=args["receipt_id"], sensors=args["sensors"])
        if args["kind"] == "transfer":
            return core.use_tested_transfer(
                transfer_receipt_id=args["receipt_id"], sensors=args["sensors"])
        raise ValueError("unrecognized retained policy kind")

    # Recover the actual Hyperon/Omega-inspired implementation from PR #536.
    from bean.learning.relational_grounding import infer_relations
    from bean.cognition.typed_relations import TypedRelations
    from bean.memory.focused_recall import recall_focused_claims
    from bean.memory.store import get_store

    orchestrator.register("infer_relations",
        "Join supplied evidence-linked triples with shared variables: "
        "{facts:[[subject,predicate,object,evidence_id]],patterns:[[s,p,o]],"
        "conclusion:[s,p,o]}; variables start with ?; returns grounded inferences",
        lambda args, task_ref: infer_relations(**args))
    orchestrator.register("query_world_relations",
        "Retrieve source-linked canonical world relations and transitive proofs: "
        "{subject:str,predicate:is_a|part_of|located_in|related_to,target?:str,max_hops?:int}; "
        "unknown and contested evidence must remain visible",
        lambda args, task_ref: TypedRelations().query(**args))
    orchestrator.register("focused_world_memory",
        "Retrieve relevant persistent claims with prior revision and source evidence: "
        "{query:str,limit?:int}",
        lambda args, task_ref: {"claims": recall_focused_claims(get_store()._conn(), **args),
                                "world_truth_verified": False})

    orchestrator.register("reason_auto",
        "BEAN symbolic reasoning then existing local inference if available: {domain:str,query:str}; no external provider authorization",
        automatic)
    orchestrator.register("retained_strategy",
        "Select BEAN's existing evidence-linked lesson strategy: {domain:str,query:str}",
        strategy)
    orchestrator.register("discover_retained_policies",
        "Find measured numeric policies in durable journal: {domain:str,limit?:int}; returns policies with receipt_id,kind,sensor_dimensions",
        discover)
    orchestrator.register("apply_retained_policy",
        "Replay a discovered digital policy on a compatible numeric observation: {kind:str,receipt_id:str,sensors:[numbers]}; provisional action only",
        apply)
