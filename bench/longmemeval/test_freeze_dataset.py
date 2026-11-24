import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from . import freeze_dataset as f


class TestDatasetFreeze(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.p = Path(self.folder.name) / "data"
        self.p.write_bytes(b"fixture")
        self.out = Path(self.folder.name) / "ids.json"
        self.sha = hashlib.sha256(b"fixture").hexdigest()
        self.m = {"dataset_sha256": self.sha, "eval_ids": list(range(50)), "dev_ids": list(range(50,100))}

    def test_wrong_size(self):
        with patch.object(f, "freeze") as call:
            with self.assertRaisesRegex(ValueError, "size"):
                f.publish(self.p, self.out)
            call.assert_not_called()
            self.assertFalse(self.out.exists())

    def test_wrong_digest(self):
        with patch.object(f, "DATASET_SIZE", 7), patch.object(f, "freeze") as call:
            with self.assertRaisesRegex(ValueError, "SHA256"):
                f.publish(self.p, self.out)
            call.assert_not_called()
            self.assertFalse(self.out.exists())

    def test_publish_and_no_overwrite(self):
        with patch.object(f, "DATASET_SIZE", 7), patch.object(f, "DATASET_SHA256", self.sha), patch.object(f, "freeze", return_value=self.m):
            f.publish(self.p, self.out)
            self.assertEqual(json.loads(self.out.read_text()), self.m)
            with self.assertRaises(FileExistsError):
                f.publish(self.p, self.out)

    def test_changed_during_freeze(self):
        with patch.object(f, "DATASET_SIZE", 7), patch.object(f, "DATASET_SHA256", self.sha), patch.object(f, "freeze", return_value=dict(self.m, dataset_sha256="bad")):
            with self.assertRaisesRegex(ValueError, "changed"):
                f.publish(self.p, self.out)
            self.assertFalse(self.out.exists())

    def test_overlap(self):
        with patch.object(f, "DATASET_SIZE", 7), patch.object(f, "DATASET_SHA256", self.sha), patch.object(f, "freeze", return_value=dict(self.m, dev_ids=list(range(50)))):
            with self.assertRaisesRegex(ValueError, "ID sets"):
                f.publish(self.p, self.out)
            self.assertFalse(self.out.exists())
