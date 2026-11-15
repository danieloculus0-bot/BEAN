#!/usr/bin/env python3
"""An actual Tk/X11 desktop for BEAN to navigate with OS-level input events.

Contains real separate windows and a sandboxed text document editor/browser.
Only files inside --sandbox are ever created or read. This is a GUI fixture,
not a replacement for a Linux desktop environment.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import re
import tkinter as tk


def launch(sandbox: Path) -> None:
    sandbox.mkdir(parents=True, exist_ok=True)
    root = tk.Tk()
    root.title("BEAN OS Lab")
    root.geometry("760x480+110+80")
    root.configure(bg="#18251f")
    tk.Label(root, text="BEAN OS  |  Desktop", fg="#d3f7d3",
             bg="#18251f", font=("DejaVu Sans", 23, "bold")).place(
                 relx=.5, rely=.14, anchor="center")

    def open_notes() -> None:
        notes = tk.Toplevel(root)
        notes.title("BEAN Notes")
        notes.geometry("720x450+250+160")
        filename = tk.Entry(notes, font=("DejaVu Sans", 14))
        filename.pack(fill="x", padx=24, pady=(24, 10))
        filename.insert(0, "")
        editor = tk.Text(notes, width=58, height=13, font=("DejaVu Sans", 12))
        editor.pack(fill="both", expand=True, padx=24)

        feedback = tk.Label(notes, text="Type filename and note, then Ctrl+S")
        feedback.pack(pady=9)

        def save(event=None):
            name = filename.get().strip()
            if not re.fullmatch(r"[A-Za-z0-9_-]{1,48}\.txt", name):
                feedback.configure(text="Invalid filename")
                return
            (sandbox / name).write_text(editor.get("1.0", "end-1c"), encoding="utf-8")
            feedback.configure(text="Saved: " + name)

        notes.bind("<Control-s>", save)
        notes.bind("<Escape>", lambda event: notes.destroy())
        notes.after(200, filename.focus_force)

    def open_files() -> None:
        files = tk.Toplevel(root)
        files.title("BEAN Files")
        files.geometry("700x420+250+160")
        tk.Label(files, text="Documents", font=("DejaVu Sans", 17)).pack(pady=12)
        listing = tk.Listbox(files, width=65, height=15, font=("DejaVu Sans", 12))
        listing.pack(fill="both", expand=True, padx=24, pady=8)
        for document in sorted(sandbox.glob("*.txt")):
            listing.insert("end", document.name)
        if listing.size():
            listing.selection_set(0)
            listing.activate(0)

        def open_selected(event=None) -> None:
            current = listing.curselection()
            if not current:
                return
            name = listing.get(current[0])
            doc = sandbox / name
            if not doc.is_file():
                return
            view = tk.Toplevel(root)
            view.title("BEAN Viewer: " + name)
            view.geometry("650x350+350+210")
            tk.Label(view, text=name, font=("DejaVu Sans", 16)).pack(pady=12)
            text = tk.Text(view, font=("DejaVu Sans", 12), wrap="word")
            text.pack(fill="both", expand=True, padx=18, pady=12)
            text.insert("1.0", doc.read_text(encoding="utf-8"))
            text.configure(state="disabled")

        listing.bind("<Return>", open_selected)
        listing.bind("<Double-Button-1>", open_selected)
        files.bind("<Escape>", lambda event: files.destroy())
        files.after(220, listing.focus_force)

    def button(label: str, y: float, handler):
        tk.Button(root, text=label, command=handler,
                  font=("DejaVu Sans", 17), width=18, height=1,
                  bg="#e1eee0", activebackground="#b5debd").place(
                      relx=.5, rely=y, anchor="center")

    button("Open Notes", .34, open_notes)
    button("Open Files", .56, open_files)
    tk.Label(root, text="Real windows, real mouse, real keyboard, isolated files",
             fg="#b1c6b5", bg="#18251f", font=("DejaVu Sans", 10)).place(
                 relx=.5, rely=.88, anchor="center")
    root.mainloop()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sandbox", type=Path, required=True)
    args = parser.parse_args()
    launch(args.sandbox)


if __name__ == "__main__":
    main()
