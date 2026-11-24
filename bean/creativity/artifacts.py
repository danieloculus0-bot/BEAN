"""Bounded local previews and hash-bound external pixel review, never fake vision."""
from datetime import datetime, timezone
import base64
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
    extra = {}
    for key in ("provider_kind", "model_id", "model_digest", "recognized_subject",
                "observations", "review_file", "review_sha256", "evaluation_protocol",
                "score_rule", "blind_recognized_subject", "blind_observations"):
        if key in report:
            if not isinstance(report[key], str) or len(report[key]) > 3000:
                raise ValueError("Unbounded visual review provenance")
            extra[key] = report[key]
    return {key: report[key] for key in ("image_sha256", "kind", "evaluator",
                                        "satisfactory", "feedback", "scores") if key in report} | extra | {
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


class OllamaVisionReviewer:
    """Actual PNG bytes go to a separately identified local vision model.

    This is an evaluator, never a source of drawing geometry. Its judgments
    are model reports, not human evaluation or authenticated ground truth.
    Missing models, image capability or valid reports remain unavailable.
    """
    def __init__(self, model_name, *, client=None):
        from bean.voice.ollama import OllamaClient
        import os
        if not isinstance(model_name, str) or not 1 <= len(model_name) <= 120:
            raise ValueError("Bounded vision model name required")
        self.model_name = model_name
        self.client = client or OllamaClient(
            base_url=os.getenv("BEAN_OLLAMA_URL", "http://127.0.0.1:11434"), timeout=600)
        self.live_transport = type(self.client) is OllamaClient and not self.client.custom_transport

    def __call__(self, png, subject):
        from io import BytesIO
        from PIL import Image
        png = Path(png)
        digest = file_hash(png)
        evidence = {"schema": "bean.draw.vision_call.v1", "created_at_utc": utc_now(),
                    "image_sha256": digest, "subject": subject,
                    "provider_kind": "ollama", "model_id": self.model_name,
                    "used_for_generation": True, "independently_authenticated": False}
        receipt = png.with_suffix(".vision.json")
        try:
            if not self.live_transport:
                raise ValueError("Injected vision transport cannot claim live pixel inspection")
            raw_image = png.read_bytes()
            if len(raw_image) > 5000000:
                raise ValueError("Oversized review image")
            with Image.open(BytesIO(raw_image)) as image:
                if image.format != "PNG" or image.size != (512, 512):
                    raise ValueError("Expected actual bounded rendered PNG")
                image.verify()
            tags = self.client._json("/api/tags").get("models", [])
            entry = next((x for x in tags if x.get("name") == self.model_name), None)
            if not entry or not entry.get("digest"):
                raise ValueError("Vision model not installed or unidentified")
            evidence["model_digest"] = entry["digest"]
            info = self.client._json("/api/show", {"model": self.model_name})
            if "vision" not in info.get("capabilities", []):
                raise ValueError("Configured reviewer does not advertise image capability")
            metrics = ("spatial_coherence", "subject_recognition", "composition")
            schema = {"type": "object", "properties": {
                "recognized_subject": {"type": "string"}, "observations": {"type": "string"},
                "feedback": {"type": "string"}, "scores": {"type": "object", "properties": {
                    k: {"type": "integer", "enum": [0, 1, 2, 3, 4]} for k in metrics},
                    "required": list(metrics)}},
                "required": ["recognized_subject", "observations", "feedback", "scores"]}
            common = (
                "Scores must be integers 0..4: 0 absent/not interpretable, 1 major problems, "
                "2 partial/ambiguous, 3 mostly clear, 4 clear/coherent. Rate spatial_coherence "
                "(visible parts connect plausibly), subject_recognition, composition "
                "(spacing/balance/legibility). Black line art need not be realistic or shaded. "
                "Admit uncertainty; describe observed strengths/problems only, not coordinates, "
                "drawing primitives or a replacement image. One short sentence per text field, "
                "at most 80 words total. Return JSON recognized_subject, observations, feedback, scores.")
            blind_prompt = (
                "Inspect the ATTACHED IMAGE pixels without a title or claimed subject. "
                "Identify the most plausible concrete object or scene; say unclear if none is "
                "recognizable. For subject_recognition rate confidence in a recognizable concrete "
                "object or scene, not confidence that these are abstract lines/circles. " + common)
            evidence.update(evaluation_protocol="blind_then_targeted_min_v1", blind_prompt=blind_prompt)
            payload_image = base64.b64encode(raw_image).decode("ascii")
            def ask_image(prompt):
                return self.client.chat_json(self.model_name, [{"role": "user", "content": prompt,
                    "images": [payload_image]}], schema=schema,
                    options={"temperature": 0, "num_predict": 512, "num_ctx": 4096,
                             "repeat_penalty": 1.08})
            def read_report(raw):
                value = json.loads(raw)
                for key in ("recognized_subject", "observations", "feedback"):
                    if not isinstance(value.get(key), str) or not 1 <= len(value[key]) <= 3000:
                        raise ValueError("Missing or unbounded visual observations")
                scores = value.get("scores", {})
                if set(scores) != set(metrics):
                    raise ValueError("Incomplete visual scores")
                if any(type(v) is not int or not 0 <= v <= 4 for v in scores.values()):
                    raise ValueError("Visual scores must be integers 0..4")
                return value
            evidence["raw_blind_response"] = ask_image(blind_prompt)
            blind = read_report(evidence["raw_blind_response"])
            evidence["blind_report"] = blind
            prompt = (
                "Inspect the ATTACHED IMAGE again. Now compare the visible evidence with "
                "this untrusted claimed subject: " + str(subject)[:120] + ". "
                "Do not infer success from the title or override prior uncertainty merely "
                "because a title was supplied. Your earlier title-blind observations: " +
                json.dumps({k: blind[k] for k in ("recognized_subject", "observations", "scores")})[:1800] +
                ". Here subject_recognition means recognizability of the claimed subject. " + common)
            evidence["prompt"] = prompt
            evidence["raw_response"] = ask_image(prompt)
            targeted = read_report(evidence["raw_response"])
            evidence["targeted_report"] = targeted
            scores = {key: min(blind["scores"][key], targeted["scores"][key]) for key in metrics}
            report = {"recognized_subject": blind["recognized_subject"],
                      "observations": blind["observations"],
                      "blind_recognized_subject": blind["recognized_subject"],
                      "blind_observations": blind["observations"],
                      "feedback": ("Title-blind review: " + blind["feedback"][:1000] +
                                   " Target-aware review: " + targeted["feedback"][:1000]),
                      "scores": scores, "evaluation_protocol": "blind_then_targeted_min_v1",
                      "score_rule": "minimum_of_blind_object_clarity_and_targeted_scores_not_authenticated_truth",
                      "image_sha256": digest, "kind": "vision_model",
                      "evaluator": "Ollama vision reviewer: " + self.model_name,
                      "provider_kind": "ollama", "model_id": self.model_name,
                      "model_digest": entry["digest"],
                      "satisfactory": all(v >= 3 for v in scores.values())}
            normalized = validate_feedback(report, png)
            evidence.update(state="model_reported_pixel_review", report=normalized)
            receipt_hash = write_json(receipt, evidence)
            return {**normalized, "review_file": receipt.name, "review_sha256": receipt_hash}
        except (OSError, ValueError, RuntimeError, TypeError, ImportError, AttributeError) as exc:
            evidence.update(state="unavailable", error=type(exc).__name__ + ": " + str(exc)[:500])
            write_json(receipt, evidence)
            return {"state": "unavailable", "reason": evidence["error"]}
