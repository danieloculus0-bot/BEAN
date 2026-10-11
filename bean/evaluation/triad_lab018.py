"""Lab 018: symmetric, contradictory and complementary three-path learning test.

Research-only synthetic experiment. Agent names A/B/C are three separate
policy states, NOT three concurrent LLM processes or live ChatGPT threads.
No held-out labels reach a learner. Each peer receives identical training
examples, inspection opportunity and evaluation budget. Their initial priors
differ; roles rotate instead of conveying different authority.

The fixture has two tests: the exact same never-trained-on fixed panel at
every round, and independently seeded unseen panels at each round. Only
separate training feedback may update a policy. Record frozen counterparts.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
from dataclasses import dataclass, field
from pathlib import Path

SCHEMA = "bean.triad-learning.lab018.v1"
FEATURES = ("evidence", "replication", "provenance", "risk",
            "regression", "complexity", "novelty")
ROLES = ("selector", "builder", "skeptic")
PRIORS = (
    (1.40, 0.35, 0.80, -0.25, -0.10, -0.10, 0.40),
    (0.50, 1.35, 0.25, -0.85, -0.95, -0.30, 0.15),
    (0.75, 0.20, 1.20, -1.20, -0.60, -0.70, 0.05),
)
TRUE_WEIGHTS = (1.95, 1.50, 1.10, -1.70, -1.85, -0.65, 0.30)
SHIFT_WEIGHTS = (2.10, 1.65, -1.05, -1.80, -2.05, -0.65, 0.25)
BIAS = 0.30
TRAIN_N = 144
TEST_N = 140
ROUNDS = 7  # round 0: no learning, rounds 1–6: new train updates


def stable_seed(kind: str, round_number: int, shift: bool) -> int:
    raw = f"lab018:{kind}:{round_number}:{int(shift)}".encode("utf-8")
    return int(hashlib.sha256(raw).hexdigest()[:15], 16)


def sigmoid(z: float) -> float:
    if z >= 0:
        return 1.0 / (1.0 + math.exp(-z))
    e = math.exp(z)
    return e / (1.0 + e)


def make_cases(kind: str, round_number: int, n: int, *, shift: bool) -> tuple[dict, ...]:
    """Keep truth outside the agent input; generator is evaluator-owned."""
    rng = random.Random(stable_seed(kind, round_number, shift))
    truth_weights = SHIFT_WEIGHTS if shift else TRUE_WEIGHTS
    cases = []
    for i in range(n):
        x = (
            rng.uniform(-1.0, 1.0),
            rng.uniform(-1.0, 1.0),
            rng.uniform(-1.0, 1.0),
            rng.uniform(0.0, 1.0),
            rng.uniform(0.0, 1.0),
            rng.uniform(0.0, 1.0),
            rng.uniform(-1.0, 1.0),
        )
        utility = BIAS + sum(a * b for a, b in zip(x, truth_weights))
        utility += rng.gauss(0, 0.22)
        cases.append({"case_id": f"{kind}:{round_number}:{i}",
                      "features": x, "truth": int(utility > 0),
                      "shift": shift})
    return tuple(cases)


def visible(case: dict) -> dict:
    """The peer never receives truth or phase/shift labels."""
    return {"case_id": case["case_id"], "features": tuple(case["features"])}


@dataclass
class Learner:
    name: str
    weights: list[float]
    step: int = 0
    update_digest: list[str] = field(default_factory=list)

    def probability(self, observation: dict) -> float:
        if set(observation) != {"case_id", "features"}:
            raise ValueError("peer observation leaked evaluator-only fields")
        x = observation["features"]
        if len(x) != len(FEATURES):
            raise ValueError("invalid feature count")
        return sigmoid(BIAS + sum(w * z for w, z in zip(self.weights, x)))

    def learn(self, training: tuple[dict, ...], *, rate: float = .12) -> None:
        """Verified training feedback is delivered only after fresh testing."""
        # Each peer gets exactly the same training truth labels.
        if not training or not 0 < rate <= 1:
            raise ValueError("training observations and bounded rate required")
        prior = tuple(self.weights)
        for case in training:
            pred = self.probability(visible(case))
            residual = case["truth"] - pred
            self.weights = [max(-4.0, min(4.0, w + rate * residual * feature))
                            for w, feature in zip(self.weights, case["features"])]
        self.step += 1
        receipt = {"name": self.name, "step": self.step,
                   "prior": prior, "after": self.weights,
                   "trained_on": [case["case_id"] for case in training]}
        self.update_digest.append(hashlib.sha256(json.dumps(
            receipt, sort_keys=True, separators=(",", ":")).encode()).hexdigest())


def score(learner: Learner, cases: tuple[dict, ...]) -> dict:
    total = len(cases)
    predictions = [learner.probability(visible(case)) for case in cases]
    labels = [case["truth"] for case in cases]
    correct = sum((p >= .5) == bool(y) for p, y in zip(predictions, labels))
    brier = sum((p-y)**2 for p, y in zip(predictions, labels)) / total
    positive = sum(labels)
    predicted_positive = sum(p >= .5 for p in predictions)
    true_pos = sum(p >= .5 and bool(y) for p, y in zip(predictions, labels))
    return {"accuracy": round(correct/total, 6),
            "correct": correct, "n": total, "brier": round(brier, 6),
            "precision": round(true_pos / predicted_positive, 6) if predicted_positive else None,
            "recall": round(true_pos / positive, 6) if positive else None}


def claim(learner: Learner, case: dict, role: str) -> dict:
    obs = visible(case)
    p = learner.probability(obs)
    xs = obs["features"]
    signals = [w*x for w, x in zip(learner.weights, xs)]
    helps = [(FEATURES[i], round(v, 5)) for i, v in enumerate(signals) if v > 0]
    harms = [(FEATURES[i], round(v, 5)) for i, v in enumerate(signals) if v < 0]
    supporting = sorted(helps if p >= .5 else harms,
                        key=lambda v: (-abs(v[1]), v[0]))
    contradicting = sorted(harms if p >= .5 else helps,
                           key=lambda v: (-abs(v[1]), v[0]))
    return {
        "peer": learner.name, "role": role, "case_id": case["case_id"],
        "claim": "improvement_likely" if p >= .5 else "regression_likely",
        "counterclaim": "regression_possible" if p >= .5 else "improvement_possible",
        "estimated_probability": round(p, 6),
        "supporting_feature": supporting[0][0] if supporting else None,
        "contradicting_feature": contradicting[0][0] if contradicting else None,
        "complementary_check": (
            "Independent test of " + (contradicting[0][0] if contradicting
                                     else "unresolved evidence") +
            " before proposing a production change"),
        "verified_fact": False,
        "test_result_status": "not_run",
    }


def peer_distinctions(peers: list[Learner], cases: tuple[dict, ...]) -> dict:
    names = [p.name for p in peers]
    agreements = {}
    minority_correct = {name: 0 for name in names}
    unanimous_wrong = 0
    conflict_count = 0
    all_different_probs = 0
    for i, left in enumerate(peers):
        for right in peers[i+1:]:
            agreements[f"{left.name}-{right.name}"] = 0
    for case in cases:
        obs = visible(case)
        votes = {p.name: int(p.probability(obs) >= .5) for p in peers}
        if len({round(p.probability(obs), 4) for p in peers}) == len(peers):
            all_different_probs += 1
        unique = set(votes.values())
        if len(unique) > 1:
            conflict_count += 1
            for name, vote in votes.items():
                if list(votes.values()).count(vote) == 1 and vote == case["truth"]:
                    minority_correct[name] += 1
        elif list(votes.values())[0] != case["truth"]:
            unanimous_wrong += 1
        for i, left in enumerate(names):
            for right in names[i+1:]:
                if votes[left] == votes[right]:
                    agreements[f"{left}-{right}"] += 1
    n = len(cases)
    return {"disagreement_rate": round(conflict_count/n, 6),
            "unanimous_wrong_rate": round(unanimous_wrong/n, 6),
            "unique_correct_dissent": minority_correct,
            "pair_agreement": {k: round(v/n, 6) for k, v in agreements.items()},
            "distinct_probability_rate": round(all_different_probs/n, 6)}


def run() -> dict:
    names = ("A", "B", "C")
    peers = [Learner(name, list(prior)) for name, prior in zip(names, PRIORS)]
    baselines = [Learner(name, list(prior)) for name, prior in zip(names, PRIORS)]
    # The immutable common panel has never been in training or fresh test panels.
    fixed = make_cases("FIXED_NEVER_TRAIN", 0, TEST_N, shift=False)
    rounds = []
    seen_train = set()
    seen_holdout = {x["case_id"] for x in fixed}
    all_train_ids = []
    all_test_ids = [x["case_id"] for x in fixed]
    for i in range(ROUNDS):
        shifted = i >= 4
        fresh = make_cases("FRESH_NEVER_TRAIN", i, TEST_N, shift=shifted)
        assert seen_holdout.isdisjoint({x["case_id"] for x in fresh})
        seen_holdout.update(x["case_id"] for x in fresh)
        all_test_ids += [x["case_id"] for x in fresh]
        roles = {names[idx]: ROLES[(idx + i) % len(ROLES)] for idx in range(3)}
        peer_scores = {}
        for peer, frozen in zip(peers, baselines):
            peer_scores[peer.name] = {
                "fixed": score(peer, fixed), "fresh": score(peer, fresh),
                "frozen_fixed": score(frozen, fixed), "frozen_fresh": score(frozen, fresh),
                "weights": [round(w, 5) for w in peer.weights],
                "learning_steps_completed": peer.step,
            }
        disputes = peer_distinctions(peers, fresh)
        # Equal-footing pro, contra, and complementary hypotheses for the SAME
        # five cases at each round. Results are not supplied to the learners.
        claims = [claim(peer, case, roles[peer.name])
                  for case in fresh[:5] for peer in peers]
        rounds.append({
            "iteration": i, "heldout_distribution_shifted": shifted,
            "same_fixed_panel_sha256": hashlib.sha256(json.dumps(
                [(x["case_id"], x["features"]) for x in fixed],
                sort_keys=True).encode()).hexdigest(),
            "fresh_panel_sha256": hashlib.sha256(json.dumps(
                [(x["case_id"], x["features"]) for x in fresh],
                sort_keys=True).encode()).hexdigest(),
            "roles": roles, "training_cases_seen_before_test": len(seen_train),
            "test_cases": TEST_N,
            "scores": peer_scores, "distinction": disputes,
            "claims": claims,
        })
        if i < ROUNDS - 1:
            # Update ONLY on separate labelled training examples, never on the
            # repeated fixed panel or the fresh holdout evaluated above.
            training = make_cases("TRAIN_ONLY", i, TRAIN_N, shift=shifted)
            train_ids = {x["case_id"] for x in training}
            assert not train_ids.intersection(seen_holdout | seen_train)
            seen_train.update(train_ids)
            all_train_ids.extend(sorted(train_ids))
            for peer in peers:
                peer.learn(training)
    assert not set(all_test_ids).intersection(all_train_ids)
    for i, peer in enumerate(peers):
        assert peer.step == ROUNDS - 1
        assert baselines[i].step == 0
    changes = {}
    for name in names:
        first, last = rounds[0]["scores"][name], rounds[-1]["scores"][name]
        changes[name] = {
            "fixed_accuracy_change": round(last["fixed"]["accuracy"]-first["fixed"]["accuracy"], 6),
            "fixed_brier_change": round(last["fixed"]["brier"]-first["fixed"]["brier"], 6),
            # This is a time-varying benchmark, not a controlled improvement
            # delta. Relative frozen-matched score separates some drift effects.
            "last_fresh_vs_frozen_accuracy": round(
                last["fresh"]["accuracy"]-last["frozen_fresh"]["accuracy"], 6),
            "last_fresh_vs_frozen_brier": round(
                last["fresh"]["brier"]-last["frozen_fresh"]["brier"], 6),
            "weight_change": [round(last["weights"][j]-first["weights"][j], 6)
                              for j in range(len(FEATURES))],
        }
    return {
        "schema": SCHEMA,
        "synthetic_only": True,
        "distinct_claims_not_distinct_ai_models": True,
        "paths": {"A": "independent candidate selection",
                  "B": "independent code draft and review",
                  "C": "independent falsification and longitudinal evaluation"},
        "equal_feedback_budget_per_peer": TRAIN_N*(ROUNDS-1),
        "fixed_panel_examples": TEST_N,
        "fresh_examples_per_round": TEST_N,
        "rounds": rounds, "learned_vs_frozen_summary": changes,
        "train_test_disjoint": True,
        "fixed_panel_never_used_for_training": True,
        "no_self_approval": True,
        "limitations": [
            "The three learners are deterministic synthetic weight models, NOT independent LLM agents.",
            "Role names rotate and no model receives extra information or authority.",
            "Their priors differ by design; independent dissent does not prove agentic identity.",
            "All receive the same labelled training batch each round, not unseen evaluation truth.",
            "Repeated fixed holdout is a diagnostic, never used for candidate or weight selection.",
            "Fresh shifted panels measure transfer but are generated from the same synthetic family.",
            "A producer able to inspect this evaluator could overfit; stronger sealed tests remain necessary.",
            "No model-generated patch execution, production mutation, hardware or real-world training."
        ]
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=Path("bean-lab018-results.json"))
    args = ap.parse_args()
    report = run()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    for name, delta in report["learned_vs_frozen_summary"].items():
        print(name, json.dumps(delta, sort_keys=True))
    compact = [{"iteration": item["iteration"], "shifted": item["heldout_distribution_shifted"],
                "disagreement": item["distinction"]["disagreement_rate"],
                "unanimous_wrong": item["distinction"]["unanimous_wrong_rate"],
                "scores": {name: {"fixed": item["scores"][name]["fixed"]["accuracy"],
                                  "fresh": item["scores"][name]["fresh"]["accuracy"],
                                  "frozen_fresh": item["scores"][name]["frozen_fresh"]["accuracy"],
                                  "fresh_brier": item["scores"][name]["fresh"]["brier"]}
                           for name in ("A", "B", "C")}}
               for item in report["rounds"]]
    print("ITERATIVE_TIMELINE=" + json.dumps(compact, sort_keys=True))
    print("TRIAD_TESTS_RECORDED_NOT_PRODUCTION_APPROVED")
    print(f"iterations={len(report['rounds'])} peers=3 holdout_disjoint={report['train_test_disjoint']}")


if __name__ == "__main__":
    main()
