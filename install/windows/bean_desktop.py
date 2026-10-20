"""Windows desktop entry point. Bundled with the existing BEAN core, no Python required."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import threading
import traceback

# PyInstaller --windowed intentionally sets std streams to None. The Core and
# Python's own subprocess/logging paths expect valid file-like objects.
if sys.stdout is None:
    sys.stdout = open(os.devnull, "w", encoding="utf-8")
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w", encoding="utf-8")


def _report_uncaught(exc_type, exc, tb):
    """Write a CI-readable crash receipt even before self_test() is reached."""
    if "--self-test-report" in sys.argv:
        try:
            idx = sys.argv.index("--self-test-report")
            target = Path(sys.argv[idx + 1])
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(
                json.dumps({"status": "BOOT_FAILURE", "error": repr(exc),
                            "traceback": "".join(traceback.format_exception(exc_type, exc, tb))},
                           indent=2), encoding="utf-8")
        except (OSError, IndexError, ValueError):
            pass
    traceback.print_exception(exc_type, exc, tb, file=sys.stderr)


sys.excepthook = _report_uncaught

import tkinter as tk
from tkinter import messagebox, scrolledtext, ttk

import psutil  # noqa: F401 - Core runtime dependency

# Real imports are deliberately visible to PyInstaller's static module graph.
# Bundling raw .py files as data allows Core to import modules PyInstaller
# never scanned and produces broken frozen builds (e.g. missing stdlib uuid).
from examples.capability_proof import run_proof
from bean.voice.ollama import OllamaClient
from bean.voice.chat import BeanConversation
from bean.voice.persona import system_prompt
from bean.voice.desktop_memory import DesktopMemory
from bean.memory.audit_mirror import mirror_path


def proof_result():
    return run_proof()


def self_test(report_path: str | None = None) -> int:
    """Exercise actual Core APIs; a windowed EXE must not depend on stdout."""
    try:
        result = proof_result()
        passed = (
            result.get("status") == "PASS" and
            result.get("checks_passed") == result.get("checks_total") == 4 and
            result.get("environment") == "offline_fictional_fixtures" and
            result.get("live_model_used") is False
        )
    except Exception as exc:
        result = {"status": "FAIL", "error": repr(exc)}
        passed = False
    if report_path:
        try:
            target = Path(report_path)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(json.dumps(result, indent=2, sort_keys=True),
                              encoding="utf-8")
        except OSError:
            return 1
    elif sys.stdout is not None:
        print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if passed else 1



def memory_fixture_cli(argv: list[str]) -> int:
    """Real cross-process SQLite write/read from the frozen installed EXE."""
    parser = argparse.ArgumentParser(description="BEAN disposable CI memory test")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--memory-fixture-write", type=Path)
    group.add_argument("--memory-fixture-read", type=Path)
    parser.add_argument("--memory-fixture-token", required=True)
    parser.add_argument("--self-test-report", required=True, type=Path)
    args = parser.parse_args(argv)
    report = {"status": "FAIL", "real_sqlite": True, "provider": "none"}
    try:
        token = args.memory_fixture_token
        if not re.fullmatch(r"[A-Za-z0-9-]{8,80}", token):
            raise ValueError("Invalid fixture token")
        source_db = args.memory_fixture_write or args.memory_fixture_read
        if not source_db.is_absolute():
            raise ValueError("Fixture DB path must be absolute")
        note_text = "CI fixture for installed BEAN continuity: " + token
        memory = DesktopMemory(source_db)
        if args.memory_fixture_write is not None:
            saved = memory.remember(note_text)
            report.update(status="PASS", operation="write", event_id=saved["id"],
                          provenance=saved["provenance"])
        else:
            matches = [item for item in memory.recall(token)
                       if item["text"] == note_text]
            if len(matches) != 1:
                raise RuntimeError("Expected one persisted human note across process restart")
            report.update(status="PASS", operation="read", event_id=matches[0]["id"],
                          provenance=matches[0]["provenance"])
        if not mirror_path(memory.path).is_file():
            raise RuntimeError("Canonical audit journal is missing")
    except Exception as exc:
        report["status"] = "FAIL"
        report["error"] = repr(exc)
    try:
        args.self_test_report.parent.mkdir(parents=True, exist_ok=True)
        args.self_test_report.write_text(json.dumps(report, sort_keys=True, indent=2),
                                         encoding="utf-8")
    except OSError:
        return 1
    return 0 if report["status"] == "PASS" else 1


class Desktop(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("BEAN | Evidence-first AI")
        self.geometry("790x565")
        self.minsize(600, 420)
        self.configure(bg="#131c1b")
        self.client = None
        self.conversation = None
        self.memory = DesktopMemory()
        self.include_saved_notes = tk.BooleanVar(value=False)
        self._worker_lock = threading.RLock()
        self._setup()

    def _setup(self):
        bg = "#131c1b"
        fg = "#e5f2e8"
        green = "#91dc91"
        tk.Label(self, text="BEAN", font=("Segoe UI", 28, "bold"),
                 bg=bg, fg=green).pack(pady=(18, 0))
        tk.Label(self, text="Technical beta  |  Offline Core checks + optional local model chat",
                 font=("Segoe UI", 10), bg=bg, fg=fg).pack(pady=(0, 12))
        bar = tk.Frame(self, bg=bg)
        bar.pack(fill="x", padx=20)
        ttk.Button(bar, text="Verify BEAN Core", command=self.verify).pack(side="left", padx=(0, 8))
        ttk.Button(bar, text="Connect local Ollama", command=self.connect).pack(side="left")
        note_bar = tk.Frame(self, bg=bg)
        note_bar.pack(fill="x", padx=20, pady=(8, 0))
        ttk.Button(note_bar, text="Remember note", command=self.remember).pack(side="left", padx=(0, 8))
        ttk.Button(note_bar, text="Recall notes", command=self.recall).pack(side="left", padx=(0, 8))
        ttk.Checkbutton(note_bar, text="Include matching notes in local chat",
                        variable=self.include_saved_notes).pack(side="left")
        self.status = tk.StringVar(value="Ready. Offline core verification works without Ollama.")
        tk.Label(self, textvariable=self.status, bg=bg, fg=green,
                 anchor="w", wraplength=735).pack(fill="x", padx=22, pady=8)
        self.transcript = scrolledtext.ScrolledText(self, bg="#1e2b28", fg=fg,
                insertbackground=fg, font=("Consolas", 10), wrap="word")
        self.transcript.pack(fill="both", expand=True, padx=20, pady=(0, 8))
        self.transcript.insert("end", "BEAN technical beta installed. The offline Core test "
                               "uses fictional fixtures, not a trained model.\n"
                               "Optional Ollama chat uses an already-running model on this PC. "
                               "Chat turns are NOT saved automatically. Type a note and press "
                               "Remember note; Recall notes survives restarts.\n"
                               "Matching notes reach local Ollama ONLY when opted in. "
                               "Saved notes are unverified submissions, not trained model weights.\n\n"
                               "No cloud sign-in or trading/hardware permissions are enabled.\n")
        self.transcript.configure(state="disabled")
        input_row = tk.Frame(self, bg=bg)
        input_row.pack(fill="x", padx=20, pady=(0, 16))
        self.entry = ttk.Entry(input_row)
        self.entry.pack(side="left", expand=True, fill="x", padx=(0, 8))
        self.entry.bind("<Return>", lambda _: self.send())
        ttk.Button(input_row, text="Send", command=self.send).pack(side="left")

    def append(self, text):
        self.transcript.configure(state="normal")
        self.transcript.insert("end", text + "\n")
        self.transcript.see("end")
        self.transcript.configure(state="disabled")

    def background(self, task, on_success):
        def worker():
            try:
                with self._worker_lock:
                    result = task()
            except Exception as exc:
                self.after(0, lambda msg=str(exc): self.fail(msg))
            else:
                self.after(0, lambda value=result: on_success(value))
        threading.Thread(target=worker, daemon=True).start()

    def fail(self, error):
        self.status.set("Not ready: " + error)
        self.append("Error: " + error + "\n")

    def verify(self):
        self.status.set("Checking BEAN Core with offline fictional fixtures...")
        def finished(result):
            self.status.set(f"Core verification: {result['status']} ({result['checks_passed']}/{result['checks_total']})")
            self.append("Offline Core check:\n" + json.dumps(result, indent=2) + "\n")
        self.background(proof_result, finished)

    def remember(self):
        note = self.entry.get().strip()
        if not note:
            self.fail("Type a note, then press Remember note.")
            return
        self.status.set("Saving explicit note to BEAN Core...")
        def done(saved):
            self.status.set(f"Saved Core journal event {saved['id']} (user assertion, unverified)")
            self.append(f"Saved event {saved['id']}: {saved['text']}\n")
            if self.entry.get().strip() == note:
                self.entry.delete(0, "end")
        self.background(lambda: self.memory.remember(note), done)

    def recall(self):
        query = self.entry.get().strip()
        if not query:
            self.fail("Enter words to search saved notes.")
            return
        self.status.set("Searching the local Core journal...")
        def done(items):
            if not items:
                self.append("No matching notes; BEAN will not invent memories.\n")
            else:
                for item in items:
                    self.append(f"Saved event {item['id']} [USER SUBMISSION, UNVERIFIED]: {item['text']}")
            self.status.set(f"Recall complete: {len(items)} matching notes")
        self.background(lambda: self.memory.recall(query), done)

    def connect(self):
        self.status.set("Connecting to local Ollama...")
        def load():
            client = OllamaClient("http://127.0.0.1:11434")
            model = client.select_model(os.environ.get("BEAN_CHAT_MODEL") or None)
            prompt, _ = system_prompt(self.memory.path)
            return model, BeanConversation(client, model, prompt)
        def ready(result):
            model, self.conversation = result
            self.status.set(f"Connected to local model: {model}")
            self.append(f"Connected to Ollama: {model}\n")
        self.background(load, ready)

    def send(self):
        text = self.entry.get().strip()
        if not text:
            return
        if self.conversation is None:
            self.fail("Connect a locally running Ollama model before chatting.")
            return
        self.entry.delete(0, "end")
        self.append("You: " + text)
        include = bool(self.include_saved_notes.get())
        self.status.set("BEAN is thinking...")
        def run():
            reference = self.memory.context_for(text) if include else ""
            response = self.conversation.reply(text, reference_context=reference)
            return response, bool(reference)
        def ready(result):
            reply, used = result
            if used:
                self.append("User-saved UNVERIFIED notes included as model reference context.")
            self.append("BEAN: " + reply + "\n")
            self.status.set("Ready")
        self.background(run, ready)


if __name__ == "__main__":
    if "--memory-fixture-write" in sys.argv or "--memory-fixture-read" in sys.argv:
        raise SystemExit(memory_fixture_cli(sys.argv[1:]))
    if "--self-test" in sys.argv:
        report = None
        if "--self-test-report" in sys.argv:
            index = sys.argv.index("--self-test-report")
            if index + 1 >= len(sys.argv):
                raise SystemExit(2)
            report = sys.argv[index + 1]
        raise SystemExit(self_test(report))
    Desktop().mainloop()
