"""Deterministic tests for BEAN source-aware small-locus genetics."""
import io
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from bean.bioinformatics.genomics import (
    parse_fasta, clean_dna, describe, translate, compare, virtual_substitution,
    splice, expression, fetch_ncbi, record_experiment, demo,
)


class GenomicsTests(unittest.TestCase):
    def test_parse_fasta_and_provenance(self):
        x = parse_fasta(">geneA synthetic\nATGAAA\nCCC\n>geneB\nATGTAA\n")
        self.assertEqual(set(x), {"geneA", "geneB"})
        self.assertEqual(x["geneA"]["dna"], "ATGAAACCC")
        self.assertEqual(len(x["geneA"]["sha256"]), 64)
        for text in [">A\nATG\n>A\nTAA", ">bad\nAT&", "ATGAAA", ">empty\n"]:
            with self.assertRaises(ValueError):
                parse_fasta(text)

    def test_translate_and_description(self):
        self.assertEqual(translate("ATGAAATGA"), "MK*")
        self.assertEqual(translate("ATGNNNTAA"), "MX*")
        self.assertTrue(describe("ATGAAATGA")["terminal_stop"])
        self.assertEqual(describe("ATGAAATGA")["gene_identity"].split()[0], "Unknown")
        with self.assertRaises(ValueError):
            clean_dna("ZZZ")

    def test_compare_conserved_substitution_indel(self):
        a = compare("ATGAAACCCGGGTAA", "ATGAAATCCGGGTAA")
        self.assertFalse(a["identical"])
        self.assertTrue(a["differences"])
        self.assertTrue(a["conserved_blocks_min3"])
        self.assertTrue(compare("ATG", "ATG")["identical"])
        self.assertTrue(compare("ATGAAACCC", "ATGAAACCCGG")["differences"])
        with self.assertRaises(ValueError):
            compare("ATG" * 4000, "ATG")

    def test_variant_synonymous_missense_stop(self):
        seq = "ATGAAACCCGGGTAA"
        v = virtual_substitution(seq, position=7, alternate="T")
        self.assertEqual(v["coding_effect"], "amino_acid_change")
        self.assertEqual(v["phenotype"], "Unknown")
        self.assertEqual(virtual_substitution("ATGAAATGA", position=6, alternate="G")["coding_effect"], "synonymous")
        self.assertEqual(virtual_substitution("ATGCAA", position=4, alternate="T")["coding_effect"], "stop_gain")
        self.assertEqual(virtual_substitution("ATGAAA", position=1, alternate="G")["coding_effect"], "start_loss")
        with self.assertRaises(ValueError):
            virtual_substitution(seq, position=40, alternate="T")

    def test_splice_requires_annotations(self):
        x = splice("ATGAAAGTACCCCGGGTAA", [(1, 6), (11, 19)])
        self.assertEqual(x["spliced_dna"], "ATGAAACCCGGGTAA")
        self.assertEqual(x["rna"], "AUGAAACCCGGGUAA")
        self.assertIn("Unknown", x["observed_rna_isoform"])
        for coords in [[(1, 9), (8, 19)], [(20, 25)], []]:
            with self.assertRaises(ValueError):
                splice("ATGAAAGTACCCCGGGTAA", coords)

    def test_expression_does_not_invent_significance(self):
        x = expression([10., 12.], [5., 6.], units="TPM")
        self.assertEqual(x["fold_change"], 0.5)
        self.assertEqual(x["statistical_significance"], "Not assessed")
        self.assertEqual(expression([0.], [1.], units="TPM")["direction"], "Unknown")
        with self.assertRaises(ValueError):
            expression([-2.], [3.], units="TPM")

    def test_ncbi_requires_version_ids_and_checks_returned_ids(self):
        class Resp(io.BytesIO):
            def __enter__(self): return self
            def __exit__(self, *args): self.close()
        def fake_opener(req, timeout):
            self.assertIn("id=AY769356.1", req.full_url)
            return Resp(b">AY769356.1 nonpathogenic plant demo reference\nATGAAATGA\n")
        x = fetch_ncbi(["AY769356.1"], opener=fake_opener)
        self.assertIn("AY769356.1", x)
        with self.assertRaises(ValueError):
            fetch_ncbi(["unversioned"], opener=fake_opener)
        with self.assertRaises(ValueError):
            fetch_ncbi(["AY769356.1"], opener=lambda req, timeout: Resp(b">WRONG.1\nATGAAA\n"))

    def test_ledger_idempotent_and_synthetic_demo(self):
        d = demo()
        self.assertEqual(d["data_class"], "synthetic")
        self.assertEqual(d["splice_model"]["spliced_dna"], "ATGAAACCCGGGTAA")
        case = {"experiment_id": "toy-01", "question": "unit test", "prediction": "one", "observation": d,
                "status": "simulated", "source_refs": []}
        with TemporaryDirectory() as td:
            path = Path(td) / "ledger.jsonl"
            r1 = record_experiment(path, case)
            r2 = record_experiment(path, case)
            self.assertFalse(r1["deduplicated"])
            self.assertTrue(r2["deduplicated"])
            rows = path.read_text().splitlines()
            self.assertEqual(len(rows), 1)
            self.assertEqual(json.loads(rows[0])["case"]["status"], "simulated")
            case["status"] = "observed"
            record_experiment(path, case)
            self.assertEqual(len(path.read_text().splitlines()), 2)


if __name__ == "__main__":
    unittest.main()
