#!/usr/bin/env python3
"""Non-destructive Jetson inspection: static wiring plus isolated BEAN startup.

Stdlib only. No installation, credentials, motor commands, or live DB changes.
"""
from __future__ import annotations
import argparse
import ast
import importlib.util
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from urllib.request import Request, ProxyHandler, build_opener

DEPS = ("psutil", "pytest", "numpy", "cv2", "serial", "vosk", "piper", "torch", "sounddevice")
FLAGS = ("BEAN_REASONING_ENABLED", "BEAN_REASONING_PROVIDER", "BEAN_LOCAL_LLM_URL",
         "BEAN_LOCAL_LLM_MODEL", "BEAN_BODY_CONFIG", "BEAN_TASK_CONFIG",
         "BEAN_WATCH_CONFIG", "BEAN_LEARNING_DB")


def run(command, root, timeout=15, env=None):
    try:
        p = subprocess.run(command, cwd=root, env=env, capture_output=True,
                           text=True, timeout=timeout, check=False)
        return p.returncode, (p.stdout + "\n" + p.stderr)[-3000:]
    except (OSError, subprocess.TimeoutExpired) as exc:
        return None, type(exc).__name__


def scrub(s):
    home = str(Path.home())
    if home != "/":
        s = s.replace(home, "~")
    return re.sub(r"(?i)(token|password|secret|api[_-]?key)\s*[:=]\s*\S+",
                  r"\1=<redacted>", s)


def dependency_report(python, root):
    code = "import importlib.util,json;print(json.dumps({x:bool(importlib.util.find_spec(x)) for x in " + repr(DEPS) + "}))"
    rc, output = run([python, "-c", code], root)
    try:
        return json.loads(output.strip()) if rc == 0 else {"error": scrub(output[-300:])}
    except ValueError:
        return {"error": "Could not read dependency probe output"}


def inspect_source(root):
    paths = list((root / "bean").rglob("*.py")) if (root / "bean").is_dir() else []
    errors = []
    for path in paths:
        try:
            ast.parse(path.read_text(encoding="utf-8"))
        except (SyntaxError, UnicodeError):
            errors.append(str(path.relative_to(root)))
    def tree_of(filename):
        path = root / filename
        return ast.parse(path.read_text(encoding="utf-8")) if path.exists() else ast.parse("")
    ticks = []
    for node in ast.walk(tree_of("bean/runtime/tick_handlers.py")):
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                and node.func.attr == "register" and node.args
                and isinstance(node.args[0], ast.Constant)
                and isinstance(node.args[0].value, str)):
            ticks.append(node.args[0].value)
    commands = []
    for node in ast.walk(tree_of("bean/runtime/inbox_handlers.py")):
        if isinstance(node, ast.FunctionDef) and node.name == "make_handlers":
            for child in ast.walk(node):
                if isinstance(child, ast.Return) and isinstance(child.value, ast.Dict):
                    commands = [k.value for k in child.value.keys
                                if isinstance(k, ast.Constant) and isinstance(k.value, str)]
                    break
    refs = set()
    for node in ast.walk(tree_of("bean_run.py")):
        if isinstance(node, ast.ImportFrom) and node.module and node.module.startswith("bean."):
            refs.add(node.module)
    return {"python_modules_on_disk": len(paths), "syntax_error_files": errors[:12],
            "entrypoint_import_references": len(refs),
            "declared_periodic_handlers": sorted(set(ticks)),
            "declared_inbox_command_count": len(commands),
            "declared_inbox_command_examples": commands[:16],
            "interpretation": "Static wiring inventory only; modules need runtime execution evidence."}


def probe_local_http(port, endpoint):
    try:
        opener = build_opener(ProxyHandler({}))
        with opener.open(Request(f"http://127.0.0.1:{port}{endpoint}", method="GET"),
                         timeout=1.5) as response:
            return {"reachable": True, "http_status": response.status}
    except Exception:
        return {"reachable": False}


def main():
    parser = argparse.ArgumentParser(description="Audit BEAN's actual Jetson Python and runtime")
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--smoke", action="store_true", help="Run one tick with disposable DB and example joints")
    args = parser.parse_args()
    root = args.root.expanduser().resolve()
    report = {"audit": "BEAN Jetson live inventory", "repo_present": (root / "bean_run.py").is_file(),
              "system": platform.system(), "architecture": platform.machine(),
              "jetson_l4t_detected": Path("/etc/nv_tegra_release").exists(),
              "tegrastats_found": shutil.which("tegrastats") is not None}
    if not report["repo_present"]:
        report["next_step"] = "Run from your BEAN source directory or pass --root /path/to/BEAN"
        print(json.dumps(report, indent=2))
        return 2
    py = str(root / ".venv/bin/python3") if (root / ".venv/bin/python3").exists() else sys.executable
    rc, v = run([py, "--version"], root)
    report["python"] = {"interpreter": "repo .venv" if py != sys.executable else "current interpreter",
                        "version": v.strip() if rc == 0 else "unavailable"}
    rc, name = run(["git", "rev-parse", "--abbrev-ref", "HEAD"], root)
    rc2, sha = run(["git", "rev-parse", "--short", "HEAD"], root)
    report["git"] = {"branch": name.strip() if rc == 0 else "unavailable",
                     "commit": sha.strip() if rc2 == 0 else "unavailable"}
    report["packages_available"] = dependency_report(py, root)
    report["config_flags"] = {k: bool(os.environ.get(k)) for k in FLAGS}
    report["local_models"] = {"llamacpp_port_8080": probe_local_http(8080, "/health"),
                              "ollama_port_11434": probe_local_http(11434, "/api/tags")}
    if shutil.which("systemctl"):
        rc, active = run(["systemctl", "is-active", "bean.service"], root, timeout=4)
        report["bean_service"] = active.strip().splitlines()[0][:80] if active.strip() else "unknown"
    report["source_wiring"] = inspect_source(root)
    rc, output = run([py, "-c", "import bean_run; print('BEAN_IMPORT_OK')"], root, timeout=25)
    report["entrypoint_import"] = {"passed": rc == 0, "output_tail": scrub(output[-650:])}
    if args.smoke:
        example = root / "bean/config/body_registry.example.json"
        if not example.is_file():
            report["isolated_boot"] = {"passed": False, "reason": "example body config missing"}
        else:
            with tempfile.TemporaryDirectory(prefix="bean-jetson-smoke-") as temp:
                env = os.environ.copy()
                env.update({"BEAN_DB_PATH": str(Path(temp) / "bean.db"),
                            "BEAN_INBOX_DIR": str(Path(temp) / "inbox"),
                            "BEAN_BODY_CONFIG": str(example),
                            "BEAN_REASONING_ENABLED": "0", "PYTHONDONTWRITEBYTECODE": "1"})
                for k in ("BEAN_LEARNING_DB", "BEAN_TASK_CONFIG", "BEAN_WATCH_CONFIG",
                          "BEAN_WATCH_REPORT_DIR"):
                    env.pop(k, None)
                Path(env["BEAN_INBOX_DIR"]).mkdir()
                rc, output = run([py, "bean_run.py", "--ticks", "1", "--hz", "10", "--no-seed"],
                                 root, timeout=60, env=env)
                report["isolated_boot"] = {"passed": rc == 0, "exit_code": rc,
                                           "output_tail": scrub(output[-1400:]),
                                           "scope": "Temporary DB, no motor output or model inference"}
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
