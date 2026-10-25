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
import re
from unicodedata import normalize

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
        # Journal.append() verifies the entire SHA chain before writing.
        # Asking journal.events() for the length first redundantly verifies
        # every historical event a second time on *every* new observation.
        count = self.journal.db.execute(
            "SELECT COUNT(*) FROM attempts").fetchone()[0]
        event = {"schema": SCHEMA, "kind": kind, "data": data,
                 "objective": "lab026", "iteration": int(count) + 1}
        return self.journal.append(event)

    def lessons(self, strategy=None, domain=None):
        found = []
        for record in self.journal.events():
            if record.get("schema") != SCHEMA or record.get("kind") not in ("lesson", "trial", "selection", "inference", "feedback", "research"):
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

    def record_research(self, receipt):
        """Append bounded unverified public web evidence to the SAME SHA ledger."""
        if (not isinstance(receipt, dict) or receipt.get("schema") !=
                "bean.native.web_research.v1"
                or not isinstance(receipt.get("domain"), str)
                or not isinstance(receipt.get("question"), str)
                or not isinstance(receipt.get("sources"), list)
                or len(receipt["sources"]) > 3
                or any(not isinstance(source, dict)
                       or not isinstance(source.get("url"), str)
                       or not isinstance(source.get("text_sha256"), str)
                       or len(source["text_sha256"]) != 64
                       for source in receipt["sources"])
                or len(canonical(receipt)) > 20000
                or receipt.get("web_facts_independently_verified") is not False):
            raise ValueError("Invalid unverified web research receipt")
        return self._append("research", receipt)

    def record_inference(self, receipt):
        """Append model input/answer with actual provider identity, not reward."""
        if (not isinstance(receipt, dict) or receipt.get("schema") !=
                "bean.native.reasoning.inference.v1"
                or not isinstance(receipt.get("model_id"), str)
                or not receipt["model_id"]
                or not isinstance(receipt.get("answer"), str)
                or (not receipt["answer"] and receipt.get("status") != "failed")
                or (receipt.get("status") == "failed"
                    and (not isinstance(receipt.get("exception_class"), str)
                         or not receipt["exception_class"]))):
            raise ValueError("Invalid model inference evidence")
        return self._append("inference", receipt)

    def record_feedback(self, event):
        """Durably retain both successful and failed host-observed outcomes."""
        if (not isinstance(event, dict)
                or event.get("schema") != "bean.native.reasoning.feedback.v1"
                or event.get("outcome_origin") != "host_reported"
                or not isinstance(event.get("source_refs"), list)
                or not event["source_refs"]
                or not isinstance(event.get("receipt_id"), str)
                or len(event["receipt_id"]) != 64
                or type(event.get("matched")) is not bool):
            raise ValueError("Invalid host feedback evidence")
        known = [row["data"] for row in self.journal.events()
                 if row.get("kind") == "inference"
                 and row["data"].get("receipt_id") == event["receipt_id"]
                 and row["data"].get("purpose") == "selected_strategy_applied"]
        if len(known) != 1:
            raise ValueError("Feedback source inference not found")
        return self._append("feedback", event)

    def record_selection(self, selection):
        """Persist the measured choice, linked to an earlier evaluation receipt."""
        if (selection.get("schema") != "bean.lab026.strategy_choice.v1"
                or selection.get("arm") not in ("cold", "reflection", "skill", "prompt")
                or not isinstance(selection.get("domain"), str)
                or not selection["domain"].strip()):
            raise ValueError("Invalid strategy selection")
        receipts = {
            row["data"].get("receipt_hash") for row in self.journal.events()
            if row.get("kind") == "trial"
        }
        if selection.get("source_trial_hash") not in receipts:
            raise ValueError("Strategy cannot be selected without a recorded trial")
        return self._append("selection", selection)

    def selected_arm(self, domain):
        for row in reversed(self.journal.events()):
            if row.get("kind") == "selection" and row["data"]["domain"] == domain:
                return row["data"]["arm"]
        raise ValueError("No measured strategy selection for domain " + str(domain))

    def close(self):
        self.journal.close()


_TOKENS = re.compile(r"[a-z0-9]+")


def task_lesson_matches(bank, *, strategy, domain, query, limit=3):
    """Rank prior lessons using only task text, without target answers.

    The same deterministic retrieval is used by the BEAN decision packet and
    the task-aware matched evaluator. Neither path gets expected labels.
    """
    terms = set(_TOKENS.findall(query.casefold()))
    matches = []
    for index, item in enumerate(bank.lessons(strategy=strategy, domain=domain)):
        # A lesson learned from a specific Bridge evidence definition is
        # scoped to that concept, not all tasks containing generic words like
        # "sensor" or "inspection". Unscoped procedural lessons keep their
        # existing domain/lexical behavior and can generalize normally.
        scopes = [ref[len("bridge_concept:"):] for ref in item.evidence_refs
                  if ref.startswith("bridge_concept:")]
        if scopes and not any(
            re.search(r"(?<![a-z0-9_])" + re.escape(scope) +
                      r"(?![a-z0-9_])", query.casefold())
            for scope in scopes
        ):
            continue
        overlap = len(terms & set(_TOKENS.findall(item.text.casefold())))
        if overlap:
            matches.append((overlap, index, item))
    matches.sort(key=lambda row: (-row[0], -row[1], row[2].lesson_id))
    return [(score, item) for score, _, item in matches[:limit]]


def question_fingerprint(question):
    """Question identity for contamination checks, excluding hidden answers.

    Normalize Unicode compatibility forms, case and spacing so a changed task
    ID or superficial text variation cannot turn a previously seen question
    into a purported unseen evaluation.
    """
    if not isinstance(question, str) or not question.strip():
        raise ValueError("Question must be nonempty text")
    normalized = " ".join(normalize("NFKC", question).casefold().split())
    return sha256(normalized.encode("utf-8")).hexdigest()


def material_for(bank, arm, domain, *, query=None):
    """Context-only adaptation; unrelated-domain lessons form placebo.

    A task-aware trial uses exactly the retrieval BEAN's decision interface
    uses. Legacy Lab026 experiments without query keep their existing scope.
    """
    if arm == "adaptive":
        return material_for(bank, bank.selected_arm(domain), domain, query=query)
    if arm == "cold":
        return ""
    strategy = "reflection" if arm == "placebo" else {
        "reflection": "reflection", "skill": "skill", "prompt": "prompt"}[arm]
    relevant = bank.lessons(strategy=strategy)
    if arm == "placebo":
        relevant = [x for x in relevant if x.domain != domain]
    else:
        relevant = [x for x in relevant if x.domain == domain]
        if query is not None:
            relevant = [item for _, item in task_lesson_matches(
                bank, strategy=strategy, domain=domain, query=query, limit=3)]
    return "\n".join(x.text for x in relevant[:3])


def run_paired_trial(*, bank, cases, model, judge, arms=ARMS,
                     context_chars=800, replicates=1, task_aware=False):
    """Matched questions, single provider ID, held-out labels owned by judge.

    A model only receives public_question and context. The judge receives
    expected and model output. Independent provenance is NOT assumed.
    """
    if (not cases or type(task_aware) is not bool
            or not 40 <= context_chars <= 12000 or
            not 1 <= replicates <= 20 or len(set(arms)) != len(arms) or
            any(arm not in (*ARMS, "adaptive") for arm in arms)):
        raise ValueError("Invalid trial")
    if model.provider_kind not in ("synthetic_fixture", "real_model") or not model.model_id:
        raise ValueError("Model fingerprint and true provider type required")
    if len({c.task_id for c in cases}) != len(cases):
        raise ValueError("Task identifiers must be distinct")
    # Public question hashes are part of the audit receipt, never expected
    # answers. Duplicate tasks with renamed IDs are not fresh evidence.
    question_hashes = [question_fingerprint(case.public_question) for case in cases]
    if task_aware and len(set(question_hashes)) != len(question_hashes):
        raise ValueError("Task-aware trial contains duplicate public questions")
    records = []
    for repetition in range(replicates):
        for i, case in enumerate(cases):
            order = list(arms)
            shift = (i + repetition) % len(order)
            order = order[shift:] + order[:shift]
            for arm in order:
                context = material_for(
                    bank, arm, case.domain,
                    query=case.public_question if task_aware else None)
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
                    "question_sha256": question_hashes[i],
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
        "question_fingerprint": "NFKC_casefold_whitespace_sha256_v1",
        "context_policy": ("same_task_lexical_retrieval_as_decide_v1"
                           if task_aware else "legacy_domain_first_three"),
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
