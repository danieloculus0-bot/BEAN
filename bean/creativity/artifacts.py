"""Bounded local previews and hash-bound external pixel review, never fake vision."""
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import time


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def file_hash(path):
    return sha256(Path(path).read_bytes()).hexdigest()


def write_json(path, value):
    Path(path).write_text(json.dumps(value, indent=2, sort_keys=True,
                                    ensure_ascii=False, allow_nan=False) + "\n",
                          encoding="utf-8")
    return file_hash(path)


def rasterize(svg, png):
    # Only our finite primitive subset is accepted before Cairo parses it.
    from scripts.build_bean_draw_gallery import validate_svg
    import cairosvg
    from PIL import Image
    raw = Path(svg).read_bytes()
    validate_svg(raw)
    cairosvg.svg2png(bytestring=raw, write_to=str(png), unsafe=False,
                    output_width=512, output_height=512,
                    background_color="white")
    with Image.open(png) as image:
        image.load()
        if image.format != "PNG" or image.size != (512, 512):
            raise ValueError("Invalid preview")
    return {"png_sha256": file_hash(png), "rasterizer": "CairoSVG " + cairosvg.__version__,
            "preview_size": [512, 512]}


def validate_feedback(report, png):
    if (not isinstance(report, dict)
            or report.get("image_sha256") != file_hash(png)
            or report.get("kind") not in ("vision_model", "human")
            or not isinstance(report.get("evaluator"), str)
            or not 1 <= len(report["evaluator"]) <= 200
            or type(report.get("satisfactory")) is not bool
            or not isinstance(report.get("feedback"), str)
            or not 1 <= len(report["feedback"]) <= 3000):
        raise ValueError("Pixel review must identify evaluator and actual PNG hash")
    if not isinstance(report.get("scores", {}), dict):
        raise ValueError("Review scores must be an object")
    for key, score in report.get("scores", {}).items():
        if key not in ("spatial_coherence", "subject_recognition", "composition", "diversity"):
            raise ValueError("Unknown review metric")
        if type(score) not in (int, float) or not 0 <= score <= 4:
            raise ValueError("Review scores must be 0..4")
    # A host callback/file is evidence, not authenticated independent truth.
    return {key: report[key] for key in ("image_sha256", "kind", "evaluator",
                                        "satisfactory", "feedback", "scores") if key in report} | {
            "state": "host_reported_pixel_review", "created_at_utc": utc_now(),
            "independently_authenticated": False}


class FileVisionReviewer:
    """A host/vision agent inspects request PNG, then supplies <hash>.json.

    No subject-label matching masquerading as image recognition. Missing review
    is unavailable; a file alone cannot authenticate who inspected the pixels.
    """
    def __init__(self, folder, wait_seconds=0):
        self.folder = Path(folder)
        self.folder.mkdir(parents=True, exist_ok=True)
        self.wait_seconds = max(0, min(600, wait_seconds))

    def __call__(self, png, subject):
        digest = file_hash(png)
        request = self.folder / (digest + ".request.json")
        write_json(request, {"image": str(Path(png).resolve()), "image_sha256": digest,
                             "subject": subject, "created_at_utc": utc_now()})
        response = self.folder / (digest + ".json")
        deadline = time.monotonic() + self.wait_seconds
        while not response.is_file() and time.monotonic() < deadline:
            time.sleep(0.5)
        if not response.is_file():
            return {"state": "unavailable", "reason": "No external pixel evaluator report"}
        if response.stat().st_size > 12000:
            raise ValueError("Oversized visual review")
        return validate_feedback(json.loads(response.read_text()), png)
