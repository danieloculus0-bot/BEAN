import hashlib
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from bean.optimization.autodev import canonical
from bean.runtime.retained_catalog_worker import dispatch,source_function,oracle

class CatalogTests(unittest.TestCase):
    def test_dynamic_reuse_and_independent_check(self):
        expr=["reverse","even_positions"]
        name="sequence_"+hashlib.sha256(canonical(expr)).hexdigest()[:16]
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            with sqlite3.connect(root/"verified_skills.sqlite") as db:
                db.execute("CREATE TABLE verified_skills(name,objective,source,sha256)")
            def install(source):
                sha=hashlib.sha256(source.encode()).hexdigest()
                with sqlite3.connect(root/"verified_skills.sqlite") as db:
                    db.execute("DELETE FROM verified_skills")
                    db.execute("INSERT INTO verified_skills VALUES(?,?,?,?)",(name,"a"*64,source,sha))
                row={"skill":name,"expression":expr,"candidate_sha256":sha,"objective_sha256":"a"*64,"passed":True,"acquisition_passed":True,"transfer":{"passed":True,"fresh_process":True,"source_sha256":sha},"transfer_count":20}
                (root/"sequence_cycles.jsonl").write_text(json.dumps(row)+"\n")
                return {"op":"execute","name":name,"source_sha256":sha,"values":[1,-2,3,4,4]}
            request=install("def solve(values):\n    return values[::-1][::2]\n")
            self.assertEqual(dispatch(root,{"op":"list","kind":"sequence","limit":12})["count"],1)
            self.assertEqual(dispatch(root,request)["value"],[4,3,1])
            bad=install("def solve(values):\n    return values\n")
            with self.assertRaises(ValueError):dispatch(root,bad)
            with self.assertRaises(ValueError):dispatch(root,request)
    def test_no_unsafe_source(self):
        for source in ("import os\ndef solve(values):return values","def solve(values):return values.__class__","def solve(values):return open('x')","def solve(values, x=1):return values","def solve(values):return __import__('os')"):
            with self.assertRaises(ValueError):source_function(source)
    def test_numeric_oracle(self):
        self.assertAlmostEqual(oracle("numeric",["div","mean","rms"],[3,4]),3.5/(12.5**.5))
        with self.assertRaises(ValueError):oracle("numeric",["div","mean","rms"],[0])
