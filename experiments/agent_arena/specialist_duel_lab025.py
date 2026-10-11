"""Lab025: controlled real Ollama five-agent match, fail closed on missing opponents.

No secret keys, paid backends, benchmark reference code in prompts or production
data. Sources are written by BEAN's validated model author or actual third-party
CLIs, never canned replacements. Agents edit isolated scratch modules.

Authoring and development score jobs do NOT import sealed tests. The separate
credential-free judging entrypoint imports hidden tests.
"""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import time

from bean.evaluation.lab023_ollama import Ollama, OllamaUnavailable
from bean.optimization.autodev import Journal
from experiments.agent_arena.author import model_written_module, sha, write_json
from experiments.agent_arena.specialist_cases_lab025 import CASES, public_case, digest

ROUNDS = 3
SCHEMA = "bean.lab025.specialist-duel.v1"
MODEL = "qwen2.5-coder:1.5b"


def clean_env(root):
    env = {
        "PATH": os.environ.get("PATH", ""),
        "HOME": str(root),
        "OLLAMA_HOST": "http://127.0.0.1:11434",
        "OLLAMA_API_BASE": "http://127.0.0.1:11434",
        "OLLAMA_CONTEXT_LENGTH": "65536",
        "GOOSE_PROVIDER": "ollama", "GOOSE_MODEL": MODEL,
        "GOOSE_MODE": "auto",
        "OLLAMA_MODEL": MODEL,
        "AIDER_ANALYTICS": "false",
        "DO_NOT_TRACK": "1",
        "PYTHONDONTWRITEBYTECODE": "1",
        "NO_COLOR": "1",
        "CI": "true",
        "LLM_MODEL": "ollama/" + MODEL,
        "LLM_BASE_URL": "http://127.0.0.1:11434",
        "LLM_API_KEY": "local-ollama-only",
    }
    return env


def isolated_test(source, suite, *, runner=subprocess.run):
    """Run source exclusively in no-network, no-privilege, read-only Docker."""
    with tempfile.TemporaryDirectory(prefix="lab025-judge-") as scratch:
        root = Path(scratch)
        root.chmod(0o755)
        for name, data in (("candidate.py", source), ("test_candidate.py", suite)):
            file = root / name
            file.write_bytes(data.encode("utf-8"))
            file.chmod(0o644)
        cmd = [
            "docker", "run", "--rm", "--network", "none",
            "--read-only", "--cpus", "1", "--memory", "256m",
            "--pids-limit", "64", "--cap-drop", "ALL",
            "--security-opt", "no-new-privileges",
            "--user", "65534:65534",
            "--mount", "type=bind,source="+str(root)+",target=/tests,readonly",
            "-w", "/tests", "-e", "PYTHONDONTWRITEBYTECODE=1",
            "python:3.12-slim", "python", "-m", "unittest", "-v", "test_candidate",
        ]
        try:
            proc = runner(cmd, capture_output=True, text=True, timeout=40,
                          env={"PATH": os.environ.get("PATH","")})
        except (OSError, subprocess.TimeoutExpired) as e:
            return {"status":"infrastructure_failure",
                    "passed":0,"total":0,"reason":type(e).__name__}
        output = (proc.stdout + "\n" + proc.stderr)[-16000:]
        m = re.search(r"Ran (\d+) tests? in", output)
        total = int(m.group(1)) if m else 0
        bad = sum(int(x) for x in re.findall(r"(?:failures|errors|skipped)=(\d+)", output))
        return {"status": ("passed" if proc.returncode == 0 and total >= 3
                            else "failed") if total >= 3 else "infrastructure_failure",
                "passed": max(0,total-bad), "total": total,
                "output_sha256": sha(output)}


def bean_attempt(client, public, original, own_previous, feedback, history, iteration):
    note = ""
    if own_previous:
        note = ("\nYOUR LAST SOURCE:\n" + own_previous +
                "\nIndependent DEVELOPMENT result: " + str(feedback["passed"]) +
                "/" + str(feedback["total"]) + " tests passed. "
                "Preserve valid behavior and correct the missing requirements.")
    elif history:
        note = ("\nEarlier source attempts were rejected by BEAN's source gate. "
                "A complete valid Python file is required, not reasoning or a patch.")
    prompt = (
        "Act as BEAN's coding engine. Return only a complete, executable "
        "Python module; no markdown, JSON, explanation, external packages or "
        "file/network access. Preserve the public function and signature. "
        "Check the requirements and make a concrete fix.\n"
        "PUBLIC CONTRACT:\n" + public["prompt"] +
        "\nCURRENT ORIGINAL CODE:\n" + original + note
    )
    try:
        raw = client.complete(prompt, tokens=4200, temperature=0.1)
        candidate, _ = model_written_module(original, raw)
        return candidate, "candidate", None
    except (OllamaUnavailable, ValueError, SyntaxError) as e:
        return None, "invalid", type(e).__name__


def run_opponent(name, client, public, own_previous, feedback, attempt, *, runner=subprocess.run):
    """Invoke a named REAL installed upstream CLI; absence is infrastructure failure."""
    with tempfile.TemporaryDirectory(prefix="lab025-"+name+"-") as tmp:
        root = Path(tmp)
        source = root / "candidate.py"
        source.write_bytes((own_previous or public["source"]).encode())
        prompt = ("Repair candidate.py only. Do not alter tests, install packages, "
                  "commit, or use network. Return the correct source in candidate.py. "
                  + public["prompt"])
        if own_previous:
            prompt += ("\nYour previous candidate passed " +
                       str(feedback["passed"]) + "/" + str(feedback["total"]) +
                       " private DEVELOPMENT tests. Improve while keeping good behavior.")
        env = clean_env(root)
        if name == "opencode":
            config = {
                "$schema": "https://opencode.ai/config.json",
                "provider": {"ollama": {"npm":"@ai-sdk/openai-compatible",
                    "name":"Ollama",
                    "options":{"baseURL":"http://127.0.0.1:11434/v1"},
                    "models":{MODEL:{"name":MODEL,
                       "limit":{"context":65536,"output":4096}}}}},
                "model":"ollama/"+MODEL,
            }
            (root / "opencode.json").write_text(json.dumps(config))
            cmd = ["opencode", "run", "--model","ollama/"+MODEL,prompt]
        elif name == "goose":
            cmd = ["goose", "run", "--no-session", "--provider","ollama",
                   "--model", MODEL, "--with-builtin","developer",
                   "--max-turns","10", "-t", prompt]
        elif name == "openhands":
            cmd = ["openhands","--headless","--always-approve",
                   "--override-with-envs","--task",prompt]
        elif name == "continue":
            cfg = root / "config.yaml"
            cfg.write_text(
                "name: Lab025 Local Only\nversion: 0.0.1\nschema: v1\n"
                "models:\n  - name: Local Coder\n    provider: ollama\n"
                "    model: " + MODEL + "\n    apiBase: http://127.0.0.1:11434\n"
                "    roles: [chat, edit, apply]\n"
            )
            cmd = ["cn","-p",prompt,"--config",str(cfg),"--auto"]
        elif name == "cline":
            # Official Ollama integration configures the local model without keys.
            cmd = ["ollama","launch","cline","--model",MODEL,"--",
                   "--yolo",prompt]
        else:
            raise ValueError("opponent not registered")
        try:
            started = time.monotonic()
            p = runner(cmd,cwd=root,env=env,stdin=subprocess.DEVNULL,
                       capture_output=True,text=True,timeout=215)
            elapsed = round(time.monotonic()-started,2)
            candidate = source.read_text(encoding="utf-8")
            log = p.stdout + "\n" + p.stderr
            meta = {"exit_code":p.returncode,"elapsed_seconds":elapsed,
                    "log_sha256":sha(log)}
            if not candidate.strip() or candidate == (own_previous or public["source"]):
                return None, "no_candidate" if p.returncode == 0 else "tool_failure", meta
            try:
                validated, _ = model_written_module(public["source"],candidate)
                return validated, "candidate", meta
            except (ValueError, SyntaxError) as e:
                return None, "invalid", {**meta,"reason":type(e).__name__}
        except (OSError,subprocess.TimeoutExpired) as e:
            return None, "tool_failure", {"reason":type(e).__name__}


def author(name, directory, *, client=None, bean_writer=bean_attempt,
           opponent_writer=run_opponent, grader=isolated_test):
    if name not in CASES:
        raise ValueError("unknown opponent")
    directory = Path(directory)
    if directory.exists() and any(directory.iterdir()):
        raise ValueError("new trial needs an empty output directory")
    client = client or Ollama(model=MODEL)
    client.preflight()
    public = public_case(name)
    directory.mkdir(parents=True, exist_ok=True)
    journal = Journal(directory / "bean-journal.sqlite")
    agents = {}
    try:
        for agent in ("bean",name):
            own, feedback, history = None, {"passed":0,"total":3}, []
            attempts = []
            for round_num in range(1,ROUNDS+1):
                if agent == "bean":
                    candidate, status, reason = bean_writer(
                        client,public,public["source"],own,feedback,history,round_num)
                else:
                    candidate, status, reason = opponent_writer(
                        name,client,public,own,feedback,round_num)
                row = {"round":round_num, "author_status":status,
                       "source_sha256":public["source_sha256"],
                       "model_requested":"ollama/"+client.model,
                       "candidate_sha256":sha(candidate) if candidate else None,
                       "author_metadata":reason}
                if status == "candidate" and candidate:
                    file = directory / "candidates" / agent / ("round"+str(round_num)+".py")
                    file.parent.mkdir(parents=True,exist_ok=True)
                    file.write_bytes(candidate.encode())
                    grade = grader(candidate,CASES[name]["dev"])
                    if grade["status"] == "infrastructure_failure":
                        raise RuntimeError("independent Docker development checker unavailable")
                    own,feedback = candidate,grade
                else:
                    grade = {"status":"not_submitted","passed":0,"total":3}
                row["development"] = grade
                attempts.append(row)
                history.append(row)
                if agent == "bean":
                    journal.append({"objective":name,"iteration":round_num,
                      "outcome":status,"source_sha256":row["candidate_sha256"],
                      "passed":grade["passed"],"total":grade["total"],
                      "model_requested":row["model_requested"]})
            eligible=[a for a in attempts if a["candidate_sha256"]]
            best=max(eligible,key=lambda r:(r["development"]["passed"],-r["round"])) if eligible else None
            agents[agent]={"rounds":attempts,
              "selected_round":best["round"] if best else None,
              "selected_sha256":best["candidate_sha256"] if best else None}
        tip=journal.export()["tip"]
    finally:
        journal.close()
    manifest={"schema":SCHEMA,"case":name,"public_sha256":digest()[name]["public"],
        "holdout_sha256":digest()[name]["holdout"],
        "development_sha256":digest()[name]["development"],
        "model_requested":"ollama/"+client.model,
        "agent_order":["bean",name],"rounds":ROUNDS,"agents":agents,
        "journal_tip":tip,"source_executed_in_author_process":False,
        "model_weights_updated":False}
    write_json(directory / "manifest.json",manifest)
    return manifest


def judge(name,directory,*,grader=isolated_test):
    """Import and execute withheld suite ONLY in credential-free judging job."""
    directory=Path(directory)
    doc=json.loads((directory/"manifest.json").read_text(encoding="utf-8"))
    hashes=digest()[name]
    if doc["schema"]!=SCHEMA or doc["case"]!=name or (
        doc["public_sha256"]!=hashes["public"] or
        doc["holdout_sha256"]!=hashes["holdout"] or
        doc["development_sha256"]!=hashes["development"] or
        set(doc["agents"])!={"bean",name}):
        raise ValueError("agent, task, or sealed test identity mismatch")
    journal=Journal(directory/"bean-journal.sqlite")
    try:
        if journal.export()["tip"]!=doc["journal_tip"] or len(journal.events())!=ROUNDS:
            raise ValueError("BEAN persistent attempt journal invalid")
    finally:
        journal.close()
    result={}
    comparable=True
    for agent in ("bean",name):
        a=doc["agents"][agent]
        if len(a["rounds"])!=ROUNDS:
            raise ValueError("lost iteration evidence")
        for k,rec in enumerate(a["rounds"],1):
            if rec["round"]!=k or rec["model_requested"]!=doc["model_requested"] or (
                    rec["source_sha256"]!=public_case(name)["source_sha256"]):
                raise ValueError("model, round or original source modified")
            file=directory/"candidates"/agent/("round"+str(k)+".py")
            if rec["candidate_sha256"]:
                if not file.is_file() or sha(file.read_bytes())!=rec["candidate_sha256"]:
                    raise ValueError("candidate source digest mismatch")
            elif file.exists():
                raise ValueError("unattested executable source present")
            if rec["author_status"]=="tool_failure":
                comparable=False
        ix=a["selected_round"]
        if ix is None:
            comparable=False
            result[agent]={"status":"no_candidate","passed":0,"total":8}
        else:
            rec=a["rounds"][ix-1]
            if rec["candidate_sha256"]!=a["selected_sha256"]:
                raise ValueError("selection does not match source")
            code=(directory/"candidates"/agent/("round"+str(ix)+".py")).read_text(encoding="utf-8")
            result[agent]=grader(code,CASES[name]["holdout"])
            if result[agent]["status"]=="infrastructure_failure":
                raise RuntimeError("independent hidden Docker judge unavailable")
    bp=result["bean"]["passed"];op=result[name]["passed"]
    verdict=("INCONCLUSIVE" if not comparable else
             "BEAN_WIN" if bp>op else name.upper()+"_WIN" if op>bp else "TIE")
    report={"schema":SCHEMA,"classification":verdict,"opponent":name,
            "discipline":CASES[name]["discipline"],"results":result,
            "comparable":comparable,"rounds":ROUNDS,
            "model_requested":doc["model_requested"],
            "limits":["one case per specialist; not general superiority",
                      "external agent tool-call count may differ",
                      "a 1.5B local coding model may be too weak for agent tool protocols",
                      "only selected development candidates face hidden test suite"],
            "journal_verified":True}
    report["evidence_sha256"]=sha(json.dumps(report,sort_keys=True))
    write_json(directory/"verdict.json",report)
    return report


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("stage",choices=("author","judge"))
    p.add_argument("--opponent",choices=tuple(CASES),required=True)
    p.add_argument("--out",type=Path,required=True)
    a=p.parse_args(argv)
    record=(author(a.opponent,a.out) if a.stage=="author" else judge(a.opponent,a.out))
    print(json.dumps(
        {"stage":a.stage,"opponent":a.opponent,
         "classification":record.get("classification"),
         "model_requested":record["model_requested"],
         "status":"authored" if a.stage=="author" else "judged"},indent=2))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
