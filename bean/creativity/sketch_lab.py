"""BEAN Core sketch experiment: model chooses, researches, draws and reflects.

Uses BEAN's existing model, web research, and SHA-chained SQLite journal.
Optional MIT-licensed drawsvg is a renderer, not a separate intelligence.
No generated Python/HTML is executed; visual success needs a host evaluator.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import math
import os
from pathlib import Path
import xml.etree.ElementTree as ET
import subprocess
import uuid

from .artifacts import file_hash, write_json, utc_now, rasterize, validate_feedback, FileVisionReviewer

from bean.learning import NativeReasoningService
from bean.learning.experimental import SCHEMA
from bean.learning.reasoning_service import _model_response
from bean.research import WebResearchService
from bean.voice.ollama import OllamaClient


def decode(raw):
    if not isinstance(raw, str) or len(raw) > 24000:
        raise ValueError("Model answer missing or oversized")
    s = raw.strip()
    if s.startswith(chr(96) * 3):
        s = "\n".join(s.splitlines()[1:-1])
    result = json.loads(s)
    if not isinstance(result, dict):
        raise ValueError("Expected a JSON object")
    return result


def text(value, limit=200):
    if not isinstance(value, str) or not 1 <= len(value.strip()) <= limit:
        raise ValueError("Required bounded text")
    return value.strip()


def coord(x, positive=False):
    if (isinstance(x, bool) or not isinstance(x, (int, float))
            or not math.isfinite(x) or not 0 <= x <= 256
            or positive and not x > 0):
        raise ValueError("Invalid drawing coordinate")
    return x


def _shape_coord(value, label, positive=False):
    try:
        return coord(value, positive)
    except ValueError as exc:
        raise ValueError("Invalid drawing coordinate " + label + "=" + repr(value)[:60] +
                         "; require finite 0..256, positive sizes") from exc


def validate_shapes(shapes):
    if not isinstance(shapes, list) or not 1 <= len(shapes) <= 80:
        raise ValueError("Expected 1..80 drawing primitives")
    validated = []
    kinds = {"line": ("x1", "y1", "x2", "y2"),
             "circle": ("cx", "cy", "r"),
             "rect": ("x", "y", "w", "h")}
    for index, obj in enumerate(shapes):
        if not isinstance(obj, dict) or obj.get("type") not in (*kinds, "polyline"):
            raise ValueError("Unsupported primitive")
        kind = obj["type"]
        if kind == "polyline":
            pts = obj.get("points")
            if (not isinstance(pts, list) or not 2 <= len(pts) <= 40
                    or any(not isinstance(p, list) or len(p) != 2 for p in pts)):
                raise ValueError("Invalid polyline")
            validated.append({"type": kind,
                              "points": [[_shape_coord(x, str(index) + ".point.x"),
                                          _shape_coord(y, str(index) + ".point.y")] for x, y in pts]})
        else:
            validated.append({"type": kind, **{
                k: _shape_coord(obj.get(k), str(index) + "." + k, k in ("r", "w", "h")) for k in kinds[kind]}})
    return validated


def draw_svg(shapes, file_path, backend="auto"):
    shapes = validate_shapes(shapes)
    path = Path(file_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if backend not in ("auto", "drawsvg", "stdlib"):
        raise ValueError("Invalid drawing backend")
    draw = None
    if backend != "stdlib":
        try:
            import drawsvg as draw
        except ImportError:
            if backend == "drawsvg":
                raise
    if draw is not None:
        canvas = draw.Drawing(256, 256)
        for s in shapes:
            k = s["type"]
            style = {"stroke": "black", "stroke_width": 2, "fill": "none"}
            if k == "line":
                obj = draw.Line(s["x1"], s["y1"], s["x2"], s["y2"], **style)
            elif k == "circle":
                obj = draw.Circle(s["cx"], s["cy"], s["r"], **style)
            elif k == "rect":
                obj = draw.Rectangle(s["x"], s["y"], s["w"], s["h"], **style)
            else:
                obj = draw.Lines(*[v for p in s["points"] for v in p],
                                 close=False, **style)
            canvas.append(obj)
        canvas.save_svg(str(path))
    else:
        ns = "http://www.w3.org/2000/svg"
        ET.register_namespace("", ns)
        root = ET.Element("{" + ns + "}svg", {
            "width": "256", "height": "256", "viewBox": "0 0 256 256"})
        for s in shapes:
            attrs = {"stroke": "black", "stroke-width": "2", "fill": "none"}
            attrs.update({k: str(v) for k, v in s.items()
                          if k not in ("type", "points")})
            if s["type"] == "rect":
                attrs["width"], attrs["height"] = attrs.pop("w"), attrs.pop("h")
            if s["type"] == "polyline":
                attrs["points"] = " ".join(
                    str(x) + "," + str(y) for x, y in s["points"])
            ET.SubElement(root, "{" + ns + "}" + s["type"], attrs)
        ET.ElementTree(root).write(path, encoding="utf-8", xml_declaration=True)
    return hashlib.sha256(path.read_bytes()).hexdigest()


class OllamaSketchProvider:
    """Reuse BEAN's localhost-only Ollama transport for creative JSON sketches.

    The ordinary OllamaProvider fixes its schema to analytical summaries, so
    its responses cannot encode sketch subjects or shape lists. This adapter
    changes only the JSON format and bounded generation budget, not memory.
    """

    adapter_name = "ollama"

    def __init__(self, model_name=None, client=None):
        self.model_name = model_name or os.environ.get("BEAN_OLLAMA_MODEL", "qwen2.5:1.5b")
        self.seed = None
        self.response_schema = None
        self.client = client or OllamaClient(
            base_url=os.environ.get("BEAN_OLLAMA_URL", "http://127.0.0.1:11434"),
            timeout=600)

    def complete(self, prompt, context=None):
        try:
            options = {"temperature": 0.65, "num_predict": 4096,
                       "num_ctx": 8192, "repeat_penalty": 1.08}
            if self.seed is not None:
                options["seed"] = self.seed
            extra = {"schema": self.response_schema} if self.response_schema else {}
            reply = self.client.chat_json(
                self.model_name, [{"role": "user", "content": prompt}],
                options=options, **extra)
            return {"ok": True, "raw_text": reply,
                    "adapter_name": "ollama", "model_name": self.model_name}
        except (OSError, RuntimeError, ValueError) as exc:
            return {"ok": False, "error": str(exc)[:240],
                    "adapter_name": "ollama", "model_name": self.model_name}


def source_revision():
    try:
        return subprocess.check_output(
            ['git', 'rev-parse', 'HEAD'], cwd=Path(__file__).resolve().parents[2],
            text=True, stderr=subprocess.DEVNULL).strip()
    except (OSError, subprocess.CalledProcessError):
        return 'local-unverified'


def configured_provider():
    name = os.getenv('BEAN_REASONING_PROVIDER', 'local_llamacpp').lower()
    providers = {'local_llamacpp': ('local_llamacpp_provider', 'LocalLlamaCppProvider'),
                 'openrouter': ('openrouter_provider', 'OpenRouterProvider'),
                 'openai': ('openai_provider', 'OpenAIProvider')}
    if name == 'ollama':
        return OllamaSketchProvider()
    if name not in providers:
        raise ValueError('Set a supported BEAN_REASONING_PROVIDER first')
    module, cls = providers[name]
    return getattr(importlib.import_module('bean.reasoning.' + module), cls)()


def execution_mode(model):
    # A caller setting provider_kind='real_model' does not prove a live call.
    if getattr(model, 'provider_kind', None) == 'synthetic_fixture':
        return 'synthetic_fixture'
    if type(model) is OllamaSketchProvider and (
            type(model.client) is not OllamaClient or model.client.custom_transport):
        return 'unverified'
    types = [OllamaSketchProvider]
    for module, cls in [('local_llamacpp_provider', 'LocalLlamaCppProvider'),
                        ('openrouter_provider', 'OpenRouterProvider'),
                        ('openai_provider', 'OpenAIProvider')]:
        types.append(getattr(importlib.import_module('bean.reasoning.' + module), cls))
    return 'live_model' if type(model) in types else 'unverified'


PLAN_SCHEMA = {'type': 'object', 'properties': {
    'subject': {'type': 'string'}, 'reference_query': {'type': 'string'}},
    'required': ['subject', 'reference_query']}
REVIEW_SCHEMA = {'type': 'object', 'properties': {
    'claimed_subject': {'type': 'string'}, 'changes': {'type': 'string'},
    'satisfied': {'type': 'boolean'}}, 'required': ['claimed_subject', 'changes', 'satisfied']}


def drawing_schema():
    variants = []
    for kind, keys in {'line': ['x1', 'y1', 'x2', 'y2'],
                       'circle': ['cx', 'cy', 'r'], 'rect': ['x', 'y', 'w', 'h'],
                       'polyline': ['points']}.items():
        props = {'type': {'const': kind}}
        for key in keys:
            props[key] = ({'type': 'array', 'minItems': 2, 'maxItems': 40,
                           'items': {'type': 'array', 'minItems': 2, 'maxItems': 2,
                                     'items': {'type': 'integer', 'enum': list(range(257))}}}
                          if key == 'points' else
                          {'type': 'integer', 'enum': list(range(1 if key in ('r', 'w', 'h') else 0, 257))})
        variants.append({'type': 'object', 'properties': props,
                         'required': ['type'] + keys, 'additionalProperties': False})
    return {'type': 'object', 'properties': {
        'description': {'type': 'string'},
        'shapes': {'type': 'array', 'minItems': 1, 'maxItems': 24,
                   'items': {'anyOf': variants}}}, 'required': ['description', 'shapes']}


class SketchLab:
    def __init__(self, core, research=None, visual_judge=None):
        if not isinstance(core, NativeReasoningService):
            raise TypeError('Expected existing BEAN Core reasoning service')
        if visual_judge is not None and not callable(visual_judge):
            raise TypeError('visual_judge must be callable')
        self.core, self.research, self.visual_judge = core, research, visual_judge
        self.calls = []

    def ask(self, prompt, schema=None):
        model = self.core._model()
        if type(model) is OllamaSketchProvider:
            model.response_schema = schema
        event = {'prompt': prompt, 'created_at_utc': utc_now()}
        self.calls.append(event)
        class Capture:
            def __getattr__(self, key):
                return getattr(model, key)
            def complete(self, query, context):
                reply = model.complete(query, context)
                event['response'] = reply
                return reply
        try:
            result = _model_response(Capture(), prompt, '')
            event['model_id'], event['provider_kind'], event['provider_response_id'] = result[1:]
            return result
        except Exception as exc:
            event['error'] = type(exc).__name__ + ': ' + str(exc)[:500]
            raise
        finally:
            if getattr(self, '_output', None) is not None:
                write_json(self._output / 'model_calls.json', self.calls)

    def run(self, *, task_ref, output_dir, allow_online=False,
            provider='auto', max_attempts=3, backend='auto',
            complete_all_attempts=False, subject=None, require_live=False,
            memory_mode='adaptive', frozen_memory=None, seed=None):
        task_ref = text(task_ref, 120)
        if (type(allow_online) is not bool or type(complete_all_attempts) is not bool
                or type(max_attempts) is not int or not 1 <= max_attempts <= 5):
            raise ValueError('Explicit online choice and 1..5 attempts required')
        if memory_mode not in ('adaptive', 'frozen', 'none'):
            raise ValueError('Invalid memory condition')
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)
        # Never overwrite an earlier draft, even after a failed process.
        if list(out.glob('attempt_*')) or (out / 'run.json').exists():
            raise ValueError('Output already contains a run; choose a new directory')
        self.calls = []
        self._output = out
        run_id, started = str(uuid.uuid4()), utc_now()
        revision = source_revision()
        mode = 'unverified'
        history = []
        subject_source = 'human' if subject is not None else 'autonomous'
        model_id, model_kind = 'unavailable', 'unavailable'
        research_state, source_urls = 'not_requested', []
        context, correction = '', ''
        runtime_files = ['bean/creativity/sketch_lab.py', 'bean/creativity/artifacts.py',
                         'bean/voice/ollama.py', 'scripts/build_bean_draw_gallery.py']
        repo = Path(__file__).resolve().parents[2]
        runtime_hashes = {name: file_hash(repo / name) for name in runtime_files}
        manifest = {'runtime_source_sha256': runtime_hashes, 'schema': 'bean.draw.run.v1', 'run_id': run_id,
                    'task_ref': task_ref, 'created_at_utc': started,
                    'source_git_sha': revision, 'subject_source': subject_source,
                    'memory_mode': memory_mode, 'seed': seed,
                    'weights_updated': False, 'learning_improvement_verified': False,
                    'independent_visual_verification': False}
        def finish(state, error=None):
            raw_digest = write_json(out / 'model_calls.json', self.calls)
            manifest.update(subject=subject, execution_mode=mode,
                            model_id=model_id, provider_kind=model_kind,
                            model_digest=getattr(self.core.model, 'model_digest', None),
                            history=history, attempts=len(history), state=state,
                            completed_at_utc=utc_now(), error=error,
                            model_calls_sha256=raw_digest)
            tip = self.core.bank.record_trial({
                **manifest, 'schema': SCHEMA, 'experiment': 'bean_sketch_run_v1',
                'domain': 'sketch'})
            manifest['journal_tip'] = tip
            write_json(out / 'run.json', manifest)
            return {'subject_chosen_by_BEAN_model': subject if subject_source == 'autonomous' else None,
                    'subject': subject, 'subject_source': subject_source,
                    'history': history, 'research_status': research_state,
                    'references': source_urls, 'final_status': state,
                    'attempts': len(history), 'run_receipt': str(out / 'run.json'),
                    'visual_success_independently_verified': False}
        try:
            model = self.core._model()
            mode = execution_mode(model)
            if require_live and mode != 'live_model':
                raise ValueError('Live run requires an existing BEAN provider; no fixture fallback')
            if seed is not None:
                if type(seed) is not int or not 0 <= seed <= 2147483647:
                    raise ValueError('Invalid seed')
                if type(model) is not OllamaSketchProvider:
                    raise ValueError('Matched seeded runs currently require OllamaSketchProvider')
                model.seed = seed
            if type(model) is OllamaSketchProvider and require_live:
                # Obtain identity from the serving runtime rather than an env claim.
                tags = model.client._json('/api/tags').get('models', [])
                entry = next((m for m in tags if m.get('name') == model.model_name), None)
                if not entry or not entry.get('digest'):
                    raise ValueError('Configured Ollama model not installed or unidentified')
                model.model_digest = entry['digest']
            prior = [e['data'] for e in self.core.bank.journal.events()
                     if e['kind'] == 'trial' and e['data'].get('experiment') == 'bean_sketch_v1']
            if memory_mode == 'none':
                prior = []
            elif memory_mode == 'frozen':
                if not isinstance(frozen_memory, list):
                    raise ValueError('Frozen condition requires a fixed trial snapshot')
                prior = frozen_memory
            precedents = json.dumps([{
                'subject': x.get('subject'), 'status': x.get('status'), 'error': x.get('error'),
                'suggested_change': x.get('self_review', {}).get('changes'),
                'external_feedback': x.get('external_feedback')}
                for x in prior[-6:]], ensure_ascii=False)[:2400]
            manifest['memory_context_sha256'] = hashlib.sha256(precedents.encode()).hexdigest()
            if subject is None:
                plan_raw, model_id, model_kind, _ = self.ask(
                    'Choose ANY subject to draw, without being given a subject. '
                    'Choose a distinct subject from prior sessions; invent your own composition. '
                    'Respond ONLY JSON with subject and reference_query keys. '
                    'The reference_query may be an empty string. '
                    'Past BEAN drawing attempts and feedback (not verified truth): ' + precedents,
                    PLAN_SCHEMA)
                idea = decode(plan_raw)
                subject = text(idea.get('subject'), 120)
                query = idea.get('reference_query', '')
            else:
                subject, query = text(subject, 120), ''
            if not isinstance(query, str) or len(query) > 300:
                raise ValueError('Invalid model-chosen search query')
            if allow_online and query.strip():
                research = self.research or WebResearchService(self.core)
                try:
                    packet = research.investigate(domain='sketch', task_ref=task_ref + '-research',
                        question=query, provider=provider, max_pages=2, answer_with_model=False)
                    source_urls = [r['url'] for r in packet['sources']]
                    research_state = 'sources_collected' if source_urls else 'no_sources'
                    rows = [e['data'] for e in self.core.bank.journal.events()
                            if e['kind'] == 'research' and e['data'].get('task_ref') == task_ref + '-research']
                    if rows:
                        context = json.dumps([{'url': s['url'], 'excerpt': s['text_excerpt'][:450]}
                                              for s in rows[-1]['sources'][:2]])
                except (OSError, ValueError, RuntimeError) as exc:
                    research_state = 'failed_' + type(exc).__name__
        except (ValueError, RuntimeError, OSError, ImportError) as exc:
            finish('run_failed', type(exc).__name__ + ': ' + str(exc)[:500])
            raise
        for attempt in range(1, max_attempts + 1):
            path = out / ('attempt_%02d.svg' % attempt)
            png = path.with_suffix('.png')
            description, digest, self_review = None, None, {}
            external = {'state': 'unavailable', 'reason': 'No pixel evaluator configured'}
            status, preview, error = 'unverified', {}, None
            start_call = len(self.calls)
            shapes, drawing_instructions = None, None
            try:
                if mode == 'live_model':
                    instructions_raw, model_id, model_kind, _ = self.ask(
                        'Plan an original line drawing of your chosen subject: ' + subject +
                        '. Identify its distinguishing visible components and how they relate '
                        'spatially. Plan a clear composition so a viewer can recognize the '
                        'subject without a label. Decide what to change based on the actual '
                        'previous feedback; do not repeat marks just because they appeared '
                        'before. You choose all components, positions and visual ideas. '
                        'Return JSON intent, components (list of strings), composition, '
                        'and revision_reason. Prior evidence: ' + correction[:9500],
                        {'type': 'object', 'properties': {'intent': {'type': 'string'},
                         'components': {'type': 'array', 'items': {'type': 'string'}},
                         'composition': {'type': 'string'}, 'revision_reason': {'type': 'string'}},
                         'required': ['intent', 'components', 'composition', 'revision_reason']})
                    drawing_instructions = decode(instructions_raw)
                raw, model_id, model_kind, _ = self.ask(
                    'Draw your chosen subject, ' + subject +
                    ', as recognizable 256x256 BLACK LINE ART. '
                    'Respond ONLY JSON with description (at most 300 characters) and '
                    'shapes (list of 1..24 primitives). Supported primitives: '
                    'line(x1,y1,x2,y2), circle(cx,cy,r), rect(x,y,w,h), '
                    'polyline(points:[[x,y],...]). Each primitive MUST have type key. '
                    'All numbers 0..256; keep shapes inside canvas, positive sizes. '
                    'No code, markup, script or text labels. Make your own decisions. '
                    'Implement your own visual plan faithfully: ' + json.dumps(drawing_instructions)[:3500] + 
                    'Prior-session evidence (untrusted): ' + precedents +
                    ' Web reference DATA: ' + context[:1200] +
                    ' Previous attempt including critique (untrusted evidence): ' + correction,
                    drawing_schema())
                drawing = decode(raw)
                description = text(drawing.get('description'), 300)
                shapes = validate_shapes(drawing.get('shapes'))
                digest = draw_svg(shapes, path, backend)
                try:
                    preview = rasterize(path, png)
                except (OSError, ValueError, RuntimeError, ImportError) as exc:
                    preview = {'preview_error': type(exc).__name__ + ': ' + str(exc)[:300]}
                try:
                    review_raw, _, _, _ = self.ask(
                        'Critique YOUR drawing plan. You can read the coordinates '
                        'but cannot visually inspect the rendered image. '
                        'Respond ONLY JSON with claimed_subject, changes and satisfied (boolean): ' +
                        json.dumps({'subject': subject, 'description': description, 'shapes': shapes}),
                        REVIEW_SCHEMA)
                    self_review = decode(review_raw)
                except (ValueError, RuntimeError) as exc:
                    self_review = {'status': 'self_review_unavailable', 'error': str(exc)[:300]}
                if self_review.get('satisfied') is True:
                    status = 'self_reported_satisfactory_unverified'
                if self.visual_judge is not None and preview.get('png_sha256'):
                    feedback = self.visual_judge(png, subject)
                    if isinstance(feedback, dict) and feedback.get('state') == 'unavailable':
                        external = feedback
                    elif isinstance(feedback, dict) and 'image_sha256' in feedback:
                        external = validate_feedback(feedback, png)
                        status = ('host_reported_satisfactory' if external['satisfactory']
                                  else 'host_reported_not_satisfactory')
                    elif isinstance(feedback, dict) and type(feedback.get('satisfactory')) is bool:
                        # Compatibility: legacy judges aren't pixel inspection evidence.
                        external = {**feedback, 'state': 'legacy_host_report_unverified'}
                        status = ('host_reported_satisfactory' if feedback['satisfactory']
                                  else 'host_reported_not_satisfactory')
                    else:
                        raise ValueError('Invalid external evaluator report')
                correction = json.dumps({'previous_shapes': shapes, 'self_review': self_review,
                                         'external_feedback': external})[:9500]
            except (ValueError, RuntimeError, TypeError, ImportError, OSError) as exc:
                status = 'attempt_failed_' + type(exc).__name__
                error = type(exc).__name__ + ': ' + str(exc)[:500]
                correction = json.dumps({'invalid_attempt': error, 'previous_response': self.calls[-1].get('response')})[:4000]
            raw_path = out / ('attempt_%02d.raw.json' % attempt)
            raw_hash = write_json(raw_path, self.calls[start_call:])
            artifact_ok = bool(digest and preview.get('png_sha256') and
                               file_hash(path) == digest and file_hash(png) == preview['png_sha256'])
            receipt = {
                'schema': SCHEMA, 'experiment': 'bean_sketch_v1', 'domain': 'sketch',
                'task_ref': task_ref, 'run_id': run_id, 'attempt': attempt,
                'created_at_utc': utc_now(), 'source_git_sha': revision,
                'model_id': model_id, 'provider_kind': model_kind,
                'model_digest': getattr(model, 'model_digest', None),
                'execution_mode': mode, 'subject': subject, 'subject_source': subject_source,
                'memory_mode': memory_mode, 'seed': seed, 'description': description,
                'drawing_instructions': drawing_instructions,
                'status': status, 'error': error, 'svg_sha256': digest,
                'svg_file': path.name if digest else None,
                'png_file': png.name if preview.get('png_sha256') else None, **preview,
                'raw_file': raw_path.name, 'raw_sha256': raw_hash,
                'reference_urls': source_urls, 'research_status': research_state,
                'self_review': self_review, 'external_feedback': external,
                'visual_feedback': external.get('feedback'),
                'verification_state': 'artifacts_verified' if artifact_ok else 'incomplete',
                'weights_updated': False, 'independent_visual_verification': False,
                'visual_evidence_independently_verified': False}
            tip = self.core.bank.record_trial(receipt)
            sidecar = path.with_suffix('.json')
            sidecar_hash = write_json(sidecar, {**receipt, 'schema': 'bean.draw.attempt.v1',
                                               'journal_tip': tip})
            history.append({'attempt': attempt, 'status': status,
                            'svg': str(path) if digest else None, 'sha256': digest,
                            'png': str(png) if preview.get('png_sha256') else None,
                            'png_sha256': preview.get('png_sha256'),
                            'journal_tip': tip, 'metadata': str(sidecar),
                            'metadata_sha256': sidecar_hash, 'description': description})
            write_json(out / 'progress.json', {'subject': subject, 'history': history})
            if not complete_all_attempts and status in (
                    'host_reported_satisfactory', 'self_reported_satisfactory_unverified'):
                break
        manifest['selected_attempt'] = None
        manifest['selection_state'] = 'unavailable'
        if mode == 'live_model' and any(h['sha256'] for h in history):
            try:
                evidence = [json.loads(Path(h['metadata']).read_text()) for h in history]
                selection_raw, _, _, _ = self.ask(
                    'Choose the strongest retained drawing attempt from this evidence. '
                    'You cannot inspect pixels yourself. Weigh external pixel feedback '
                    'separately from your textual confidence. Return JSON selected_attempt '
                    '(an existing valid attempt number) and reason: ' + json.dumps(evidence)[:19000],
                    {'type': 'object', 'properties': {'selected_attempt': {'type': 'integer'},
                     'reason': {'type': 'string'}}, 'required': ['selected_attempt', 'reason']})
                selection = decode(selection_raw)
                selected = selection.get('selected_attempt')
                if type(selected) is not int or not any(h['attempt'] == selected and h['sha256'] for h in history):
                    raise ValueError('Model selected a failed or nonexistent draft')
                manifest.update(selected_attempt=selected, selection_reason=text(selection.get('reason'), 1000),
                                selection_state='model_selected_from_recorded_evidence')
            except (ValueError, RuntimeError, OSError) as exc:
                manifest['selection_error'] = type(exc).__name__ + ': ' + str(exc)[:500]
        return finish(history[-1]['status'])


def main():
    p = argparse.ArgumentParser(description='BEAN model-generated sketches with retained evidence')
    p.add_argument('--db', default='bean_reasoning_lessons.sqlite3')
    p.add_argument('--out', default='bean_sketch_output')
    p.add_argument('--task-ref', default='sketch-001')
    p.add_argument('--online', action='store_true')
    p.add_argument('--provider', choices=('auto', 'brave', 'wikipedia'), default='auto')
    p.add_argument('--backend', choices=('auto', 'drawsvg', 'stdlib'), default='auto')
    p.add_argument('--attempts', type=int, default=3)
    p.add_argument('--all-attempts', action='store_true')
    p.add_argument('--subject', help='Optional human subject; geometry always comes from model')
    p.add_argument('--require-live', action='store_true')
    p.add_argument('--memory-mode', choices=('adaptive', 'frozen', 'none'), default='adaptive')
    p.add_argument('--frozen-memory', type=Path)
    p.add_argument('--seed', type=int)
    p.add_argument('--review-dir', type=Path)
    p.add_argument('--review-wait', type=int, default=0)
    args = p.parse_args()
    model = configured_provider()
    core = NativeReasoningService(args.db, model=model)
    judge = FileVisionReviewer(args.review_dir, args.review_wait) if args.review_dir else None
    try:
        result = SketchLab(core, visual_judge=judge).run(
            task_ref=args.task_ref, output_dir=args.out, allow_online=args.online,
            provider=args.provider, backend=args.backend, max_attempts=args.attempts,
            complete_all_attempts=args.all_attempts, subject=args.subject,
            require_live=args.require_live, memory_mode=args.memory_mode, seed=args.seed,
            frozen_memory=json.loads(args.frozen_memory.read_text()) if args.frozen_memory else None)
        print(json.dumps(result, indent=2))
        if not any(row['sha256'] for row in result['history']):
            raise SystemExit(2)
    finally:
        core.close()


if __name__ == '__main__':
    main()
