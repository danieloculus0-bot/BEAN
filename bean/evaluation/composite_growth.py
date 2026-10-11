"""Lab 013: composite synthetic growth, with paired baseline and ablations.

BEAN MemoryStore, EpistemicGuard, TaskEngine and Lab012 mock baseline participate.
Feedback trains ONLY a small sandbox source-reliability policy, not an LLM.
Hidden truth is revealed to the policy's supervisor AFTER the training decision.
Holdout decisions have NO feedback. No real-world output or model promotion.
"""
from __future__ import annotations
import argparse
import json
import random
import tempfile
from dataclasses import dataclass
from pathlib import Path
from statistics import mean
from typing import Optional

from bean.cognition.epistemic_guard import CandidateClaim, EpistemicGuard, EpistemicVerdict
from bean.evaluation.entrance_exam import run_exam
from bean.memory.store import get_store, init_store
from bean.reasoning.mock_llm import MockLLMAdapter
from bean.runtime.task_engine import TaskEngine, TaskSpec

SOURCES = ("dashboard", "telemetry", "inspector")
TRAIN_DOMAINS = ("fabrication", "deliveries", "cooling")
TEST_DOMAINS = ("energy", "maintenance", "inventory")
SCHEMA = """
CREATE TABLE IF NOT EXISTS eval013_feedback (
 id INTEGER PRIMARY KEY, source TEXT NOT NULL,
 correct INTEGER NOT NULL CHECK(correct IN (0,1)),
 phase TEXT NOT NULL CHECK(phase='training')
);
CREATE INDEX IF NOT EXISTS eval013_source ON eval013_feedback(source,id);
"""

@dataclass(frozen=True)
class Observation:
    ref: str
    source: str
    value: Optional[int]
    status: str = "unverified"

@dataclass(frozen=True)
class Episode:
    domain: str
    truth: int
    records: tuple[Observation, ...]
    kind: str

@dataclass(frozen=True)
class Decision:
    answer: Optional[int]  # None signifies unknown; zero is an actual reading
    confidence: float
    source_ref: Optional[str]
    epistemic_status: str = "inference"

class Memory:
    """Dedicated simulated feedback, never BEAN's verified world model."""
    def __init__(self):
        self.db = get_store()
        self.db._conn().executescript(SCHEMA)
        self.db.commit()

    def posterior(self, kind):
        if kind not in SOURCES:
            raise ValueError("unexpected source")
        rows = self.db.fetchall(
            "SELECT correct FROM eval013_feedback WHERE source=? "
            "ORDER BY id DESC LIMIT 48", (kind,)
        )
        return (2 + sum(row["correct"] for row in rows)) / (3 + len(rows)), len(rows)

    def learn_supervised(self, episode):
        # Supervisor-only evaluation; cannot be called on holdouts.
        rows = [(o.source, int(o.value == episode.truth), "training")
                for o in episode.records if o.status == "unverified" and o.value in (0,1)]
        if rows:
            self.db.executemany(
                "INSERT INTO eval013_feedback(source,correct,phase) VALUES (?,?,?)", rows
            )
            self.db.commit()

    def count(self):
        return self.db.fetchone("SELECT COUNT(*) AS n FROM eval013_feedback")["n"]

class FrozenPolicy:
    """Paired no-learning control; first available source is used."""
    def choose(self, records):
        for o in records:
            if o.status == "unverified" and o.value in (0, 1):
                return Decision(o.value, 2 / 3, o.ref)
        return Decision(None, 0.0, None)

class AdaptivePolicy:
    """Bounded beta-posterior source calibration, not new conceptual learning."""
    def __init__(self, memory):
        self.memory = memory

    def choose(self, records):
        options = []
        for o in records:
            if o.status != "unverified" or o.value not in (0, 1):
                continue
            reliability, count = self.memory.posterior(o.source)
            options.append((reliability, count, o))
        if not options:
            return Decision(None, 0.0, None)
        p, _, best = max(options, key=lambda option: (option[0],option[1]))
        if p < 0.64:
            return Decision(None, p, None)
        return Decision(best.value, p, best.ref)

def make_cases(seed, count, phase, drift=False):
    if phase not in ("training", "holdout"):
        raise ValueError("bad phase")
    rng = random.Random(seed)
    domains = TRAIN_DOMAINS if phase == "training" else TEST_DOMAINS
    episodes = []
    for i in range(count):
        truth = rng.randrange(2)
        if i % 23 == 0:
            types = []
            kind = "missing"
        elif i % 29 == 0:
            types = [("dashboard","stale")]
            kind = "stale"
        else:
            types = [("dashboard","unverified")]
            if rng.random() < 0.72:
                types.append(("telemetry","unverified"))
            if rng.random() < 0.34:
                types.append(("inspector","unverified"))
            kind = "routine"
        records = []
        values = set()
        for source, status in types:
            reliabilities = (
                {"dashboard":0.24,"telemetry":0.84,"inspector":0.96}
                if phase == "training" else
                {"dashboard":0.29,"telemetry":0.77,"inspector":0.93}
            )
            p = reliabilities[source]
            if drift and phase == "holdout" and i >= count // 2 and source == "telemetry":
                p = 0.22
            value = truth if rng.random() < p else 1 - truth
            if status == "unverified":
                values.add(value)
            records.append(Observation(f"{phase}-{seed}-{i}-{source}",source,value,status))
        if kind == "routine" and len(values) > 1:
            kind = "conflict"
        episodes.append(Episode(domains[i % len(domains)],truth,tuple(records),kind))
    return episodes

def score(episode, decision):
    sources = {o.ref: o for o in episode.records}
    valid = (
        decision.source_ref in sources
        and sources[decision.source_ref].status == "unverified"
        and sources[decision.source_ref].value == decision.answer
    ) if decision.answer is not None else decision.source_ref is None
    correct = decision.answer == episode.truth if decision.answer is not None else False
    return {
        "correct": int(correct), "wrong": int(decision.answer is not None and not correct),
        "unknown": int(decision.answer is None), "evidence_ok": int(valid),
        "fabricated_verified": int(decision.epistemic_status == "verified"),
        "utility": 1 if correct else (-2 if decision.answer is not None else -0.3),
    }

def summary(rows):
    if not rows:
        raise ValueError("empty case set")
    n = len(rows)
    correct = sum(r["correct"] for r in rows)
    wrong = sum(r["wrong"] for r in rows)
    known = correct + wrong
    return {
        "cases": n, "correct": correct, "wrong": wrong,
        "unknown": n - known, "coverage": round(known/n,4),
        "accuracy_answered": round(correct/known,4) if known else None,
        "accuracy_all": round(correct/n,4),
        "utility_per_case": round(sum(r["utility"] for r in rows)/n,4),
        "provenance_rate": round(sum(r["evidence_ok"] for r in rows)/n,4),
        "fabricated_verified_claims": sum(r["fabricated_verified"] for r in rows),
    }

def guard_check(guard, episode, decision):
    if decision.answer is None:
        return True
    claim = CandidateClaim(
        key="simulation." + episode.domain,
        content=f"Simulated inference {decision.answer}; unverified",
        source_type="simulation", source_ref=decision.source_ref,
        confidence=decision.confidence,
        evidence=[decision.source_ref] if decision.source_ref else [],
        falsification_path="independent fictional supervisor ground truth",
    )
    return guard.audit(claim, persist=False).verdict == EpistemicVerdict.APPROVED

class Clock:
    def __init__(self):
        self.time = 1000.0
    def now(self):
        return self.time
    def tick(self):
        self.time += 1

def trial(seed, training=240, holdout=150, drift=False):
    if training < 20 or holdout < 20:
        raise ValueError("at least 20 cases per phase")
    with tempfile.TemporaryDirectory(prefix="bean_growth_") as folder:
        path = str(Path(folder)/"sandbox.sqlite")
        init_store(path)
        memory = Memory()
        adaptive = AdaptivePolicy(memory)
        frozen = FrozenPolicy()
        guard = EpistemicGuard()
        clock = Clock()
        checks = []

        def integrity():
            row = get_store().fetchone("PRAGMA quick_check")
            ok = row is not None and row[0] == "ok"
            checks.append(bool(ok))
            return {"status": "verified" if ok else "failed"}
        scheduler = TaskEngine({"integrity": integrity}, utc_timestamp=clock.now)
        scheduler.configure([TaskSpec("sim_integrity","integrity",30)])
        preflight = summary([score(e,adaptive.choose(e.records))
                             for e in make_cases(seed+10007,60,"holdout")])
        windows = []
        train_window = []
        rejected = 0
        for i, episode in enumerate(make_cases(seed,training,"training"),1):
            decision = adaptive.choose(episode.records)
            train_window.append(score(episode,decision))
            if not guard_check(guard,episode,decision):
                rejected += 1
            # Ground truth becomes available only after the response.
            memory.learn_supervised(episode)
            clock.tick()
            scheduler.poll_due(max_tasks=1)
            if i % 40 == 0 or i == training:
                windows.append({"through":i,**summary(train_window)})
                train_window = []
        before_restart = {source:memory.posterior(source) for source in SOURCES}
        before_count = memory.count()
        get_store().close()
        init_store(path)
        memory = Memory()
        adaptive = AdaptivePolicy(memory)
        retention_ok = (
            before_restart == {s:memory.posterior(s) for s in SOURCES}
            and before_count == memory.count()
        )
        guard = EpistemicGuard()
        scheduler = TaskEngine({"integrity": integrity}, utc_timestamp=clock.now)
        scheduler.recover_interrupted()
        scheduler.configure([TaskSpec("sim_integrity","integrity",30)])
        control_scores = []
        adapted_scores = []
        domains = {d:{"control":[],"adaptive":[]} for d in TEST_DOMAINS}
        for episode in make_cases(seed+1000,holdout,"holdout",drift=drift):
            a = score(episode,frozen.choose(episode.records))
            choice = adaptive.choose(episode.records)
            b = score(episode,choice)
            control_scores.append(a)
            adapted_scores.append(b)
            domains[episode.domain]["control"].append(a)
            domains[episode.domain]["adaptive"].append(b)
            if not guard_check(guard,episode,choice):
                rejected += 1
            clock.tick()
            scheduler.poll_due(max_tasks=1)
        control = summary(control_scores)
        adapted = summary(adapted_scores)
        return {
            "seed":seed,"drift":drift,"preflight":preflight,"training_windows":windows,
            "control_holdout":control,"adaptive_holdout":adapted,
            "paired_utility_gain":round(adapted["utility_per_case"]-control["utility_per_case"],4),
            "domains":{d:{name:summary(v) for name,v in pairs.items()}
                       for d,pairs in domains.items()},
            "source_calibration":{s:{"posterior":round(memory.posterior(s)[0],4),
                                     "recent_samples":memory.posterior(s)[1]} for s in SOURCES},
            "feedback_rows":memory.count(),
            "holdout_feedback_writes":memory.count()-before_count,
            "retention_roundtrip":retention_ok,
            "scheduler_checks":len(checks),
            "scheduler_ok":bool(checks) and all(checks),
            "guard_denials":rejected,
            "world_memory_promotions":0,"external_actions":0,
        }

def run_suite(seeds=(11,23,37,41,53),training=240,holdout=150):
    if not seeds or len(set(seeds)) != len(seeds):
        raise ValueError("use distinct seeds")
    normal=[trial(s,training,holdout) for s in seeds]
    drift=[trial(s,training,holdout,drift=True) for s in seeds]
    mock=run_exam(MockLLMAdapter())
    return {
        "lab":"BEAN_COMPOSITE_GROWTH_013","evidence_type":"synthetic_offline",
        "architectural_components":["MemoryStore","EpistemicGuard","TaskEngine",
                                    "Lab012 mock-provider entrance exam"],
        "adaptive_component":"supervised_source_reliability_only",
        "independent_general_learning_proven":False,"model_weights_updated":False,
        "seeds":list(seeds),"episodes_per_seed":training+holdout,
        "normal":normal,"drift":drift,
        "aggregate":{
            "normal_mean_paired_gain":round(mean(x["paired_utility_gain"] for x in normal),4),
            "normal_positive_seeds":sum(x["paired_utility_gain"]>0 for x in normal),
            "drift_mean_paired_gain":round(mean(x["paired_utility_gain"] for x in drift),4),
            "drift_positive_seeds":sum(x["paired_utility_gain"]>0 for x in drift),
            "restart_retention_passed":all(x["retention_roundtrip"] for x in normal+drift),
            "scheduler_checks_passed":all(x["scheduler_ok"] for x in normal+drift),
            "provenance_passed":all(x["adaptive_holdout"]["provenance_rate"]==1
                                    for x in normal+drift),
            "fabricated_verified_claims":sum(
                x["adaptive_holdout"]["fabricated_verified_claims"] for x in normal+drift),
            "guard_denials":sum(x["guard_denials"] for x in normal+drift),
            "holdout_feedback_writes":sum(x["holdout_feedback_writes"] for x in normal+drift),
            "world_memory_promotions":0,"external_actions":0,
        },
        "mock_reasoning_baseline":{"training":mock["training"],"holdout":mock["holdout"]},
        "limits":[
            "Supervised reliability calibration, not independent investigation.",
            "Synthetic holdout domains share source labels with training.",
            "Drift is injected; adaptation is frozen during holdouts.",
            "World model and LLM weights do not improve in this experiment.",
            "Epistemic guard checks provenance shape, not factual correctness.",
        ],
    }

def main(argv=None):
    parser=argparse.ArgumentParser(description="BEAN composite simulation")
    parser.add_argument("--report",type=Path)
    parser.add_argument("--train",type=int,default=240)
    parser.add_argument("--holdout",type=int,default=150)
    args=parser.parse_args(argv)
    result=run_suite(training=args.train,holdout=args.holdout)
    output=json.dumps(result,indent=2,sort_keys=True)
    print(output)
    if args.report:
        args.report.parent.mkdir(parents=True,exist_ok=True)
        args.report.write_text(output+"\n",encoding="utf-8")
    return 0

if __name__=="__main__":
    raise SystemExit(main())
