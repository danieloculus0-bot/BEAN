"""Nightly read-only smoke of published GitHub Pages ecosystem entry points.

This checks actual HTTP responses and navigation markers, not application state,
record propagation, authentication or integrations. No credentials or uploads.
"""
from __future__ import annotations

import sys
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

BEAN = "https://danieloculus0-bot.github.io/BEAN/"
ERP = "https://danieloculus0-bot.github.io/Axiom_Beta/erp/"
HUB = BEAN + "portfolio/"

# Required markers are literal source strings that identify the correct
# published document and its outward navigation. A 200 alone is insufficient.
ROUTES = {
    BEAN: (ERP, "Project directory"),
    HUB: (ERP, "EZ CAM", "EZ Attendance"),
    BEAN + "axiom.html": (ERP, "Axiom"),
    BEAN + "portfolio/axiom/": (ERP, HUB, "Command Center", "Job Passport"),
    BEAN + "portfolio/ez-office/": (ERP, "EZ-Office"),
    BEAN + "portfolio/ez-fair/": (ERP, "EZ-FAIR"),
    BEAN + "portfolio/bean-learning/": (ERP, "BEAN"),
    BEAN + "aiscend.html": (ERP, HUB),
    ERP: (HUB, 'id="module-nav"', 'id="menu-search"'),
    "https://danieloculus0-bot.github.io/Axiom_Beta/ewi/": (HUB, 'id="job-select"'),
    "https://danieloculus0-bot.github.io/Axiom_Beta/lab/": (HUB, 'data-view="passport"'),
    "https://danieloculus0-bot.github.io/EZstimate/": (HUB, "EZ Estimate"),
    "https://danieloculus0-bot.github.io/EZ-FEA/": (HUB, "EZ-FEA"),
    "https://danieloculus0-bot.github.io/EZ-CAM/": (HUB, "EZ CAM"),
    "https://danieloculus0-bot.github.io/FUN/": (HUB, "EMPEROR GAUNTLET"),
    "https://danieloculus0-bot.github.io/64-/": (HUB, "64Δ"),
    "https://danieloculus0-bot.github.io/EZ-Attendance/": (HUB, "EZ Attendance"),
    "https://danieloculus0-bot.github.io/EZ-Office/": (HUB, "EZ-Office"),
}


def check(url: str, markers: tuple[str, ...]) -> None:
    request = Request(url, headers={
        "User-Agent": "Axiom-Ecosystem-ReadOnly-Smoke/1.0",
        "Cache-Control": "no-cache",
    })
    with urlopen(request, timeout=15) as response:
        status = response.status
        body = response.read(750_000).decode("utf-8", errors="replace")
    if status != 200:
        raise ValueError(f"HTTP {status}")
    missing = [mark for mark in markers if mark not in body]
    if missing:
        raise ValueError("missing expected published markers: " + repr(missing))


def main() -> int:
    errors = []
    for url, markers in ROUTES.items():
        try:
            check(url, markers)
            print("OK", url)
        except (OSError, UnicodeError, ValueError, HTTPError, URLError) as error:
            print("FAIL", url, str(error), file=sys.stderr)
            errors.append(url)
    print(f"Checked {len(ROUTES)} URLs; {len(errors)} failed")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
