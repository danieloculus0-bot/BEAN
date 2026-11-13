"""Run bounded, scored digital tasks inside BEAN's existing GitHub Core lifecycle.

This is an executable *synthetic* learning experiment, not evidence of AGI.
World is a fixed public benchmark. The truth labels are never given to the
candidate during rule discovery, and blind evaluation happens after reopening
the existing SHA-journal SQLite database. No network/model/device calls.
"""
from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path

from bean.evaluation.active_abstraction_benchmark import World
from bean.learning.active_hypothesis import act, discover
from bean.learning.reasoning_service import NativeReasoningService

SCHEMA = "bean.github.digital_feedback.v1"
EXPERIMENT = "bean.github.digital_feedback.v1"
FAMILIES = ("channel", "difference", "parity")
TRAIN = tuple(str(100 + i) for i in range(40))
VALIDATE = tuple(str(1000 + i) for i in range(8))
BLIND = tuple(str(50000 + i) for i in range(48))
BUDGET = 12


def _hash(value):
    return sha256(json.dumps(
        value, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")).hexdigest()


def _prior_evaluations(service):
    return [
        item["data"] for item in service.bank.journal.events()
        if item["kind"] == "trial"
        and item["data"].get("experiment") == EXPERIMENT
    ]


def _action(service, receipt_id, sensors):
    answer = service.use_discovered_analogy(
        receipt_id=receipt_id, sensors=sensors)
    return answer.get("action") if answer["status"] == "provisional_action" else None


def run_scored_digital_cycle(db_path: Path, *, generation: int,
                             source_sha: str = "local-validation") -> dict:
    """Observe new worlds, learn from reward and blindly score AFTER reopening.

    Cases, environments and source SHA are identified in durable journal
    receipts. Once recorded a generation cannot earn credit a second time.
    Scores are measured by our deterministic host fixture, not an external
    assessor; they remain explicitly synthetic and non-independent of the repo.
    """
    if type(generation) is not int or not 1 <= generation <= 99999:
        raise ValueError("generation must be 1..99999")
    if not isinstance(source_sha, str) or not source_sha or len(source_sha) > 64:
        raise ValueError("invalid source revision")

    service = NativeReasoningService(db_path, model=None)
    try:
        earlier = _prior_evaluations(service)
        matching = [item for item in earlier
                    if item.get("generation") == generation]
        # Interrupted runs may have committed one or two scored families.
        # Validate those immutable records before resuming only the missing
        # families. Never rewrite or earn a second credit for a scored family.
        recorded = {}
        for item in matching:
            family = item.get("family")
            if family not in FAMILIES or family in recorded:
                raise ValueError("duplicate or unknown digital learning family")
            if item.get("source_sha") != source_sha:
                raise ValueError("digital generation source revision conflict")
            if (item.get("evaluation_sha256") != _hash({
                    k: v for k, v in item.items()
                    if k != "evaluation_sha256"})
                    or item.get("world_id") != (
                        100000 + generation * 100 + FAMILIES.index(family))
                    or item.get("scored_cases") != len(BLIND)
                    or [case.get("case_id") for case in item.get(
                        "case_level_evidence", [])] != list(BLIND)):
                raise ValueError("invalid existing digital learning receipt")
            recorded[family] = item
        if len(recorded) == len(FAMILIES):
            return _summary(
                [recorded[family] for family in FAMILIES],
                new_evaluation=False)
        previous = {
            item["family"]: item for item in earlier
            if item.get("generation") == generation - 1
        }
        preparation = []
        for family_index, family in enumerate(FAMILIES):
            if family in recorded:
                continue
            world_id = 100000 + generation * 100 + family_index
            world = World(world_id, family)
            task = f"g{generation:05d}-{family}"
            # The next generation must actually consult durable reasoning
            # evidence. A previous failed hypothesis widens the compositional
            # grammar; an accepted or failed parent is revised using new host
            # observations rather than merely scored after the fact.
            parent = previous.get(family)
            expanded = bool(parent and (
                parent.get("learning_status") == "abstain"
                or parent.get("hypothesis_grammar_expanded") is True))
            # Generation-qualified IDs are genuinely unseen by the previous
            # revision ancestry, including its unrewarded observations.
            # The public blind pool remains separate from either arm.
            training = (TRAIN if generation == 1 else tuple(
                str(generation * 1000000 + int(pid)) for pid in TRAIN))
            validation = (VALIDATE if generation == 1 else tuple(
                str(generation * 1000000 + int(pid)) for pid in VALIDATE))
            arguments = dict(
                domain="synthetic_numeric_control", task_ref=task,
                source_ref=f"bean-benchmark:World:{world_id}:{family}",
                probe_ids=training, validation_probe_ids=validation,
                observe=world.observe, reward=world.feedback,
                budget=BUDGET, method="disagreement", seed=world_id,
                include_products=expanded)
            if parent is None:
                learner = service.discover_analogy(**arguments)
                strategy = "cold_start_no_prior_receipt"
            else:
                learner = service.revise_discovered_analogy(
                    parent_receipt_id=parent["learning_receipt_id"],
                    **arguments)
                strategy = "revise_prior_rule_from_fresh_feedback"
            # The passive control receives the SAME expanded hypothesis class
            # and reward budget, isolating probe selection from grammar scope.
            passive = discover(
                probe_ids=training, validation_probe_ids=validation,
                observe=world.observe, reward=world.feedback,
                budget=BUDGET, method="passive", seed=world_id,
                include_products=expanded)
            # The memory-ablated candidate does not receive the prior failure
            # or prior policy. Same new-world observations, active strategy,
            # budget and validation. This baseline isolates *the complete
            # memory-conditioned choice*, not the grammar expansion alone.
            ablated = discover(
                probe_ids=training, validation_probe_ids=validation,
                observe=world.observe, reward=world.feedback,
                budget=BUDGET, method="disagreement", seed=world_id)
            # Historical negative control, retained for continuity. Its label
            # offset is NOT assumed to guarantee wrong feedback (audit #333).
            def wrong_feedback(case_id, action, *, _world=world):
                return _world.feedback(str(int(case_id) + 1000000), action)
            shuffled = discover(
                probe_ids=training, validation_probe_ids=validation,
                observe=world.observe, reward=wrong_feedback,
                budget=BUDGET, method="disagreement", seed=world_id,
                include_products=expanded)
            preparation.append((
                family, world, task, learner, passive, shuffled, ablated,
                parent, expanded, strategy, training, validation))
    finally:
        service.close()

    # Recreate the real Core reasoning service: selected actions must be
    # retrieved from its persisted rule receipt, not a Python local variable.
    reopened = NativeReasoningService(db_path, model=None)
    records = [recorded[family] for family in FAMILIES if family in recorded]
    try:
        current = [item for item in _prior_evaluations(reopened)
                   if item.get("generation") == generation]
        if _hash(current) != _hash(matching):
            raise ValueError("digital generation changed during evaluation")
        for (family, world, task, learner, passive, shuffled, ablated,
             parent, expanded, strategy, training, validation) in preparation:
            score = {"candidate": 0, "passive": 0, "shuffled": 0,
                     "memory_ablated": 0, "always_zero": 0}
            abstentions = {"candidate": 0, "passive": 0,
                           "shuffled": 0, "memory_ablated": 0}
            cases = []
            parent_score = 0
            parent_attempted = 0
            for case in BLIND:
                sensors = world.observe(case)
                truth = world.correct_action(case)  # evaluator only
                choices = {
                    "candidate": _action(reopened, learner["receipt_id"], sensors),
                    "passive": (act(passive["selected_rule"], sensors)
                                if passive["selected_rule"] is not None else None),
                    "shuffled": (act(shuffled["selected_rule"], sensors)
                                 if shuffled["selected_rule"] is not None else None),
                    "memory_ablated": (act(ablated["selected_rule"], sensors)
                                       if ablated["selected_rule"] is not None else None),
                    "always_zero": 0,
                }
                for arm, action in choices.items():
                    score[arm] += int(action == truth)
                    if arm in abstentions and action is None:
                        abstentions[arm] += 1
                if parent is not None:
                    transfer = _action(
                        reopened, parent["learning_receipt_id"], sensors)
                    parent_score += int(transfer == truth)
                    parent_attempted += int(transfer is not None)
                cases.append({
                    "case_id": case,
                    "sensors_sha256": _hash(sensors),
                    "truth": truth, "actions": choices,
                    "correct": {arm: action == truth
                                for arm, action in choices.items()},
                })
            receipt = {
                "schema": "bean.adaptive_lab026.v1",
                "evaluation_schema": SCHEMA, "experiment": EXPERIMENT,
                "generation": generation, "source_sha": source_sha,
                "family": family, "task_ref": task, "world_id": world.world_id,
                "task_generator": "bean.evaluation.active_abstraction_benchmark.World",
                "budget_probes": BUDGET,
                "training_ids_sha256": _hash(training),
                "validation_ids_sha256": _hash(validation),
                "learning_strategy": strategy,
                "revision_decision": learner.get("revision_decision"),
                "prior_receipt_used_during_learning": (
                    parent["learning_receipt_id"] if parent else None),
                "hypothesis_grammar_expanded": expanded,
                "grammar_expansion_trigger": (
                    "retained_failed_or_expanded_search" if expanded else None),
                "heldout_ids_sha256": _hash(BLIND),
                "heldout_evaluated_after_service_restart": True,
                "hidden_truth_not_passed_to_candidate": True,
                "benchmark_is_synthetic_public_fixture": True,
                "external_independent_verification": False,
                "correct_sensor_or_rule_supplied": False,
                "model_weights_trained": False,
                "learning_receipt_id": learner["receipt_id"],
                "learning_status": learner["status"],
                "learning_reward_calls": learner["reward_calls"],
                "passive_reward_calls": passive["reward_calls"],
                "shuffled_reward_calls": shuffled["reward_calls"],
                "memory_ablated_reward_calls": ablated["reward_calls"],
                "scored_cases": len(BLIND),
                "correct": score, "abstentions": abstentions,
                "prior_generation_transfer_correct": (
                    parent_score if parent is not None else None),
                "prior_generation_transfer_attempted": (
                    parent_attempted if parent is not None else None),
                "prior_generation_source_receipt": (
                    parent["learning_receipt_id"] if parent is not None else None),
                "case_level_evidence": cases,
            }
            receipt["evaluation_sha256"] = _hash(receipt)
            # Existing typed SHA journal is the sole store. Failures and
            # abstentions are stored just as successes are.
            reopened.bank.record_trial(receipt)
            records.append(receipt)
        return _summary(
            sorted(records, key=lambda row: FAMILIES.index(row["family"])),
            new_evaluation=True)
    finally:
        reopened.close()


def _summary(records, *, new_evaluation):
    return {
        "schema": SCHEMA,
        "generation": records[0]["generation"],
        "source_sha": records[0]["source_sha"],
        "new_evaluation": new_evaluation,
        "families": {
            record["family"]: {
                "correct": record["correct"],
                "abstentions": record["abstentions"],
                "learning_status": record["learning_status"],
                "learning_strategy": record.get("learning_strategy", "historical_unrecorded"),
                "revision_decision": record.get("revision_decision"),
                "hypothesis_grammar_expanded": record.get("hypothesis_grammar_expanded", False),
                "prior_generation_transfer_correct":
                    record["prior_generation_transfer_correct"],
                # Attempted-case coverage is a distinct denominator. A score
                # without it cannot establish transfer success or failure.
                "prior_generation_transfer_attempted":
                    record.get("prior_generation_transfer_attempted"),
                # Missing transfer evidence is not a failed experiment. Keep
                # the numeric field null, and annotate missingness separately.
                "incomplete_fields": {
                    **({"prior_generation_transfer_correct": (
                        "N/A" if record["generation"] == 1 else "Unknown")}
                       if record["prior_generation_transfer_correct"] is None
                       else {}),
                    **({"prior_generation_transfer_attempted": (
                        "N/A" if record["generation"] == 1 else "Unknown")}
                       if record.get("prior_generation_transfer_attempted") is None
                       else {}),
                },
                "evaluation_sha256": record["evaluation_sha256"],
                "learning_receipt_id": record["learning_receipt_id"],
            } for record in records
        },
        "blind_cases_total": sum(record["scored_cases"] for record in records),
        "candidate_correct_total": sum(
            record["correct"]["candidate"] for record in records),
        "passive_correct_total": sum(
            record["correct"]["passive"] for record in records),
        "shuffled_correct_total": sum(
            record["correct"]["shuffled"] for record in records),
        # Legacy checkpoint receipts predate the ablation arm. Missing
        # measurements are unknown, never a fabricated zero score.
        "memory_ablated_correct_total": (
            sum(record["correct"]["memory_ablated"] for record in records)
            if all("memory_ablated" in record["correct"] for record in records)
            else None),
        "always_zero_correct_total": sum(
            record["correct"]["always_zero"] for record in records),
        "source_evidence_sha256": _hash(
            [record["evaluation_sha256"] for record in records]),
        "scope": "synthetic_numeric_control_not_general_intelligence",
        "independently_audited": False,
    }
