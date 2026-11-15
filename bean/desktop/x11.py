"""Real X11 GUI input adapter for BEAN OS desktop experiments.

This operates actual windows and sends actual OS mouse/keyboard events. It is
opt-in and instantiated only by a trusted local host with DISPLAY configured.
X11 today; Wayland, native accessibility and screen interpretation are future
backends. No shell command is derived from an agent instruction.
"""
from __future__ import annotations

from hashlib import sha256
import os
from pathlib import Path
import shutil
import subprocess
import time


class X11Desktop:
    def __init__(self, evidence_dir: str | Path):
        if not os.environ.get("DISPLAY") or os.environ.get("XDG_SESSION_TYPE") == "wayland":
            raise RuntimeError("X11 DISPLAY required for this desktop adapter")
        for executable in ("wmctrl", "scrot"):
            if not shutil.which(executable):
                raise RuntimeError(f"Missing local desktop dependency: {executable}")
        # Import after checking DISPLAY; pyautogui initializes the live X server.
        import pyautogui
        self.ui = pyautogui
        self.ui.PAUSE = 0.10
        self.ui.FAILSAFE = True
        self.evidence_dir = Path(evidence_dir)
        self.evidence_dir.mkdir(parents=True, exist_ok=True)
        self.trace: list[dict] = []

    @staticmethod
    def _command(*args: str) -> str:
        result = subprocess.run(
            list(args), capture_output=True, text=True, check=True, timeout=8)
        return result.stdout

    def windows(self) -> list[dict]:
        """Observe real window-manager top-level titles and screen geometry."""
        raw = self._command("wmctrl", "-lG")
        found = []
        for line in raw.splitlines():
            parts = line.split(maxsplit=7)
            if len(parts) != 8:
                continue
            handle, desktop, x, y, width, height, host, title = parts
            found.append({
                "id": handle, "title": title, "x": int(x), "y": int(y),
                "width": int(width), "height": int(height),
            })
        return found

    def find(self, title: str) -> dict | None:
        return next((w for w in self.windows() if w["title"] == title), None)

    def wait_for(self, title: str, timeout: float = 8.0) -> dict:
        until = time.monotonic() + timeout
        while time.monotonic() < until:
            window = self.find(title)
            if window:
                return window
            time.sleep(.15)
        raise TimeoutError(f"Expected GUI window not visible: {title}")

    def focus(self, title: str) -> dict:
        window = self.wait_for(title)
        self._command("wmctrl", "-ia", window["id"])
        time.sleep(.23)
        self.trace.append({"action": "focus", "window": title})
        return self.wait_for(title)

    def click_relative(self, title: str, x: float, y: float):
        if not (0 < x < 1 and 0 < y < 1):
            raise ValueError("Relative click must fall within a window")
        window = self.focus(title)
        px = window["x"] + int(window["width"] * x)
        py = window["y"] + int(window["height"] * y)
        self.ui.click(px, py)
        self.trace.append({"action": "mouse_click", "window": title,
                           "screen_x": px, "screen_y": py})

    def type_text(self, value: str):
        if not isinstance(value, str) or not 0 < len(value) <= 1000:
            raise ValueError("Nonempty bounded text required")
        self.ui.write(value, interval=.004)
        self.trace.append({"action": "keyboard_type", "length": len(value)})

    def press(self, key: str):
        if key not in ("tab", "enter", "esc"):
            raise ValueError("Unregistered navigation key")
        self.ui.press(key)
        self.trace.append({"action": "keyboard_key", "key": key})

    def save_shortcut(self):
        self.ui.hotkey("ctrl", "s")
        self.trace.append({"action": "keyboard_shortcut", "key": "ctrl+s"})

    def screenshot(self, label: str) -> dict:
        if not label.replace("_", "").isalnum() or len(label) > 40:
            raise ValueError("Invalid screenshot identifier")
        path = self.evidence_dir / (label + ".png")
        self._command("scrot", str(path))
        data = path.read_bytes()
        observation = {
            "kind": "real_x11_screenshot",
            "file": str(path), "sha256": sha256(data).hexdigest(),
            "bytes": len(data),
            "visible_windows": [w["title"] for w in self.windows()],
        }
        self.trace.append({"action": "screen_observe", **observation})
        return observation
