"""BEAN 3D Studio: localhost-only image-to-mesh adapter for upstream TripoSR.

This module is infrastructure, not a bundled neural model. TripoSR is installed
separately by its operator under its own MIT license. Python stdlib only here.
"""
from __future__ import annotations

import base64
import binascii
import io
import json
import math
import os
from pathlib import Path
import re
import struct
import subprocess
import sys
import tempfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

REPO_ROOT = Path(__file__).resolve().parents[2]
DOCS = REPO_ROOT / "docs"
MAX_IMAGE_BYTES = 8 * 1024 * 1024
MAX_REQUEST_BYTES = 12 * 1024 * 1024
MAX_TRIANGLES = 500_000
IMAGE_RE = re.compile(r"^data:image/(png|jpeg);base64,([A-Za-z0-9+/=\r\n]+)$")
PORT = 8768


def model_script() -> Path | None:
    """Return the actual installed upstream inference script, if available."""
    location = os.environ.get("TRIPOSR_DIR", "")
    if not location:
        return None
    script = Path(location).expanduser() / "run.py"
    return script.resolve() if script.is_file() else None


def decode_image(data_url: str) -> tuple[bytes, str]:
    if not isinstance(data_url, str):
        raise ValueError("Image must be a PNG or JPEG data URL")
    match = IMAGE_RE.fullmatch(data_url)
    if not match:
        raise ValueError("Only base64 PNG/JPEG image uploads are supported")
    try:
        data = base64.b64decode(match.group(2), validate=True)
    except binascii.Error as exc:
        raise ValueError("Invalid base64 image") from exc
    if not data or len(data) > MAX_IMAGE_BYTES:
        raise ValueError("Image must be between 1 byte and 8 MB")
    kind = match.group(1)
    if kind == "png" and not data.startswith(b"\x89PNG\r\n\x1a\n"):
        raise ValueError("PNG content does not match its type")
    if kind == "jpeg" and not data.startswith(b"\xff\xd8\xff"):
        raise ValueError("JPEG content does not match its type")
    return data, ".png" if kind == "png" else ".jpg"


def read_obj(source: str):
    """Parse OBJ vertex and polygon records without requiring trimesh."""
    vertices: list[tuple[float, float, float]] = []
    faces: list[tuple[int, int, int]] = []
    for line in source.splitlines():
        if line.startswith("v "):
            parts = line.split()
            if len(parts) < 4:
                raise ValueError("Invalid OBJ vertex")
            xyz = tuple(float(s) for s in parts[1:4])
            if not all(math.isfinite(v) for v in xyz):
                raise ValueError("Nonfinite OBJ coordinate")
            vertices.append(xyz)
        elif line.startswith("f "):
            pieces = line.split()[1:]
            if len(pieces) < 3:
                raise ValueError("Invalid OBJ face")
            ids = []
            for item in pieces:
                token = item.split("/")[0]
                raw = int(token)
                idx = raw - 1 if raw > 0 else len(vertices) + raw
                if idx < 0 or idx >= len(vertices):
                    raise ValueError("OBJ face references unknown vertex")
                ids.append(idx)
            for j in range(1, len(ids) - 1):
                faces.append((ids[0], ids[j], ids[j + 1]))
                if len(faces) > MAX_TRIANGLES:
                    raise ValueError("Mesh exceeds supported triangle limit")
    if not vertices or not faces:
        raise ValueError("OBJ has no useful mesh geometry")
    return vertices, faces


def obj_to_binary_stl(obj_text: str, longest_mm: float) -> tuple[bytes, int]:
    """Rebase to a Z=0 floor, XY-center, normalize longest size in millimeters."""
    longest_mm = float(longest_mm)
    if not math.isfinite(longest_mm) or not 10 <= longest_mm <= 500:
        raise ValueError("Target dimension must be 10 to 500 mm")
    vertices, faces = read_obj(obj_text)
    low = [min(v[k] for v in vertices) for k in range(3)]
    high = [max(v[k] for v in vertices) for k in range(3)]
    largest = max(high[k] - low[k] for k in range(3))
    if largest <= 1e-12:
        raise ValueError("Mesh has zero extent")
    factor = longest_mm / largest
    mids = [(high[0] + low[0]) / 2, (high[1] + low[1]) / 2, low[2]]
    output = io.BytesIO()
    output.write(b"BEAN 3D | TripoSR reconstruction | millimeters".ljust(80, b"\0"))
    output.write(struct.pack("<I", len(faces)))
    for face in faces:
        coords = []
        for i in face:
            xyz = vertices[i]
            coords.append(tuple((xyz[k] - mids[k]) * factor for k in range(3)))
        a, b, c = coords
        u = [b[k] - a[k] for k in range(3)]
        v = [c[k] - a[k] for k in range(3)]
        n = (
            u[1] * v[2] - u[2] * v[1],
            u[2] * v[0] - u[0] * v[2],
            u[0] * v[1] - u[1] * v[0],
        )
        magnitude = math.sqrt(sum(x * x for x in n)) or 1.0
        normal = tuple(x / magnitude for x in n)
        output.write(struct.pack("<12fH", *(normal + a + b + c), 0))
    return output.getvalue(), len(faces)


def reconstruct(image: bytes, extension: str, target_mm: float) -> tuple[bytes, int]:
    script = model_script()
    if not script:
        raise RuntimeError("TripoSR not installed: set TRIPOSR_DIR to its cloned repository")
    python = os.environ.get("TRIPOSR_PYTHON", sys.executable)
    with tempfile.TemporaryDirectory(prefix="bean-3d-") as work:
        folder = Path(work)
        source = folder / ("input" + extension)
        output = folder / "output"
        source.write_bytes(image)
        command = [
            python, str(script), str(source),
            "--output-dir", str(output),
            "--model-save-format", "obj",
        ]
        try:
            process = subprocess.run(
                command, cwd=str(script.parent), capture_output=True,
                text=True, timeout=900, check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError("TripoSR inference timed out after 15 minutes") from exc
        if process.returncode:
            details = (process.stderr or process.stdout or "").strip()[-1400:]
            raise RuntimeError("TripoSR exited with error: " + details)
        obj_path = output / "0" / "mesh.obj"
        if not obj_path.is_file():
            raise RuntimeError("TripoSR produced no output/0/mesh.obj")
        if obj_path.stat().st_size > 120 * 1024 * 1024:
            raise RuntimeError("Reconstruction mesh is too large")
        return obj_to_binary_stl(obj_path.read_text(encoding="utf-8"), target_mm)


class Handler(BaseHTTPRequestHandler):
    """Serve the interface and local-only GPU bridge from the same origin."""

    server_version = "BEAN3D/0.1"

    def send_bytes(self, data: bytes, status: int = 200, content_type: str = "application/json"):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(data)

    def send_json(self, data: dict, status: int = 200):
        self.send_bytes(json.dumps(data).encode("utf-8"), status)

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/health":
            self.send_json({
                "service": "bean-3d-studio",
                "model": "TripoSR",
                "model_available": model_script() is not None,
                "scope": "localhost",
            })
            return
        if path == "/":
            self.send_response(302)
            self.send_header("Location", "/bean-3d/")
            self.end_headers()
            return
        public = {
            "/bean-3d/": DOCS / "bean-3d/index.html",
            "/bean-3d/index.html": DOCS / "bean-3d/index.html",
            "/bean-3d/mesh.mjs": DOCS / "bean-3d/mesh.mjs",
            "/bean-official.webp": DOCS / "bean-official.webp",
            "/ecosystem-nav.css": DOCS / "ecosystem-nav.css",
        }
        filepath = public.get(path)
        if filepath and filepath.is_file():
            typ = "text/html" if filepath.suffix == ".html" else "text/javascript" if filepath.suffix == ".mjs" else "text/css" if filepath.suffix == ".css" else "image/webp"
            self.send_bytes(filepath.read_bytes(), content_type=typ)
        else:
            self.send_json({"error": "Not found"}, 404)

    def do_POST(self):
        if urlparse(self.path).path != "/api/image-to-3d":
            self.send_json({"error": "Not found"}, 404)
            return
        try:
            raw_size = int(self.headers.get("Content-Length", "0"))
            if not 0 < raw_size <= MAX_REQUEST_BYTES:
                raise ValueError("Request must be smaller than 12 MB")
            if self.headers.get("Content-Type", "").split(";")[0].strip() != "application/json":
                raise ValueError("Use application/json")
            data = json.loads(self.rfile.read(raw_size))
            image, extension = decode_image(data["image"])
            size = float(data.get("size_mm", 100))
            if not 10 <= size <= 500 or not math.isfinite(size):
                raise ValueError("Target longest dimension must be between 10 and 500 mm")
        except (ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
            self.send_json({"error": str(exc)}, 400)
            return
        try:
            stl, faces = reconstruct(image, extension, size)
            self.send_json({
                "triangles": faces,
                "longest_dimension_mm": size,
                "source": "TripoSR local reconstruction",
                "stl_base64": base64.b64encode(stl).decode("ascii"),
            })
        except (RuntimeError, OSError, ValueError) as exc:
            self.send_json({"error": str(exc)}, 500)


def main():
    server = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    print("BEAN 3D Studio: http://127.0.0.1:%s/ (localhost only)" % PORT)
    print("TripoSR script:", model_script() or "not configured")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
