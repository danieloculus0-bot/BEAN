"""No-login public Try BEAN page regression and executable browser memory tests.

This demo is deliberately NOT BEAN Core/SQLite or a hosted ChatGPT API. The
offline tests enforce those labels while demonstrating browser persistence.
"""
from __future__ import annotations

from html.parser import HTMLParser
from pathlib import Path
import re
import shutil
import subprocess
import unittest

ROOT=Path(__file__).resolve().parents[2]
PAGE=ROOT/"docs"/"try-bean.html"
HOME=ROOT/"docs"/"index.html"
JAVASCRIPT=ROOT/"docs"/"try-bean-memory.js"
CHECK=ROOT/"bean"/"tests"/"fixtures"/"try_bean_runtime_check.cjs"

class LinksAndControls(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links=[]
        self.ids=set()
        self.scripts=[]
    def handle_starttag(self,tag,attrs):
        x=dict(attrs)
        if x.get("id"): self.ids.add(x["id"])
        if tag=="a" and x.get("href"): self.links.append(x["href"])
        if tag=="script": self.scripts.append(x)

class PublicTryBEANTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.page=PAGE.read_text(encoding="utf-8")
        cls.home=HOME.read_text(encoding="utf-8")
        cls.js=JAVASCRIPT.read_text(encoding="utf-8")
        cls.parsed=LinksAndControls()
        cls.parsed.feed(cls.page)

    def test_from_homepage(self):
        self.assertIn('id="try-bean"',self.home)
        self.assertIn('href="./try-bean.html"',self.home)
        self.assertIn("Try BEAN without login",self.home)
        self.assertIn("not the Python Core engine",self.home)

    def test_actual_functional_controls_and_scripts(self):
        for key in ("memory-form","memory-subject","memory-statement",
                    "memory-source","memory-query","memory-search",
                    "memory-history","memory-results","memory-context",
                    "memory-recheck","memory-clear","memory-status",
                    "memory-handoff","memory-count","memory-tip"):
            self.assertIn(key,self.parsed.ids,key)
            self.assertIn('getElementById',self.js)
        self.assertEqual(len(self.parsed.scripts),1)
        self.assertEqual(self.parsed.scripts[0].get("src"),"./try-bean-memory.js")
        for feature in ("localStorage","SHA-256","recall","UNVERIFIED",
                        "context","add","verify","clear","location.reload"):
            self.assertIn(feature,self.js)

    def test_no_fake_connector_no_network_or_sensitive_data(self):
        for statement in ("not running BEAN's Python/SQLite Core",
                          "does not connect to ChatGPT",
                          "not a live account connector",
                          "manually","No credentials",
                          "browser-local",
                          "not independently verified",
                          "not yet a publicly hosted ChatGPT connector"):
            self.assertIn(statement.casefold(),self.page.casefold(),statement)
        self.assertIn("user-supplied and unverified",self.js)
        for text in ("fetch(", "XMLHttpRequest", "WebSocket", "EventSource",
                     "apikey", "api_key", "localStorage.setItem('token'"):
            self.assertNotIn(text,self.js)
        for text in ("PAPER TRADING LAB",'id="paperBuy"', "market order",
                     "wallet address","trade-buy","Place a trade"):
            self.assertNotIn(text,self.page)

    def test_source_links_and_approved_mascot(self):
        self.assertIn("./bean-official.webp",self.page)
        self.assertIn("object-fit:contain",self.page)
        for url in (
            "https://github.com/danieloculus0-bot/BEAN/blob/main/examples/restart_continuity.py",
            "https://github.com/danieloculus0-bot/BEAN/blob/main/integrations/chatgpt/README.md",
            "https://github.com/danieloculus0-bot/BEAN",
        ):
            self.assertIn(url,self.parsed.links)
        self.assertTrue((PAGE.parent/"bean-official.webp").is_file())

    def test_valid_html_and_no_embedded_fiction(self):
        self.assertEqual(self.page.count("</html>"),1)
        self.assertEqual(self.page.count("</body>"),1)
        self.assertRegex(self.page,r"</body>\s*</html>\s*\Z")
        self.assertNotRegex(self.page,r"sk-(?:or|proj)-[A-Za-z0-9_-]{12,}")

    @unittest.skipUnless(shutil.which("node"),"Node needed for actual JS runtime test")
    def test_js_runs_and_survives_restart(self):
        js_check=subprocess.run(["node","--check",str(JAVASCRIPT)],capture_output=True,text=True,timeout=20)
        self.assertEqual(js_check.returncode,0,js_check.stderr)
        result=subprocess.run(["node",str(CHECK)],capture_output=True,text=True,timeout=30)
        self.assertEqual(result.returncode,0,result.stdout+"\n"+result.stderr)
        self.assertIn("PASS",result.stdout)

if __name__=="__main__":
    unittest.main()
