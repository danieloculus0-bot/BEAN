"""Synthetic two-receipt contract; CI supplies independently run OS evidence."""
import json
from pathlib import Path
import tempfile
import unittest

from bean.learning.lab026_report import smoke
from bean.learning.bridge_matrix import compare_node_receipts


class CrossPlatformMatrixTests(unittest.TestCase):
    def test_real_bridge_accepts_hashed_reproducible_fixture_results(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            smoke(root/"linux")
            smoke(root/"windows")
            result=compare_node_receipts(
                root/"linux"/"mechanism_receipt.json",
                root/"windows"/"mechanism_receipt.json",
                root/"audit")
            self.assertEqual(len(result["nodes"]),7)
            self.assertFalse(result["learning_demonstrated"])
            self.assertTrue(all(n["outcome"]=="cross_platform_mechanism_reproduced"
                                for n in result["nodes"]))
            self.assertTrue((root/"audit"/"BRIDGE_NODE_MATRIX.md").exists())

    def test_tampered_or_incomplete_evidence_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            smoke(root/"left")
            smoke(root/"right")
            path=root/"right"/"mechanism_receipt.json"
            record=json.loads(path.read_text())
            record["restart_verified"]=False
            path.write_text(json.dumps(record))
            with self.assertRaisesRegex(ValueError,"Incomplete"):
                compare_node_receipts(
                    root/"left"/"mechanism_receipt.json",path,root/"audit")


if __name__=="__main__":
    unittest.main()
