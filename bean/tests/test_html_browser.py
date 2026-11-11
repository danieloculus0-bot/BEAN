"""Real isolated Chromium tests for BEAN's local HTML/JS capability.

All fixtures are fully synthetic; no private pages or network destinations.
"""
from __future__ import annotations

import asyncio
from pathlib import Path
import os
import tempfile
import unittest
from unittest.mock import patch

from bean.integration.html_browser import inspect_html


class LocalHtmlBrowserTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.env = patch.dict(os.environ, {
            "BEAN_HTML_ROOT": str(self.root),
            "BEAN_HTML_ALLOWED_ORIGINS": "",
        })
        self.env.start()
        self.addCleanup(self.env.stop)
        (self.root / "script.js").write_text(
            "window.namedFromExternal = 'Linked JavaScript loaded';",
            encoding="utf-8",
        )
        self.doc = self.root / "synthetic.html"
        self.doc.write_text(
            """<!doctype html><html lang="en"><head><title>BEAN Test</title>
            <script src="script.js"></script>
            <script>
            document.addEventListener('DOMContentLoaded', () => {
              document.querySelector('#result').textContent =
                window.namedFromExternal || 'Linked script missing';
            });
            function change() {
              document.querySelector('#result').textContent =
                document.querySelector('#answer').value || 'Clicked';
            }
            fetch('https://unlisted.invalid/data').catch(() => {});
            const deniedSocket = new WebSocket('wss://unlisted.invalid/ws');
            deniedSocket.onerror = () => {};
            </script>
            </head><body><h1>Untrusted page fixture</h1>
            <input id="answer" value=""/>
            <button id="go" onclick="change()">Go</button>
            <div id="result">Unchanged</div></body></html>""",
            encoding="utf-8",
        )

    def test_inspect_source_inline_script_without_executing(self):
        result = inspect_html(str(self.doc))
        self.assertEqual(result["schema"], "bean.local.html_browser.v1")
        self.assertFalse(result["scripts_executed"])
        self.assertEqual(result["target_kind"], "local_file")
        self.assertIn("Unchanged", result["rendered_text"])
        self.assertNotIn("Linked JavaScript loaded", result["rendered_text"])
        self.assertIn("change()", result["source_excerpt"])
        self.assertEqual(result["script_count_visible"], 2)
        self.assertEqual([x["kind"] for x in result["scripts"]], ["external", "inline"])
        self.assertIn("function change()", result["scripts"][1]["code"])
        self.assertIn("namedFromExternal", result["scripts"][0]["code"])
        self.assertEqual(len(result["scripts"][0]["source_sha256"]), 64)
        self.assertEqual(len(result["source_sha256"]), 64)

    def test_executes_html_js_linked_script_and_interacts_with_controls(self):
        before = inspect_html(str(self.doc), execute_scripts=True, wait_ms=150)
        self.assertIn("Linked JavaScript loaded", before["rendered_text"])
        self.assertGreaterEqual(before["blocked_request_count"], 1)
        self.assertIn("https", before["blocked_request_schemes"])
        self.assertIn("websocket", before["blocked_request_schemes"])
        after = inspect_html(str(self.doc), execute_scripts=True,
                             actions=[
                                 {"type": "fill", "selector": "#answer", "value": "42"},
                                 {"type": "click", "selector": "#go"},
                             ], wait_ms=150)
        self.assertIn("42", after["rendered_text"])
        self.assertEqual(after["actions_performed"], 2)
        self.assertNotEqual(before["dom_sha256"], after["dom_sha256"])

    def test_authorized_file_picker_reads_local_csv_without_private_write(self):
        csv_path = self.root / "fake.csv"
        csv_path.write_text("Item,Qty\nWidget,3\n", encoding="utf-8")
        page = self.root / "file-picker.html"
        page.write_text(
            """<!doctype html><title>Picker</title><button id="open">Open</button>
            <p id="loaded">Unloaded</p><script>
            document.getElementById('open').addEventListener('click', () => {
              const input = document.createElement('input');
              input.type = 'file';
              input.onchange = async () => {
                document.getElementById('loaded').textContent =
                  (await input.files[0].text()).trim();
              };
              input.click();
            });
            </script>""", encoding="utf-8",
        )
        result = inspect_html(str(page), execute_scripts=True,
                              actions=[{"type": "choose_file", "selector": "#open",
                                        "value": str(csv_path)}], wait_ms=200)
        self.assertIn("Widget,3", result["rendered_text"])
        self.assertEqual(result["actions_performed"], 1)
        self.assertEqual(csv_path.read_text(encoding="utf-8"), "Item,Qty\nWidget,3\n")

    def test_restricts_root_network_and_action_inputs(self):
        outside = self.root.parent / "unapproved-html-fixture.html"
        # No need to create outside the root; access must fail before browser.
        with self.assertRaisesRegex(ValueError, "inside BEAN_HTML_ROOT"):
            inspect_html(str(outside))
        with self.assertRaisesRegex(ValueError, "origin is not permitted"):
            inspect_html("https://example.com/")
        with self.assertRaisesRegex(ValueError, "requires execute_scripts"):
            inspect_html(str(self.doc), actions=[{"type": "click", "selector": "#go"}])
        with self.assertRaisesRegex(ValueError, "bounded"):
            inspect_html(str(self.doc), execute_scripts=True,
                         actions=[{"type": "fill", "selector": "#answer", "value": "x" * 1025}])
        with patch.dict(os.environ, {"BEAN_HTML_ROOT": ""}):
            with self.assertRaisesRegex(ValueError, "Configure BEAN_HTML_ROOT"):
                inspect_html(str(self.doc))


class LocalHtmlMcpContractTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.doc = self.root / "mcp.html"
        self.doc.write_text(
            '<!doctype html><title>Tool test</title><p id="value">Before</p>'
            '<script>document.querySelector("#value").textContent="After"</script>',
            encoding="utf-8",
        )
        self.env = patch.dict(os.environ, {
            "BEAN_HTML_ROOT": str(self.root),
            "BEAN_HTML_ALLOWED_ORIGINS": "",
        })
        self.env.start()
        self.addCleanup(self.env.stop)

    def test_actual_local_mcp_registration_and_tool_calls(self):
        from integrations.chatgpt.local_html_server import mcp

        async def exercise():
            registered = await mcp.list_tools()
            self.assertEqual(
                {tool.name for tool in registered},
                {"bean_html_inspect", "bean_html_run"},
            )
            for tool in registered:
                wire = tool.annotations.model_dump(by_alias=True, exclude_none=True)
                self.assertFalse(wire.get("openWorldHint", False))
            result = await mcp.call_tool("bean_html_inspect", {"target": str(self.doc)})
            self.assertFalse(result.is_error)
            self.assertFalse(result.structured_content["scripts_executed"])
            self.assertIn("Before", result.structured_content["rendered_text"])
            result = await mcp.call_tool("bean_html_run", {"target": str(self.doc)})
            self.assertFalse(result.is_error)
            self.assertTrue(result.structured_content["scripts_executed"])
            self.assertIn("After", result.structured_content["rendered_text"])
        asyncio.run(exercise())


if __name__ == "__main__":
    unittest.main()
