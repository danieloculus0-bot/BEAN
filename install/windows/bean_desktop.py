"""Windows desktop entry point. Bundled with the existing BEAN core, no Python required."""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import threading
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


class Desktop(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("BEAN | Evidence-first AI")
        self.geometry("790x565")
        self.minsize(600, 420)
        self.configure(bg="#131c1b")
        self.client = None
        self.conversation = None
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
        self.status = tk.StringVar(value="Ready. Offline core verification works without Ollama.")
        tk.Label(self, textvariable=self.status, bg=bg, fg=green,
                 anchor="w", wraplength=735).pack(fill="x", padx=22, pady=8)
        self.transcript = scrolledtext.ScrolledText(self, bg="#1e2b28", fg=fg,
                insertbackground=fg, font=("Consolas", 10), wrap="word")
        self.transcript.pack(fill="both", expand=True, padx=20, pady=(0, 8))
        self.transcript.insert("end", "BEAN technical beta installed. The offline Core test "
                               "uses fictional fixtures, not a trained model.\n"
                               "Optional Ollama chat uses an already-running model on this PC. "
                               "Chat turns are NOT saved in BEAN Core memory across restarts.\n\n"
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

    def connect(self):
        self.status.set("Connecting to local Ollama...")
        def load():
            client = OllamaClient("http://127.0.0.1:11434")
            model = client.select_model(None)
            prompt, _ = system_prompt(None)
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
        self.status.set("BEAN is thinking...")
        def ready(reply):
            self.append("BEAN: " + reply + "\n")
            self.status.set("Ready")
        self.background(lambda: self.conversation.reply(text), ready)


if __name__ == "__main__":
    if "--self-test" in sys.argv:
        report = None
        if "--self-test-report" in sys.argv:
            index = sys.argv.index("--self-test-report")
            if index + 1 >= len(sys.argv):
                raise SystemExit(2)
            report = sys.argv[index + 1]
        raise SystemExit(self_test(report))
    Desktop().mainloop()
