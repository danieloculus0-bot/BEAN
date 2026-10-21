"""Execute BEAN navigation tools against the *actual* Axiom Flask application.

CI checks out Axiom at an explicit commit. This test uses a disposable local
database and real HTTP, but no public service, cloud model, or user data.
"""
from __future__ import annotations

import os
from pathlib import Path
import tempfile
import threading
import unittest
from importlib.util import find_spec

from integrations.chatgpt.axiom_navigation import AxiomNavigationClient

try:
    from werkzeug.serving import make_server
except ImportError:
    make_server = None


@unittest.skipUnless(find_spec("superforge") is not None and make_server is not None,
                     "Real Axiom checkout/Flask required, verified in cross-repo CI")
class CrossRepositoryFavoritesTests(unittest.TestCase):
    def test_real_axiom_http_persistence_and_chatgpt_navigation(self):
        from superforge.app import create_app

        with tempfile.TemporaryDirectory() as root:
            old = os.environ.get("AXIOM_DATA_DIR")
            os.environ["AXIOM_DATA_DIR"] = str(Path(root) / "axiom_data")
            try:
                app = create_app({"TESTING": True})
                server = make_server("127.0.0.1", 0, app)
                thread = threading.Thread(target=server.serve_forever, daemon=True)
                thread.start()
                try:
                    client = AxiomNavigationClient(
                        origin="http://127.0.0.1:" + str(server.server_port))
                    matches = client.find("Quality")
                    self.assertTrue(matches["ok"])
                    self.assertEqual(matches["items"][0]["href"], "/quality")
                    self.assertEqual(client.list()["items"], [])
                    self.assertTrue(client.pin("quality")["saved"])
                    self.assertEqual(client.list()["items"][0]["key"], "quality")
                    self.assertTrue(client.pin("quality")["saved"])
                    self.assertFalse(client.pin("quality")["created"])
                    self.assertTrue(client.remove("quality")["removed"])
                    self.assertEqual(client.list()["items"], [])
                finally:
                    server.shutdown()
                    thread.join(timeout=10)
                    server.server_close()
                # Confirm the saved item survives a full new Flask app instance.
                from superforge.favorites import add_favorite
                self.assertTrue(add_favorite("bean")["saved"])
                new_app = create_app({"TESTING": True})
                favorites = new_app.test_client().get("/api/favorites").get_json()["items"]
                self.assertEqual(favorites[0]["href"], "/intelligence")
            finally:
                if old is None:
                    os.environ.pop("AXIOM_DATA_DIR", None)
                else:
                    os.environ["AXIOM_DATA_DIR"] = old


if __name__ == "__main__":
    unittest.main()
