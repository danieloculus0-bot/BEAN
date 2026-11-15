#!/usr/bin/env python3
"""Real GUI navigation by a BEAN Core registered goal action (X11 only).

Unlike the numeric simulation, this drives an actual desktop GUI using
window-manager discovery, real mouse events, typing, hotkeys, and screenshots.
The initial goal is supplied by a trusted host; BEAN does NOT yet discover
new GUI procedures or understand arbitrary screenshots. All files are synthetic.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys
import time
import uuid

from bean.desktop.x11 import X11Desktop
from bean.memory.store import init_store, get_store
from bean.runtime.goal_cycle import GoalCycle


def execute_note_goal(desktop: X11Desktop, sandbox: Path, detail: dict) -> dict:
    if not isinstance(detail, dict) or detail.get("capability") != "gui_create_and_open_note":
        return {"status": "unknown", "reason": "unsupported_gui_goal"}
    filename, body = detail.get("filename"), detail.get("body")
    if (not isinstance(filename, str) or filename != "bean_test_note.txt"
            or not isinstance(body, str) or not 0 < len(body) <= 300
            or not body.isascii() or "\n" in body):
        return {"status": "unknown", "reason": "invalid_demo_goal"}
    # All screen coordinates are derived from fresh window geometry. The two
    # relative positions are fixture-specific known controls, not visual AI.
    desktop.wait_for("BEAN OS Lab")
    initial = desktop.screenshot("initial_desktop")
    desktop.click_relative("BEAN OS Lab", .50, .34)
    desktop.wait_for("BEAN Notes")
    desktop.focus("BEAN Notes")
    time.sleep(.35)
    desktop.type_text(filename)
    desktop.press("tab")
    desktop.type_text(body)
    desktop.save_shortcut()
    destination = sandbox / filename
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline and (
            not destination.is_file() or destination.read_text(encoding="utf-8") != body):
        time.sleep(.10)
    if not destination.is_file() or destination.read_text(encoding="utf-8") != body:
        return {"status": "failed", "reason": "note_not_saved_via_gui",
                "trace": desktop.trace}
    saved = desktop.screenshot("note_saved")
    desktop.press("esc")
    desktop.focus("BEAN OS Lab")
    desktop.click_relative("BEAN OS Lab", .50, .56)
    desktop.wait_for("BEAN Files")
    desktop.focus("BEAN Files")
    time.sleep(.35)
    desktop.press("enter")
    viewer_title = "BEAN Viewer: " + filename
    desktop.wait_for(viewer_title)
    viewer = desktop.screenshot("viewer_open")
    return {
        "status": "verified",
        "source": "real_x11_gui_and_isolated_filesystem",
        "navigated_windows": ["BEAN OS Lab", "BEAN Notes",
                              "BEAN Files", viewer_title],
        "mouse_clicks": sum(e["action"] == "mouse_click" for e in desktop.trace),
        "keyboard_actions": sum(e["action"].startswith("keyboard_")
                                for e in desktop.trace),
        "file_sha256": sha256(destination.read_bytes()).hexdigest(),
        "initial_screen_sha256": initial["sha256"],
        "saved_screen_sha256": saved["sha256"],
        "viewer_screen_sha256": viewer["sha256"],
        "file_content_verified": True,
        "screen_changes_verified": len({initial["sha256"], saved["sha256"],
                                         viewer["sha256"]}) == 3,
    }


def run(sandbox: Path, *, body: str = "BEAN navigated this real X11 desktop offline.") -> dict:
    sandbox = sandbox.resolve()
    sandbox.mkdir(parents=True, exist_ok=True)
    evidence = sandbox / "screenshots"
    application = subprocess.Popen(
        [sys.executable, "-m", "experiments.bean_os.gui_lab_app",
         "--sandbox", str(sandbox / "documents")],
        stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
    )
    (sandbox / "documents").mkdir(exist_ok=True)
    try:
        desktop = X11Desktop(evidence)
        desktop.wait_for("BEAN OS Lab")
        init_store(str(sandbox / "bean_core_memory.db"))
        cycle = GoalCycle({
            "gui_navigate": lambda goal: execute_note_goal(
                desktop, sandbox / "documents", goal["action_detail"])
        })
        goal_id = str(uuid.uuid4())
        conn = get_store()._conn()
        # The trusted demo host requests this explicit goal; it is not
        # presented as a self-generated open-ended plan.
        conn.execute(
            "INSERT INTO cognition_goal_proposals "
            "(proposal_id,session_uuid,goal_state,action_type,action_detail,"
            "motivation,priority,approval_required,status) "
            "VALUES (?,?,?,?,?,?,?,?,?)",
            (goal_id, "gui-demo", "create_note_and_verify_viewer",
             "gui_navigate",
             json.dumps({"capability": "gui_create_and_open_note",
                         "filename": "bean_test_note.txt", "body": body}),
             "trusted_host_gui_navigation_demo", 1, "none", "pending"))
        conn.commit()
        receipts = cycle.poll_due(max_goals=1)
        state = cycle.history(limit=1)
        if len(receipts) != 1 or len(state) != 1:
            raise AssertionError("BEAN Core did not process desktop goal")
        outcome = json.loads(state[0]["result_json"] or "null")
        return {
            "schema": "bean.os.real_gui_navigation.v1",
            "backend": "X11_Xvfb_Tk",
            "real_gui_events": True,
            "real_user_pc_connected": False,
            "model_used": False,
            "task_origin": "trusted_host",
            "core_goal_receipt": receipts[0],
            "core_goal_state": state[0]["state"],
            "result": outcome,
            "screenshot_files": sorted(str(p) for p in evidence.glob("*.png")),
        }
    finally:
        application.terminate()
        try:
            application.wait(timeout=4)
        except subprocess.TimeoutExpired:
            application.kill()
            application.wait(timeout=4)
        try:
            get_store().close()
        except RuntimeError:
            pass


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sandbox", type=Path, default=Path("artifacts/bean-gui-nav"))
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = run(args.sandbox)
    report = json.dumps(result, indent=2, sort_keys=True)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(report + "\n", encoding="utf-8")
    print(report)
    valid = (result["core_goal_state"] == "success"
             and result["result"] is not None
             and result["result"].get("file_content_verified") is True
             and result["result"].get("screen_changes_verified") is True
             and result["result"].get("mouse_clicks", 0) >= 2
             and result["result"].get("keyboard_actions", 0) >= 4
             and len(result["screenshot_files"]) == 3)
    if not valid:
        raise SystemExit("BEAN graphical desktop navigation did not verify")


if __name__ == "__main__":
    main()
