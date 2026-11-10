"""Local-only BEAN HTML browser: source inspection and bounded real JS rendering.

Runs a fresh isolated Chromium context for each call. There is no persistent
browser profile, browser credential sharing, general shell, or filesystem write.
No live site, private file, or result is published to GitHub by this module.
"""
from __future__ import annotations

from hashlib import sha256
import os
from pathlib import Path
from urllib.parse import unquote, urlsplit

MAX_HTML_BYTES = 1_000_000
MAX_RESULT_CHARS = 12000
MAX_SCRIPT_CHARS = 3000
MAX_ACTIONS = 8


def _root() -> Path:
    configured = os.environ.get("BEAN_HTML_ROOT", "").strip()
    if not configured:
        raise ValueError("Configure BEAN_HTML_ROOT to an authorized local folder")
    root = Path(configured).expanduser().resolve(strict=True)
    if not root.is_dir():
        raise ValueError("BEAN_HTML_ROOT must be a folder")
    return root


def _inside(file: Path, root: Path) -> Path:
    resolved = file.expanduser().resolve(strict=True)
    if not resolved.is_file() or not resolved.is_relative_to(root):
        raise ValueError("HTML file must be inside BEAN_HTML_ROOT")
    return resolved


def _allowed_origins() -> set[str]:
    values = set()
    raw = os.environ.get("BEAN_HTML_ALLOWED_ORIGINS", "")
    for item in (x.strip() for x in raw.split(",") if x.strip()):
        parsed = urlsplit(item)
        if (parsed.scheme not in {"http", "https"} or not parsed.hostname
                or parsed.username or parsed.password or parsed.path not in ("", "/")
                or parsed.query or parsed.fragment):
            raise ValueError("Allowed origins must be exact http(s) origins")
        values.add(parsed.scheme + "://" + parsed.netloc.lower())
    return values


def _origin(url: str) -> str | None:
    try:
        parsed = urlsplit(url)
        if parsed.scheme in {"http", "https"} and parsed.hostname:
            return parsed.scheme + "://" + parsed.netloc.lower()
    except ValueError:
        return None
    return None


def _target(value: str, root: Path, origins: set[str]) -> tuple[str, Path | None]:
    if not isinstance(value, str) or not value or len(value) > 2048:
        raise ValueError("A bounded HTML file path or explicitly permitted URL is required")
    parsed = urlsplit(value)
    if parsed.scheme in {"http", "https"}:
        if _origin(value) not in origins:
            raise ValueError("Target origin is not permitted by BEAN_HTML_ALLOWED_ORIGINS")
        if parsed.username or parsed.password:
            raise ValueError("Embedded URL credentials are not supported")
        return value, None
    if parsed.scheme:
        raise ValueError("Only local file paths or explicitly permitted http(s) URLs are supported")
    f = _inside(Path(value), root)
    if f.suffix.lower() not in {".html", ".htm"}:
        raise ValueError("Target must be an HTML document")
    if f.stat().st_size > MAX_HTML_BYTES:
        raise ValueError("HTML source exceeds the size limit")
    return f.as_uri(), f


def _valid_actions(actions: list[dict[str, str]] | None) -> list[dict[str, str]]:
    if actions is None:
        return []
    if not isinstance(actions, list) or len(actions) > MAX_ACTIONS:
        raise ValueError("Only up to eight bounded browser actions are supported")
    cleaned = []
    for action in actions:
        if not isinstance(action, dict) or set(action) not in ({"type", "selector"}, {"type", "selector", "value"}):
            raise ValueError("Action requires type, selector and optional value")
        kind, selector = action.get("type"), action.get("selector")
        if kind not in {"click", "fill"} or not isinstance(selector, str) or not 1 <= len(selector) <= 200:
            raise ValueError("Use a bounded click/fill action and CSS selector")
        if kind == "click" and "value" in action:
            raise ValueError("Click does not take a value")
        if kind == "fill" and (not isinstance(action.get("value"), str) or len(action["value"]) > 1024):
            raise ValueError("Fill requires a bounded string value")
        cleaned.append(dict(action))
    return cleaned


def inspect_html(target: str, *, execute_scripts: bool = False,
                 actions: list[dict[str, str]] | None = None,
                 wait_ms: int = 100) -> dict:
    """Read raw source, embedded scripts, and rendered DOM with bounded output.

    The browser executes page scripts only when execute_scripts=True. All
    requests outside BEAN_HTML_ROOT or explicitly allowlisted origins are
    aborted, including frames, fetch, images, and subresources. No network
    origin is allowed by default.
    """
    if type(execute_scripts) is not bool:
        raise ValueError("execute_scripts must be boolean")
    if type(wait_ms) is not int or not 0 <= wait_ms <= 1500:
        raise ValueError("wait_ms must be between 0 and 1500")
    steps = _valid_actions(actions)
    if steps and not execute_scripts:
        raise ValueError("Browser interaction requires execute_scripts=True")
    root, origins = _root(), _allowed_origins()
    address, file = _target(target, root, origins)
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise RuntimeError("Playwright is missing: pip install playwright") from exc

    blocked = []
    console = []
    script_errors = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        try:
            context = browser.new_context(
                java_script_enabled=execute_scripts,
                accept_downloads=False,
                service_workers="block",
                permissions=[],
            )
            try:
                def route_request(route):
                    url = route.request.url
                    scheme = urlsplit(url).scheme
                    allow = False
                    if scheme == "file":
                        try:
                            path = Path(unquote(urlsplit(url).path)).resolve(strict=True)
                            allow = path.is_file() and path.is_relative_to(root)
                        except (OSError, ValueError):
                            pass
                    elif scheme in {"http", "https"}:
                        allow = _origin(url) in origins and urlsplit(url).username is None
                    elif scheme in {"data", "blob", "about"}:
                        allow = True
                    if allow:
                        route.continue_()
                    else:
                        blocked.append(scheme or "unknown")
                        route.abort()

                context.route("**/*", route_request)
                page = context.new_page()
                page.on("console", lambda msg: console.append(
                    {"type": msg.type, "message": msg.text[:500]}
                ) if len(console) < 20 else None)
                page.on("pageerror", lambda err: script_errors.append(
                    str(err)[:500]
                ) if len(script_errors) < 20 else None)
                response = page.goto(address, wait_until="domcontentloaded", timeout=12000)
                if file is not None:
                    source_bytes = file.read_bytes()
                    if len(source_bytes) > MAX_HTML_BYTES:
                        raise ValueError("Source changed during inspection")
                    source = source_bytes.decode("utf-8", errors="replace")
                else:
                    if response is None:
                        raise RuntimeError("Browser returned no HTML response")
                    if response.status >= 400:
                        raise RuntimeError("HTML page returned HTTP " + str(response.status))
                    source = response.text()
                    if len(source.encode("utf-8")) > MAX_HTML_BYTES:
                        raise ValueError("Remote HTML exceeds source limit")
                for step in steps:
                    control = page.locator(step["selector"]).first
                    if step["type"] == "click":
                        control.click(timeout=2500)
                    else:
                        control.fill(step["value"], timeout=2500)
                if execute_scripts and wait_ms:
                    page.wait_for_timeout(wait_ms)
                scripts = page.locator("script").evaluate_all(
                    """nodes => nodes.slice(0, 30).map(node => ({
                        kind: node.src ? 'external' : 'inline',
                        src: node.getAttribute('src') || '',
                        type: node.getAttribute('type') || '',
                        code: node.src ? '' : (node.textContent || '').slice(0, 3000)
                    }))"""
                )
                # Script enumeration must work even when page JS is disabled.
                # Playwright's evaluation is a controller-side read, not
                # site-authored JS execution; verified in the browser test.
                dom = page.content()
                rendered = page.locator("body").inner_text(timeout=3000) if page.locator("body").count() else ""
                return {
                    "schema": "bean.local.html_browser.v1",
                    "scope": "local_isolated_browser",
                    "scripts_executed": execute_scripts,
                    "target_kind": "local_file" if file else "explicit_origin",
                    "source_sha256": sha256(source.encode("utf-8")).hexdigest(),
                    "source_excerpt": source[:MAX_RESULT_CHARS],
                    "source_truncated": len(source) > MAX_RESULT_CHARS,
                    "title": page.title()[:300],
                    "rendered_text": rendered[:MAX_RESULT_CHARS],
                    "dom_excerpt": dom[:MAX_RESULT_CHARS],
                    "dom_sha256": sha256(dom.encode("utf-8")).hexdigest(),
                    "scripts": scripts,
                    "script_count_visible": page.locator("script").count(),
                    "actions_performed": len(steps),
                    "console": console,
                    "page_errors": script_errors,
                    "blocked_request_count": len(blocked),
                    "blocked_request_schemes": sorted(set(blocked)),
                    "notes": [
                        "No browser profile, saved credentials or persistent session was loaded.",
                        "Local file reads stay inside configured root; remote origins are opt-in.",
                        "The browser's JS engine executes page scripts only in run mode.",
                        "No file, journal or public repository was written.",
                    ],
                }
            finally:
                context.close()
        finally:
            browser.close()
