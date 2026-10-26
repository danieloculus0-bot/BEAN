"""Pocket-simple local BEAN Jobsite UI backed by the *actual* BEAN Python math.

Run: python -m bean.engineering.jobsite_web
Open: http://127.0.0.1:8765

This loopback-only tool is not an Internet or LAN service. Deployment to field
tablets requires an authenticated HTTPS host; never bind this unauthenticated
development service to 0.0.0.0.
"""
from __future__ import annotations

import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib.resources import files
import json
from pathlib import Path

from .jobsite import _number, evaluate_request

MAX_REQUEST_BYTES = 32768
PROFILE_KEYS = (
    "modulus_psi", "allowable_bending_psi", "allowable_shear_psi",
    "deflection_limit_ratio",
)


def load_profile(path):
    """Require material/screen values and provenance from a reviewed project."""
    if path is None:
        return None
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict) or data.get("schema") != "bean.jobsite_profile.v1":
        raise ValueError("Project profile must use bean.jobsite_profile.v1")
    name = data.get("name")
    source = data.get("limits_source")
    if not isinstance(name, str) or not name.strip() or len(name) > 120:
        raise ValueError("Project profile needs a meaningful name")
    if not isinstance(source, str) or not source.strip() or len(source) > 400:
        raise ValueError("Profile must identify the externally established source of limits")
    limits = data.get("project_defaults")
    if not isinstance(limits, dict) or set(limits) != set(PROFILE_KEYS):
        raise ValueError("Profile must give explicit modulus, bending, shear and deflection limits")
    for field in PROFILE_KEYS:
        _number(limits[field],field)
    if limits["deflection_limit_ratio"] <= 1:
        raise ValueError("Deflection denominator must be above one")
    return data


def calculate(payload, profile=None):
    """Dispatch the UI request to BEAN itself; no browser-side equation copy."""
    if not isinstance(payload, dict):
        raise ValueError("Calculation must be a JSON object")
    if profile and payload.get("operation") == "beam_check":
        # Project defaults are established at the server, not by a browser.
        if payload.get("project_defaults"):
            raise ValueError("Field request cannot override installed project limits")
        members = payload.get("members")
        if not isinstance(members, list):
            raise ValueError("Beam input must include members")
        for member in members:
            if not isinstance(member, dict) or any(k in member for k in PROFILE_KEYS):
                raise ValueError("Material limits come from the installed project profile")
        payload = {**payload, "project_defaults": profile["project_defaults"]}
    return evaluate_request(payload)


def make_handler(profile=None):
    class JobsiteHandler(BaseHTTPRequestHandler):
        def _send(self, status, data, content_type="application/json; charset=utf-8"):
            body = (json.dumps(data, separators=(",", ":")).encode("utf-8")
                    if isinstance(data, (dict,list)) else data)
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; connect-src 'self'; frame-ancestors 'none'")
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            if self.path == "/":
                with files("bean.engineering").joinpath("jobsite_page.html").open("rb") as fh:
                    self._send(200, fh.read(), "text/html; charset=utf-8")
            elif self.path == "/jobsite.js":
                with files("bean.engineering").joinpath("jobsite_page.js").open("rb") as fh:
                    self._send(200, fh.read(), "text/javascript; charset=utf-8")
            elif self.path == "/api/profile":
                self._send(200, {
                    "profile_installed": profile is not None,
                    "name": profile["name"] if profile else None,
                    "limits_source": profile["limits_source"] if profile else None,
                })
            else:
                self._send(404, {"error":"Not found"})

        def do_POST(self):
            if self.path != "/api/calculate":
                self._send(404, {"error":"Not found"})
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if not 0 < length <= MAX_REQUEST_BYTES:
                    raise ValueError("Calculation request has invalid length")
                payload = json.loads(self.rfile.read(length))
                result = calculate(payload, profile)
            except (ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
                self._send(400, {"error":str(exc)})
            else:
                self._send(200, result)

    return JobsiteHandler


def main():
    parser = argparse.ArgumentParser(description="Local BEAN Jobsite web app")
    parser.add_argument("--port",type=int,default=8765)
    parser.add_argument("--profile",help="Reviewed JSON with project-specific material limits")
    args=parser.parse_args()
    profile = load_profile(args.profile)
    with ThreadingHTTPServer(("127.0.0.1", args.port),make_handler(profile)) as server:
        print(f"BEAN Jobsite running locally: http://127.0.0.1:{server.server_port}")
        print("Local engineering screening only; no Internet or LAN access exposed.")
        server.serve_forever()


if __name__ == "__main__":
    main()
