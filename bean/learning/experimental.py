"""Experimental adaptive learning: source-grounded nodes and matched trials.

Reuses BEAN's actual hash-chained Autodev Journal. No model weight updates,
external action privileges, or origin-identity mutations. A positive score
from synthetic experiments is NOT evidence of autonomous model learning.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict
from hashlib import sha256
from importlib.util import find_spec
from pathlib import Path
import json

from bean.optimization.autodev import Journal, canonical

SCHEMA = "bean.adaptive_lab026.v1"
ARMS = ("cold", "reflection", "skill", "prompt", "placebo")
NODES = {
    "memory": ("Letta-style persistent history", "bean.memory.store", "existing"),
    "reflection": ("Reflexion-style outcome reflection", "bean.reflection.reflect", "adapter"),
    "skill": ("Voyager-style reusable task skill", "bean.optimization.autodev", "adapter"),
    "prompt": ("GEPA-style candidate prompt search", "bean.optimization.selection", "adapter"),
    "bridge": ("BEAN AI Bridge evidence replay", "bean.integration.evidence_bridge", "adapter"),
    "weights": ("Agent Lightning weight learning", None, "not_implemented"),
    "self_revision": ("Darwin Goedel code trial", "bean.optimization.autodev", "existing_lab"),
}


def assess_nodes(bridge_present=False):
    """Dependency presence, not a synthetic claim of node effectiveness."""
    origin = json.loads((Path(__file__).resolve().parents[2] /
                         "memory/identity/origin_record.json").read_text())
    values = set(origin["core_values"])
    if not {"truth", "evidence", "continuity", "learning from outcomes", "independence"} <= values:
        raise ValueError("BEAN origin compatibility must be checked explicitly")
    report = []
    for name, (inspiration, package, state) in NODES.items():
        present = bool(find_spec(package)) if package else False
        if name == "bridge":
            present = bool(bridge_present)
        report.append({
            "node": name, "inspiration": inspiration, "source_state": state,
            "dependency_present": present,
            "viability": "research_only" if package is None else
                         "source_present_not_benchmarked" if present else "dependency_missing",
            "learning_improvement_verified": False,
            "origin_values_unchanged": True,
        })
    return report


@dataclass(frozen=True)
class Lesson:
    lesson_id: str
    strategy: str
    domain: str
    text: str
    evidence_refs: tuple[str, ...]
    observed_outcome: str

    def __post_init__(self):
        if self.strategy not in {"reflection", "skill", "prompt"}:
            raise ValueError("Unsupported lesson strategy")
        if not all((self.lesson_id, self.domain, self.text, self.observed_outcome)):
            raise ValueError("Incomplete retained lesson")
        if not self.evidence_refs or any(not x for x in self.evidence_refs):
            raise ValueError("Lesson requires original evidence receipts")


@dataclass(frozen=True)
class TrialCase:
    task_id: str
    domain: str
    public_question: str
    expected: str


class ExperienceBank:
    """A typed view over BEAN's already-installed append-only SHA journal."""
    def __init__(self, path):
        self.journal = Journal(path)
        self.lessons()

    def _append(self, kind, data):
        event = {"schema": SCHEMA, "kind": kind, "data": data,
                 "objective": "lab026", "iteration": len(self.journal.events()) + 1}
        return self.journal.append(event)

    def lessons(self, strategy=None, domain=None):
        found = []
        for record in self.journal.events():
            if record.get("schema") != SCHEMA or record.get("kind") not in ("lesson", "trial"):
                raise ValueError("Invalid adaptive journal event type")
            if record["kind"] == "lesson":
                raw = dict(record["data"])
                raw["evidence_refs"] = tuple(raw["evidence_refs"])
                lesson = Lesson(**raw)
                if ((strategy is None or lesson.strategy == strategy)
                        and (domain is None or lesson.domain == domain)):
                    found.append(lesson)
        return found

    def add(self, lesson):
        if not isinstance(lesson, Lesson):
            raise TypeError("Expected typed lesson")
        if lesson.lesson_id in {x.lesson_id for x in self.lessons()}:
            raise ValueError("Duplicate lesson identity")
        return self._append("lesson", asdict(lesson))

    def record_trial(self, receipt):
        if receipt.get("schema") != SCHEMA:
            raise ValueError("Incorrect experiment schema")
        return self._append("trial", receipt)

    def close(self):
        self.journal.close()


def material_for(bank, arm, domain):
    """Context-only adaptation; unrelated-domain lessons form placebo."""
    if arm == "cold":
        return ""
    strategy = "reflection" if arm == "placebo" else {
        "reflection": "reflection", "skill": "skill", "prompt": "prompt"}[arm]
    relevant = bank.lessons(strategy=strategy)
    if arm == "placebo":
        relevant = [x for x in relevant if x.domain != domain]
    else:
        relevant = [x for x in relevant if x.domain == domain]
    return "\n".join(x.text for x in relevant[:3])


def run_paired_trial(*, bank, cases, model, judge, arms=ARMS,
                     context_chars=800, replicates=1):
    """Matched questions, single provider ID, held-out labels owned by judge.

    A model only receives public_question and context. The judge receives
    expected and model output. Independent provenance is NOT assumed.
    """
    if (not cases or not 40 <= context_chars <= 12000 or
            not 1 <= replicates <= 20 or len(set(arms)) != len(arms) or
            any(arm not in ARMS for arm in arms)):
        raise ValueError("Invalid trial")
    if model.provider_kind not in ("synthetic_fixture", "real_model") or not model.model_id:
        raise ValueError("Model fingerprint and true provider type required")
    if len({c.task_id for c in cases}) != len(cases):
        raise ValueError("Task identifiers must be distinct")
    records = []
    for repetition in range(replicates):
        for i, case in enumerate(cases):
            order = list(arms)
            shift = (i + repetition) % len(order)
            order = order[shift:] + order[:shift]
            for arm in order:
                context = material_for(bank, arm, case.domain)
                context = (context[:context_chars].ljust(context_chars)
                           if arm != "cold" else "")
                answer = model.complete(case.public_question, context)
                if not isinstance(answer, str):
                    raise TypeError("Model reply must be text")
                passed = judge(case.expected, answer)
                if type(passed) is not bool:
                    raise TypeError("Evaluator must return actual Boolean verdict")
                records.append({
                    "task_id": case.task_id, "arm": arm, "replicate": repetition,
                    "context_sha256": sha256(context.encode()).hexdigest(),
                    "answer_sha256": sha256(answer.encode()).hexdigest(),
                    "passed": passed,
                })
    counts = {a: sum(x["passed"] for x in records if x["arm"] == a) for a in arms}
    receipt = {
        "schema": SCHEMA, "provider_kind": model.provider_kind,
        "model_id": model.model_id, "arms": list(arms),
        "cases": len(cases), "replicates": replicates,
        "context_chars": context_chars, "scores": counts,
        "records": records, "model_weights_modified": False,
        "independent_evaluation_authenticated": False,
        "promotion": "none",
        "verdict": ("synthetic_fixture_not_learning_proof"
                    if model.provider_kind == "synthetic_fixture"
                    else "needs_external_blind_replication"),
    }
    receipt["receipt_hash"] = sha256(canonical(receipt)).hexdigest()
    receipt["journal_tip"] = bank.record_trial(receipt)
    return receipt
