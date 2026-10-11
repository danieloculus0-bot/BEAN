import unittest
from bean.memory.compression import file_memory, recover_memory, score_evidence

class MemoryCompressionTests(unittest.TestCase):
    def test_scored_roundtrip_and_determinism(self):
        data={"values":[{"state":i%3,"reward":i%5} for i in range(2000)]}
        a=file_memory(data,accuracy=.9,relevance=.85,provenance=.8,sample_count=200)
        self.assertEqual(a,file_memory(data,accuracy=.9,relevance=.85,provenance=.8,sample_count=200))
        self.assertEqual(recover_memory(a,require_eligible=True),data)
        self.assertLess(a["compressed_bytes"],a["raw_bytes"])
        self.assertGreater(a["score"]["value"],60)
        self.assertFalse(a["score"]["verified"])
    def test_unscored_or_low_quality(self):
        with self.assertRaises(ValueError):
            file_memory({"x":1},accuracy=float("nan"),relevance=.8,provenance=.9,sample_count=200)
        a=file_memory({"x":1},accuracy=0,relevance=0,provenance=0,sample_count=0)
        self.assertEqual(recover_memory(a),{"x":1})
        with self.assertRaises(ValueError):
            recover_memory(a,require_eligible=True)
    def test_modified_bytes_rejected(self):
        a=file_memory({"x":1},accuracy=1,relevance=1,provenance=1,sample_count=200)
        for field,value in (("sha256","0"*64),("mnemonic","bad"),("payload","bad"),("raw_bytes",9999)):
            b=dict(a);b[field]=value
            with self.assertRaises(ValueError):
                recover_memory(b)
    def test_score_limits(self):
        with self.assertRaises(ValueError):
            score_evidence(accuracy=1.1,relevance=1,provenance=1,sample_count=30)

if __name__=="__main__":
    unittest.main()
