"""Integration checks for actual native GUI input in an isolated X11 display."""
from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from bean.desktop.x11 import X11Desktop
from experiments.bean_os.navigate_gui import execute_note_goal, run


class ActualDesktopNavigationTest(unittest.TestCase):
    def test_unsupported_goal_cannot_emit_input(self):
        with tempfile.TemporaryDirectory() as directory:
            desktop = X11Desktop(Path(directory))
            response = execute_note_goal(
                desktop, Path(directory), {"capability": "unknown"})
            self.assertEqual(response["status"], "unknown")
            self.assertEqual(desktop.trace, [])

    def test_real_gui_click_type_save_and_open_through_bean_core(self):
        with tempfile.TemporaryDirectory() as directory:
            report = run(Path(directory))
            self.assertTrue(report["real_gui_events"])
            self.assertFalse(report["real_user_pc_connected"])
            self.assertEqual(report["core_goal_state"], "success", report)
            outcome = report["result"]
            self.assertEqual(outcome["status"], "verified", report)
            self.assertTrue(outcome["file_content_verified"])
            self.assertTrue(outcome["screen_changes_verified"])
            self.assertGreaterEqual(outcome["mouse_clicks"], 2)
            self.assertGreaterEqual(outcome["keyboard_actions"], 4)
            self.assertEqual(len(report["screenshot_files"]), 3)
            for screenshot in report["screenshot_files"]:
                self.assertGreater(Path(screenshot).stat().st_size, 5000)
            self.assertEqual(
                (Path(directory) / "documents" / "bean_test_note.txt"
                ).read_text(encoding="utf-8"),
                "BEAN navigated this real X11 desktop offline.")


if __name__ == "__main__":
    unittest.main()
