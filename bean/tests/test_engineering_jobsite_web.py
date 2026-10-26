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
