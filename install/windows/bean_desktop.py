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

import psutil  # noqa: F401 - bundle the dependency used by Core

if getattr(sys, "frozen", False):
    sys.path.insert(0, sys._MEIPASS)


def proof_result():
    from examples.capability_proof import run_proof
    return run_proof()


def self_test() -> int:
    try:
        result = proof_result()
        print(json.dumps(result, indent=2))
        return 0 if result.get("status") == "PASS" else 1
    except Exception as exc:
        print("BEAN self-test failed: " + repr(exc), file=sys.stderr)
        return 1


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
        tk.Label(self, text="Evidence-first reasoning  |  Local Windows desktop",
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
        self.transcript.insert("end", "BEAN is installed. Run the offline core verification, "
                               "or connect to an Ollama server already running on this PC.\n\n"
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
            from bean.voice.ollama import OllamaClient
            from bean.voice.chat import BeanConversation
            from bean.voice.persona import system_prompt
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
        raise SystemExit(self_test())
    Desktop().mainloop()
