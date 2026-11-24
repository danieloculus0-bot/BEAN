import hashlib
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from . import server_prepare as s


class TestServerPrepare(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.target = Path(directory.name) / "data.json"
        self.data = b"official fixture"
        self.addCleanup(patch.stopall)
        patch.object(s, "DATASET_SIZE", len(self.data)).start()
        patch.object(s, "DATASET_SHA256", hashlib.sha256(self.data).hexdigest()).start()

    def test_good_download(self):
        with patch.object(s, "urlopen", return_value=io.BytesIO(self.data)) as request:
            self.assertEqual(s.fetch_dataset(self.target), self.target)
            request.assert_called_once_with(s.DATASET_URL, timeout=60)
        self.assertEqual(self.target.read_bytes(), self.data)
        self.assertEqual(list(self.target.parent.iterdir()), [self.target])

    def test_bad_downloads_leave_no_file(self):
        for data in (b"short", self.data + b"extra", b"x" * len(self.data)):
            with self.subTest(data=data), patch.object(s, "urlopen", return_value=io.BytesIO(data)):
                with self.assertRaises(ValueError):
                    s.fetch_dataset(self.target)
                self.assertEqual(list(self.target.parent.iterdir()), [])

    def test_network_error_cleans_up(self):
        with patch.object(s, "urlopen", side_effect=OSError("offline")):
            with self.assertRaises(OSError):
                s.fetch_dataset(self.target)
        self.assertEqual(list(self.target.parent.iterdir()), [])

    def test_existing_cache_never_overwritten(self):
        self.target.write_bytes(b"cached")
        with patch.object(s, "urlopen") as request:
            self.assertEqual(s.fetch_dataset(self.target), self.target)
            request.assert_not_called()
        self.assertEqual(self.target.read_bytes(), b"cached")
