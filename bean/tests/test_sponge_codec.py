import unittest
from bean.optimization.sponge_codec import pack, unpack


class CodecTests(unittest.TestCase):
    def test_roundtrip_reproducible_and_smaller(self):
        q = {str(i): [float(i), -float(i), float(i) / 3] for i in range(1500)}
        a = pack(q)
        self.assertEqual(a, pack(dict(reversed(list(q.items())))))
        self.assertEqual(unpack(a), q)
        self.assertLess(a["compressed_bytes"], a["uncompressed_bytes"])

    def test_tampering_rejected(self):
        original = pack({"state": [1.0, 2.0]})
        for key, value in [
            ("sha256", "0" * 64), ("mnemonic", "bad"),
            ("uncompressed_bytes", 999), ("payload", "x")
        ]:
            altered = dict(original)
            altered[key] = value
            with self.assertRaises(ValueError):
                unpack(altered)

    def test_invalid(self):
        with self.assertRaises(ValueError):
            pack({"state": [float("nan")]})
        with self.assertRaises(ValueError):
            unpack({"format": "old"})


if __name__ == "__main__":
    unittest.main()
