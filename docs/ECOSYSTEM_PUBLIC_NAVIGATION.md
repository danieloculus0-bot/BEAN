# Public ecosystem navigation contract

One discoverable public workshop catalog, one canonical Axiom ERP browser demo, and clear return paths from independent projects. This document describes publicly reachable entry points and does not imply shared authentication, business records, ERP synchronization, BEAN integration, or remote actions.

## Shared navigation implementation (November 20, 2026)

The cross-project source audit covered **42 HTML entry points across 13 repositories**: BEAN (18), Axiom_Beta (5), EZ-CAM (2), EZ-FEA (3), EZstimate (2), EZ-Office (1), EZ-Construction (1), FUN (4), 64- (1), EZ-Attendance (1), EZ_Expedite (1), ForgeVault (1), and venvWin's portable arcade editions (2). This counts source entry points, not 42 independently deployed public websites.

Each updated page has a direct BEAN Home route and an All Projects route, together with Latest Build and navigation to other significant labs. Public pages use the shared charcoal/lime BEAN navigation styling from [`docs/ecosystem-nav.css`](ecosystem-nav.css) while preserving their app-specific layout, colors, controls and domain scope. Fullscreen games use a compact floating BEAN return menu rather than shifting the game canvas. Offline-first EZ-Office, BEAN Core Demo and RMA PWAs keep a local copy or cache of the navigation stylesheet so adding ecosystem chrome does not introduce a network requirement for their core offline flows.

**Canonical routes:** [BEAN Home](https://danieloculus0-bot.github.io/BEAN/), [All Projects](https://danieloculus0-bot.github.io/BEAN/portfolio/), [Current Build](https://danieloculus0-bot.github.io/BEAN/status.html), [BEAN Draw](https://danieloculus0-bot.github.io/BEAN/bean-draw/), [Axiom ERP](https://danieloculus0-bot.github.io/Axiom_Beta/erp/), [AutoNest](https://danieloculus0-bot.github.io/Axiom_Beta/erp/autonest.html), [Brake Simulation](https://danieloculus0-bot.github.io/EZ-CAM/brake-lab.html).

**Evidence boundaries:** The home, Workshop and Core Demo pages highlight the November 20 source milestones, including original model-generated drawing attempts and persistent ordered plans. They do not claim every separate demo has a live BEAN connection. The source test `tests/test_public_ecosystem_chrome.py` enforces return links for every BEAN HTML file; Axiom has `web/ecosystem-navigation.test.mjs`. Browser regressions, including Core Demo offline restart and the EZ-Office offline suite, were exercised through GitHub Actions. Links and successful deployment workflows are not a substitute for independent human visual checks across every device. Standalone EZ-Office's separate Pages workflow cannot create its Pages site with the current GitHub Actions integration permission; the BEAN Workshop copy is a separate published route with its own checks.

**Maintenance contract:** Any new public or packaged HTML demo should include the global BEAN navigation, keep a direct one-click BEAN Home link, preserve its current workflow, and link to the dated current-build evidence page rather than hard-coding untested capability claims. Regenerate navigation-source tests when adding pages, and copy/update the shared CSS for offline-first apps.

## Canonical destinations

| Purpose | Public entry point | Meaning |
| --- | --- | --- |
| Discover projects | https://danieloculus0-bot.github.io/BEAN/portfolio/ | Canonical project catalog, search, category filters, source links |
| Main Axiom application | https://danieloculus0-bot.github.io/Axiom_Beta/erp/ | Canonical browser-local, synthetic ERP demo |
| Operator EWI and clocking | https://danieloculus0-bot.github.io/Axiom_Beta/ewi/ | Separate browser-local operator demonstration |
| Evidence lab | https://danieloculus0-bot.github.io/Axiom_Beta/lab/ | Distinct standalone evidence experiment, not primary ERP |
| BEAN home | https://danieloculus0-bot.github.io/BEAN/ | BEAN project landing and research |
| Axiom architecture | https://danieloculus0-bot.github.io/BEAN/axiom.html | Explanatory overview linking to the actual application |
| Interactive Axiom portfolio lab | https://danieloculus0-bot.github.io/BEAN/portfolio/axiom/ | Preserved standalone interactive **synthetic browser lab**, with explicit routes to the canonical ERP and Workshop |

Other public apps are listed and linked by the project directory. Desktop-only and early-stage repositories have source links rather than fabricated demos.

## Navigation rules

- Each independent public application or overview must offer a clear route back to the project directory and/or Axiom ERP.
- Keep the user-approved /BEAN/portfolio/axiom/ dashboard interactive and visually intact. It is a distinct browser lab and must NOT auto-redirect to the Axiom ERP; show clear links between the two instead.
- Axiom's internal department navigation and record-aware Open with retain responsibility for exact job, part, PO, machine, inspection and NCR identity. Cross-site links must not invent record context or replace the canonical module state.
- Do not redirect a user's active ERP context to a made-up record. Cross-site entry links open the application landing route, not a guessed `#job` or `#ncr`.
- Internal app controls, native browser context menus on editable fields and links, existing application state, and synthetic-data boundaries remain intact.
- A public link is navigation, not evidence of a live BEAN API, JobBOSS connection, HR approval, payroll transaction, or manufacturing authorization.
- Historic demonstrations with genuinely distinct functions can remain labeled as labs; redundant simulations must route to the canonical implementation.
- No real employer/customer/shop records, images, drawings, credentials, or uploads may enter these public pages.
- Match the approved Axiom lab visual language across BEAN site pages over time: charcoal/black canvas, compact dashboard panels, structured navigation, small lime accent. Preserve each existing tool and its accessibility.

## Verification

- Run `python -m unittest discover -s tests -p 'test_ecosystem_navigation.py' -v` in BEAN for source-level route and legacy-redirect checks.
- Run `node --test web/ecosystem-navigation.test.mjs` in Axiom_Beta for the application's entry-point and preservation checks. Axiom Browser Lab CI includes the test.
- After publication, `python scripts/verify_ecosystem_live.py` performs read-only HTTP checks of actual published pages, expected route links and recognizable application markers. This runs nightly and on workflow dispatch.
- These tests establish navigation and page identity only. They do not prove cross-service synchronization, authentication, browser compatibility or all user workflows. Use the application's own CI and browser tests for functionality.

## Publication dependency

BEAN navigation PR #209 replaces superseded partial PR #207. Axiom_Beta PR #94 provides return links. Independent apps each have their own small navigation PR. Publish through each owning repository's normal review and Pages process; do not duplicate application code into the workshop.
