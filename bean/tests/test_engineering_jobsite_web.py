"""Field UI must call the real local BEAN engine and honor material limits."""
from http.server import ThreadingHTTPServer
import json
from pathlib import Path
import tempfile
import threading
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from bean.engineering.jobsite_web import calculate, load_profile, make_handler


class BeanJobsiteWebTests(unittest.TestCase):
    def test_profile_requires_source_and_all_limits(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"project.json"
            data={
                "schema":"bean.jobsite_profile.v1",
                "name":"Example qualified project",
                "limits_source":"Approved design office reference",
                "project_defaults":{"modulus_psi":1200000,
                    "allowable_bending_psi":900,"allowable_shear_psi":135,
                    "deflection_limit_ratio":360}
            }
            p.write_text(json.dumps(data))
            self.assertEqual(load_profile(p)["name"],"Example qualified project")
            del data["limits_source"]
            p.write_text(json.dumps(data))
            with self.assertRaisesRegex(ValueError,"source"):
                load_profile(p)

    def test_profile_cannot_be_overridden_from_browser(self):
        profile={"name":"My project","limits_source":"Document A","project_defaults":{
            "modulus_psi":1200000,"allowable_bending_psi":900,
            "allowable_shear_psi":135,"deflection_limit_ratio":360}}
        member={"id":"A","width_in":1.5,"depth_in":3.5,
                "span_ft":10.,"load_plf":40.}
        payload={"schema":"bean.jobsite_request.v1","operation":"beam_check","members":[member]}
        result=calculate(payload,profile)
        self.assertEqual(result["weakest_member_by_utilization"],"A")
        member["allowable_bending_psi"]=9999999
        with self.assertRaisesRegex(ValueError,"project profile"):
            calculate(payload,profile)

    def test_multiple_members_ranked_and_opening_schedule_via_real_http_dispatch(self):
        project={"name":"Reviewed project","limits_source":"Example signed design sheet",
                 "project_defaults":{"modulus_psi":1200000,
                  "allowable_bending_psi":900,"allowable_shear_psi":135,
                  "deflection_limit_ratio":360}}
        with tempfile.TemporaryDirectory() as tmp:
            server=ThreadingHTTPServer(("127.0.0.1",0),make_handler(project))
            thread=threading.Thread(target=server.serve_forever,daemon=True)
            thread.start()
            try:
                root=f"http://127.0.0.1:{server.server_port}"
                with urlopen(root+"/") as resp:
                    html=resp.read().decode()
                self.assertIn('id="add-opening"',html)
                self.assertIn('id="beam-members"',html)
                self.assertIn('id="beam-template"',html)
                with urlopen(root+"/jobsite.js") as resp:
                    script=resp.read().decode()
                self.assertIn('"wall_layout"',script)
                self.assertIn('"beam-members"',script)
                self.assertIn('result.ranking',script)
                wall={
                    "schema":"bean.jobsite_request.v1","operation":"wall_layout",
                    "length_ft":20,"spacing_in":16,
                    "openings":[{"start_in":64,"width_in":40,
                                 "extra_king_studs_per_side":1,"jack_studs_per_side":1}]
                }
                req=Request(root+"/api/calculate",
                    data=json.dumps(wall).encode(),
                    headers={"Content-Type":"application/json"},method="POST")
                with urlopen(req) as resp:
                    result=json.load(resp)
                self.assertEqual(result["minimum_specified_2x4_pieces_before_other_framing"],18)
                beams={"schema":"bean.jobsite_request.v1","operation":"beam_check",
                       "members":[
                        {"id":"A","width_in":1.5,"depth_in":3.5,"span_ft":2,"load_plf":1},
                        {"id":"B","width_in":1.5,"depth_in":3.5,"span_ft":10,"load_plf":40}]}
                req=Request(root+"/api/calculate",
                    data=json.dumps(beams).encode(),
                    headers={"Content-Type":"application/json"},method="POST")
                with urlopen(req) as resp:
                    result=json.load(resp)
                self.assertEqual(result["ranking"],["B","A"])
                self.assertEqual(result["weakest_member_by_utilization"],"B")
                self.assertFalse(result["building_code_compliant"])
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=3)

    def test_http_endpoint_uses_engine_and_rejects_invalid_calculations(self):
        server=ThreadingHTTPServer(("127.0.0.1",0),make_handler())
        thread=threading.Thread(target=server.serve_forever,daemon=True)
        thread.start()
        try:
            root=f"http://127.0.0.1:{server.server_port}"
            with urlopen(root+"/") as resp:
                html=resp.read().decode()
            self.assertIn("Count 2×4s",html)
            self.assertIn('src="/jobsite.js"',html)
            with urlopen(root+"/jobsite.js") as resp:
                js=resp.read().decode()
            self.assertIn('fetch("/api/calculate"',js)

            payload={"schema":"bean.jobsite_request.v1","operation":"wall_studs",
                     "length_ft":20,"spacing_in":16}
            req=Request(root+"/api/calculate",
                data=json.dumps(payload).encode(),headers={"Content-Type":"application/json"},
                method="POST")
            with urlopen(req) as resp:
                result=json.loads(resp.read())
            self.assertEqual(result["base_full_height_studs"],16)
            payload["spacing_in"]=0
            req=Request(root+"/api/calculate",data=json.dumps(payload).encode(),method="POST")
            with self.assertRaises(HTTPError) as ctx:
                urlopen(req)
            self.assertEqual(ctx.exception.code,400)
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=3)


if __name__=="__main__":
    unittest.main()
