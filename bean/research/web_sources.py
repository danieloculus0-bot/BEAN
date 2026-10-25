"""Bounded read-only public web sources for BEAN Core.

BEAN owns the source index and decisions; Brave/Wikipedia supply candidate
links, never trusted facts or executable instructions. Only HTTPS, public DNS,
safe response types, capped bodies and nonredirecting requests are permitted.
No JavaScript, login/cookies, deep crawl, arbitrary user-supplied tools or shell.
"""
from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
from html import unescape
from html.parser import HTMLParser
import ipaddress
import json
import os
import socket
from urllib.parse import quote, urlencode, urlsplit
from urllib.request import Request, build_opener, HTTPRedirectHandler

WIKI_SEARCH = "https://en.wikipedia.org/w/api.php"
BRAVE_SEARCH = "https://api.search.brave.com/res/v1/web/search"
MAX_RESPONSE_BYTES = 196608
MAX_PAGE_CHARS = 10000
USER_AGENT = "BEAN-Research/1.0 (read-only; source-attributed; no crawl)"


class ResearchTransportError(RuntimeError):
    pass


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, newurl):
        raise ResearchTransportError("HTTP redirect refused (no unverified destination)")


def _http(request, *, timeout):
    return build_opener(_NoRedirect()).open(request, timeout=timeout)


def _load(request, *, request_fn, max_bytes=MAX_RESPONSE_BYTES):
    try:
        with request_fn(request, timeout=8) as response:
            status = getattr(response, "status", 200)
            if status != 200:
                raise ResearchTransportError("HTTP status " + str(status))
            headers = getattr(response, "headers", {})
            mime = headers.get("Content-Type", "text/plain").split(";")[0].lower()
            if mime not in ("text/html", "text/plain", "application/json"):
                raise ResearchTransportError("Unsupported content type")
            raw = response.read(max_bytes + 1)
        if len(raw) > max_bytes:
            raise ResearchTransportError("Response exceeds maximum safe bytes")
        return raw, mime
    except ResearchTransportError:
        raise
    except Exception as exc:
        # Never copy raw exception messages: they may include private URLs,
        # query content, credentials, or returned document fragments.
        raise ResearchTransportError("HTTP request failed: " + type(exc).__name__) from exc


def _valid_host(url, resolver=socket.getaddrinfo):
    if not isinstance(url, str) or len(url) > 1800:
        raise ValueError("Bounded HTTPS source URL required")
    parts = urlsplit(url)
    host = parts.hostname
    if (parts.scheme.lower() != "https" or not host
            or parts.username is not None or parts.password is not None
            or parts.port not in (None, 443) or parts.fragment
            or len(host) > 253 or host.endswith(".")
            or "." not in host or host.lower() in ("localhost",)
            or host.lower().endswith((".localhost", ".local", ".internal", ".test"))):
        raise ValueError("Source URL must be public HTTPS without credentials/fragment")
    try:
        ipaddress.ip_address(host)
    except ValueError:
        pass
    else:
        raise ValueError("IP literal not allowed as source host")
    try:
        addresses = resolver(host, 443, type=socket.SOCK_STREAM)
    except (OSError, ValueError) as exc:
        raise ValueError("Public source DNS resolution failed") from exc
    if not addresses:
        raise ValueError("Source DNS returned no addresses")
    for item in addresses:
        try:
            addr = ipaddress.ip_address(item[4][0])
        except (IndexError, ValueError, TypeError) as exc:
            raise ValueError("Invalid resolved address") from exc
        if not addr.is_global:
            raise ValueError("Private/nonroutable DNS address rejected")
    return host.casefold()


class _Text(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.fragments = []
        self.depth = 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style", "noscript", "template", "svg"):
            self.depth += 1
        elif tag in ("p", "br", "h1", "h2", "h3", "li") and not self.depth:
            self.fragments.append("\n")

    def handle_endtag(self, tag):
        if tag in ("script", "style", "noscript", "template", "svg") and self.depth:
            self.depth -= 1

    def handle_data(self, data):
        if not self.depth:
            self.fragments.append(data)


def _plain(text, *, html=False, maximum=MAX_PAGE_CHARS):
    if html:
        parser = _Text()
        parser.feed(text)
        text = "".join(parser.fragments)
    else:
        text = unescape(text)
    # Preserve whitespace-separated words rather than HTML/JS execution.
    return " ".join(text.split())[:maximum]


class PublicWebSources:
    """Search one external index then read at most three public HTML pages."""

    def __init__(self, *, brave_key=None, request_fn=_http, resolver=socket.getaddrinfo):
        self.brave_key = brave_key or os.environ.get("BRAVE_SEARCH_API_KEY")
        self.request_fn = request_fn
        self.resolver = resolver
        self.call_count = 0

    def search(self, question, *, limit=3, engine="auto"):
        if (not isinstance(question, str) or not 1 <= len(question.strip()) <= 500
                or len(question.split()) > 75 or type(limit) is not int
                or not 1 <= limit <= 5):
            raise ValueError("Bounded search query and 1..5 result limit required")
        if engine not in ("auto", "wikipedia", "brave"):
            raise ValueError("Unknown search provider")
        use_brave = engine == "brave" or (engine == "auto" and bool(self.brave_key))
        if use_brave:
            if not self.brave_key:
                raise ValueError("Brave requires BRAVE_SEARCH_API_KEY")
            params = urlencode({"q": question, "count": limit, "safesearch": "moderate"})
            url = BRAVE_SEARCH + "?" + params
            request = Request(url, headers={
                "Accept": "application/json", "X-Subscription-Token": self.brave_key,
                "User-Agent": USER_AGENT})
            provider = "brave_web"
        else:
            # Useful key-free fallback, but covers Wikipedia only, NOT the full
            # open web. Do not describe Wikipedia as comprehensive web search.
            params = urlencode({
                "action": "query", "list": "search", "srsearch": question,
                "srlimit": limit, "format": "json", "utf8": 1})
            request = Request(WIKI_SEARCH + "?" + params,
                              headers={"Accept": "application/json", "User-Agent": USER_AGENT})
            provider = "wikipedia"
        self.call_count += 1
        raw, mime = _load(request, request_fn=self.request_fn)
        if mime != "application/json":
            raise ResearchTransportError("Search did not return JSON")
        try:
            data = json.loads(raw)
        except (ValueError, UnicodeError) as exc:
            raise ResearchTransportError("Search JSON invalid") from exc
        if provider == "brave_web":
            items = (data.get("web") or {}).get("results") or []
            records = [{
                "title": str(x.get("title", ""))[:180],
                "url": str(x.get("url", "")),
                "snippet": _plain(str(x.get("description", "")), html=True, maximum=600),
                "source_index": provider
            } for x in items[:limit] if isinstance(x, dict)]
        else:
            items = (data.get("query") or {}).get("search") or []
            records = [{
                "title": str(x.get("title", ""))[:180],
                "url": "https://en.wikipedia.org/wiki/" +
                       quote(str(x.get("title", "")).replace(" ", "_"), safe="()_-"),
                "snippet": _plain(str(x.get("snippet", "")), html=True, maximum=600),
                "source_index": provider
            } for x in items[:limit] if isinstance(x, dict)]
        # Search result titles/URLs are untrusted; no implicit page visit.
        return [r for r in records if r["title"] and r["url"].startswith("https://")]

    def read(self, url):
        origin = _valid_host(url, resolver=self.resolver)
        request = Request(url, headers={
            "Accept": "text/html, text/plain;q=0.9",
            "User-Agent": USER_AGENT})
        self.call_count += 1
        raw, mime = _load(request, request_fn=self.request_fn)
        if mime not in ("text/html", "text/plain"):
            raise ResearchTransportError("Page was not readable plain text or HTML")
        try:
            content = raw.decode("utf-8", errors="replace")
        except UnicodeError as exc:
            raise ResearchTransportError("Document decode failed") from exc
        text = _plain(content, html=mime == "text/html")
        if not text:
            raise ResearchTransportError("Empty public document")
        return {
            "url": url,
            "origin": origin,
            "text": text,
            "text_sha256": sha256(text.encode("utf-8")).hexdigest(),
            "fetched_at_utc": datetime.now(timezone.utc).isoformat(),
            "mime": mime,
            "verified_fact": False,
        }
