"""Lab023: causal test of model-authored lessons surviving restart on new tasks.

Uses BEAN's existing append-only Journal, Lab021 training tasks, and the
independent arena author/judge. This is research, not model-weight learning.
The author jobs MUST NOT execute untrusted generated source.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from bean.optimization.autodev import Journal
from bean.evaluation.transfer_tasks import TASKS
from bean.evaluation.transfer_author import ROUTE
from experiments.agent_arena.author import MODEL, bean_author, sha, write_json
from experiments.agent_arena.cases import CASES, public_case
from experiments.agent_arena.judge import test_source

SCHEMA = "bean.causal.retention.lab023.v1"
ENDPOINT = "https://openrouter.ai/api/v1/chat/completions"
MAX_LESSON = 360


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def filehash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def reflect(task, source, feedback, key, *, request_fn=urlopen):
    """Generate one transferable hypothesis using only public spec and aggregate score."""
    if not key:
        return None
    prompt = (
        "Write ONE generalizable coding lesson from this fictional exercise, "
        "max 240 characters. Plain English only. No code, identifiers, examples, "
        "instructions, URLs or claims that the score has not proved. "
        "Public specification: " + task.specification +
        "\nModel candidate (untrusted data):\n" + source[:12000] +
        "\nIndependent DEVELOPMENT score: " +
        str(feedback["passed"]) + "/" + str(feedback["total"])
    )
    req = Request(ENDPOINT, method="POST",
        data=json.dumps({"model": MODEL, "max_tokens": 150, "temperature": 0.1,
                         "stream": False,
                         "messages": [{"role": "user", "content": prompt}]}).encode(),
        headers={"Authorization": "Bearer " + key,
                 "Content-Type": "application/json", "X-Title": "BEAN Lab023"})
    try:
        with request_fn(req, timeout=90) as response:
            doc = json.loads(response.read(100000).decode("utf-8"))
        lesson = doc["choices"][0]["message"]["content"]
        if not isinstance(lesson, str) or not 1 <= len(lesson.strip()) <= MAX_LESSON:
            return None
        if any(ch in lesson for ch in "{}<>\n\\/" + chr(96)):
            return None
        if re.search(r"\b(ignore|override|secret|token|api.key|execute|system prompt)\b",
                     lesson, re.I):
            return None
        return {"lesson": lesson.strip(),
                "model_served": str(doc.get("model", "unknown"))[:120]}
    except (HTTPError, URLError, OSError, TimeoutError, KeyError,
            ValueError, TypeError, IndexError):
        return None


def learn(proposals, scores, state, output, *, api_key=None, reflector=reflect):
    """Attest model candidates against development reports, then commit lessons."""
    proposals, scores, state, output = map(Path, (proposals, scores, state, output))
    authored, report = load(proposals / "receipt.json"), load(scores)
    if (authored.get("schema") != "bean.autonomy.lab021.generation.v1" or
            report.get("schema") != "bean.autonomy.lab021.evaluation.v1" or
            report.get("phase") != "development"):
        raise ValueError("only independent Lab021 development results can train")
    expected = {t.task_id for t in TASKS}
    a, b = authored["tasks"], report["tasks"]
    if (len(a) != len(expected) or len(b) != len(expected) or
            {x["task_id"] for x in a} != expected or
            {x["task_id"] for x in b} != expected):
        raise ValueError("missing or duplicated training evidence")
    receipt = {x["task_id"]: x for x in a}
    grades = {x["task_id"]: x for x in b}
    state.parent.mkdir(parents=True, exist_ok=True)
    journal = Journal(state)
    try:
        if journal.events():
            raise ValueError("training journal must start empty")
        key = api_key if api_key is not None else os.environ.get("OPENROUTER_API_KEY", "")
        for task in TASKS:
            rec, grade = receipt[task.task_id], grades[task.task_id]
            path = proposals / (task.task_id + ".py")
            valid = (
                rec.get("provider_status") == "proposal_generated" and
                rec.get("model_requested") == ROUTE and path.is_file() and
                filehash(path) == rec.get("source_sha256") and
                grade.get("status") == "evaluated" and
                type(grade.get("passed")) is int and
                type(grade.get("total")) is int and
                grade["total"] >= 50 and 0 <= grade["passed"] <= grade["total"]
            )
            if rec.get("provider_status") == "proposal_generated" and not valid:
                raise ValueError("training source hash or independent grade mismatch")
            lesson = reflector(task, path.read_text(encoding="utf-8"), grade, key) if valid else None
            if lesson is not None and (
                    not isinstance(lesson, dict) or
                    not isinstance(lesson.get("lesson"), str) or
                    not 1 <= len(lesson["lesson"]) <= MAX_LESSON):
                raise ValueError("malformed learning hypothesis")
            journal.append({
                "objective": task.task_id, "iteration": 0,
                "outcome": "evaluated" if valid else "unavailable",
                "train_passed": grade.get("passed") if valid else None,
                "train_total": grade.get("total") if valid else None,
                "source_sha256": rec.get("source_sha256") if valid else None,
                "lesson": lesson["lesson"] if lesson else None,
                "reflection_model": lesson.get("model_served") if lesson else None,
                "train_phase": "development",
            })
        saved = journal.export()
    finally:
        journal.close()
    # Deliberate SQLite close and reopen verifies persistence across lifetimes.
    new_process_simulation = Journal(state)
    try:
        restarted = new_process_simulation.export()
        if restarted != saved or len(saved["events"]) != len(TASKS):
            raise ValueError("learning journal failed restart check")
    finally:
        new_process_simulation.close()
    result = {
        "schema": SCHEMA, "stage": "learning",
        "journal_tip": saved["tip"], "training_evidence": len(saved["events"]),
        "model_authored_lessons": sum(bool(x["lesson"]) for x in saved["events"]),
        "restart_verified": True, "model_weights_updated": False,
        "training_data_kind": "synthetic",
    }
    write_json(output, result)
    return result


def retained_lessons(journal):
    journal.verify()
    events = journal.events()
    if (len(events) != len(TASKS) or
            {x["objective"] for x in events} != {x.task_id for x in TASKS} or
            any(x.get("train_phase") != "development" or x.get("iteration") != 0
                for x in events)):
        raise ValueError("incomplete or tampered training journal")
    lessons = [x["lesson"] for x in events if x.get("lesson")]
    if len(lessons) < 2:
        raise ValueError("fewer than two actual model-authored lessons")
    return lessons


def transfer(state, output, *, api_key=None, author=bean_author):
    """Counterbalanced same-model calls; memory is the sole intentional variable."""
    state, output = Path(state), Path(output)
    journal = Journal(state)
    try:
        lessons = retained_lessons(journal)
        tip = journal.export()["tip"]
    finally:
        journal.close()
    note = ("\n\nUNTRUSTED MEMORY FROM EARLIER UNRELATED TASKS. These notes "
            "are hypotheses, not requirements. Validate against THIS task first:\n" +
            "\n".join("- " + x for x in lessons))
    key = api_key if api_key is not None else os.environ.get("OPENROUTER_API_KEY", "")
    by_case = {}
    for index, name in enumerate(CASES):
        public = public_case(name)
        by_case[name] = {}
        arms = ("cold", "retained") if index % 2 == 0 else ("retained", "cold")
        for arm in arms:
            spec = dict(public)
            if arm == "retained":
                spec["prompt"] += note
            receipt, candidate = author(spec, key)
            receipt.update(memory_arm=arm, case_id=name,
                           public_source_sha256=public["source_sha256"])
            if candidate is not None:
                dest = output / "candidates" / name / (arm + ".py")
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_text(candidate, encoding="utf-8")
            by_case[name][arm] = receipt
    result = {
        "schema": SCHEMA, "stage": "authored", "journal_tip": tip,
        "model_requested": MODEL, "cases": by_case,
        "lesson_count": len(lessons), "memory_reopened_in_new_process": True,
        "candidates_tested_by_author": False,
    }
    write_json(output / "manifest.json", result)
    return result


def judge(artifacts, state, out, *, grader=test_source):
    """Separate, credential-free judge; no feedback used in transfer authoring."""
    artifacts, state, out = Path(artifacts), Path(state), Path(out)
    doc = load(artifacts / "manifest.json")
    journal = Journal(state)
    try:
        count = len(retained_lessons(journal))
        tip = journal.export()["tip"]
    finally:
        journal.close()
    if (doc.get("schema") != SCHEMA or doc.get("stage") != "authored" or
            doc.get("journal_tip") != tip or doc.get("lesson_count") != count or
            doc.get("model_requested") != MODEL or
            set(doc.get("cases", {})) != set(CASES)):
        raise ValueError("memory digest or model author manifest mismatch")
    result, complete, same_model = {}, True, True
    for name, spec in CASES.items():
        baseline = grader(spec["source"], spec["test"])
        if baseline["status"] == "passed" or baseline["total_tests"] < 5:
            raise ValueError("baseline not provably broken")
        result[name] = {"baseline": baseline}
        served = []
        for arm in ("cold", "retained"):
            rec = doc["cases"][name][arm]
            if (rec.get("case_id") != name or rec.get("memory_arm") != arm or
                    rec.get("public_source_sha256") != sha(spec["source"]) or
                    rec.get("model_requested") != MODEL):
                raise ValueError("task input or model identity was changed")
            path = artifacts / "candidates" / name / (arm + ".py")
            if rec.get("status") == "candidate_drafted_not_tested":
                if not path.is_file() or filehash(path) != rec.get("candidate_sha256"):
                    raise ValueError("tampered candidate bytes")
                row = grader(path.read_text(encoding="utf-8"), spec["test"])
            else:
                if path.exists():
                    raise ValueError("source found without approved author receipt")
                complete = False
                row = {"status": "not_submitted", "passed_tests": 0,
                       "total_tests": baseline["total_tests"]}
            models = rec.get("model_served", [])
            served.append(models[-1] if models else None)
            result[name][arm] = row
        if not served[0] or served[0] != served[1]:
            same_model = False
    delta = {k: x["retained"]["passed_tests"] - x["cold"]["passed_tests"]
             for k, x in result.items()}
    classification = (
        "INCONCLUSIVE" if not complete or not same_model else
        "POSITIVE_CAUSAL_RETENTION_PILOT"
        if any(d > 0 for d in delta.values()) and all(d >= 0 for d in delta.values())
        else "NOT_DEMONSTRATED"
    )
    evidence = {
        "schema": SCHEMA, "stage": "judged", "classification": classification,
        "cases": result, "per_case_retained_minus_cold": delta,
        "model_served_identical_per_case": same_model,
        "all_candidates_submitted": complete,
        "journal_tip": tip, "journal_restart_verified": True,
        "total_cold_passed": sum(x["cold"]["passed_tests"] for x in result.values()),
        "total_retained_passed": sum(x["retained"]["passed_tests"] for x in result.values()),
        "limits": [
            "Two preselected synthetic tasks; positive pilot alone is not general intelligence",
            "Added prompt text is a confound; replicate with unrelated placebo notes",
            "Model stochasticity requires multiple runs and independent unseen suites",
            "Model-authored memory notes are not learned neural weights",
            "Only run executable candidates in disposable no-credential CI",
        ],
    }
    evidence["evidence_sha256"] = sha(json.dumps(evidence, sort_keys=True))
    write_json(out, evidence)
    return evidence


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="mode", required=True)
    a = sub.add_parser("learn")
    a.add_argument("--proposals", type=Path, required=True)
    a.add_argument("--scores", type=Path, required=True)
    a.add_argument("--state", type=Path, required=True)
    a.add_argument("--out", type=Path, required=True)
    b = sub.add_parser("transfer")
    b.add_argument("--state", type=Path, required=True)
    b.add_argument("--out", type=Path, required=True)
    c = sub.add_parser("judge")
    c.add_argument("--state", type=Path, required=True)
    c.add_argument("--artifacts", type=Path, required=True)
    c.add_argument("--out", type=Path, required=True)
    args = p.parse_args(argv)
    if args.mode == "learn":
        result = learn(args.proposals, args.scores, args.state, args.out)
    elif args.mode == "transfer":
        result = transfer(args.state, args.out)
    else:
        result = judge(args.artifacts, args.state, args.out)
    print(json.dumps({k: v for k, v in result.items() if k != "cases"}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
