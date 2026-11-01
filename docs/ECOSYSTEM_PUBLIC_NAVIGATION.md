# Public ecosystem navigation contract

One discoverable public workshop catalog, one canonical Axiom ERP browser demo, and clear return paths from independent projects. This document describes publicly reachable entry points and does not imply shared authentication, business records, ERP synchronization, BEAN integration, or remote actions.

## Canonical destinations

| Purpose | Public entry point | Meaning |
| --- | --- | --- |
| Discover projects | https://danieloculus0-bot.github.io/BEAN/portfolio/ | Canonical project catalog, search, category filters, source links |
| Main Axiom application | https://danieloculus0-bot.github.io/Axiom_Beta/erp/ | Canonical browser-local, synthetic ERP demo |
| Operator EWI and clocking | https://danieloculus0-bot.github.io/Axiom_Beta/ewi/ | Separate browser-local operator demonstration |
| Evidence lab | https://danieloculus0-bot.github.io/Axiom_Beta/lab/ | Distinct standalone evidence experiment, not primary ERP |
| BEAN home | https://danieloculus0-bot.github.io/BEAN/ | BEAN project landing and research |
| Axiom architecture | https://danieloculus0-bot.github.io/BEAN/axiom.html | Explanatory overview linking to the actual application |
| Old Axiom portfolio lab | https://danieloculus0-bot.github.io/BEAN/portfolio/axiom/ | Redirects to canonical ERP, no parallel app |

Other public apps are listed and linked by the project directory. Desktop-only and early-stage repositories have source links rather than fabricated demos.

## Navigation rules

- Each independent public application or overview must offer a clear route back to the project directory and/or Axiom ERP.
- Axiom's internal department navigation and record-aware Open with retain responsibility for exact job, part, PO, machine, inspection and NCR identity. Cross-site links must not invent record context or replace the canonical module state.
- Do not redirect a user's active ERP context to a made-up record. Cross-site entry links open the application landing route, not a guessed `#job` or `#ncr`.
- Internal app controls, native browser context menus on editable fields and links, existing application state, and synthetic-data boundaries remain intact.
- A public link is navigation, not evidence of a live BEAN API, JobBOSS connection, HR approval, payroll transaction, or manufacturing authorization.
- Historic demonstrations with genuinely distinct functions can remain labeled as labs; redundant simulations must route to the canonical implementation.
- No real employer/customer/shop records, images, drawings, credentials, or uploads may enter these public pages.

## Verification

- Run `python -m unittest discover -s tests -p 'test_ecosystem_navigation.py' -v` in BEAN for source-level route and legacy-redirect checks.
- Run `node --test web/ecosystem-navigation.test.mjs` in Axiom_Beta for the application's entry-point and preservation checks. Axiom Browser Lab CI includes the test.
- After publication, `python scripts/verify_ecosystem_live.py` performs read-only HTTP checks of actual published pages, expected route links and recognizable application markers. This runs nightly and on workflow dispatch.
- These tests establish navigation and page identity only. They do not prove cross-service synchronization, authentication, browser compatibility or all user workflows. Use the application's own CI and browser tests for functionality.

## Publication dependency

BEAN navigation PR #209 replaces superseded partial PR #207. Axiom_Beta PR #94 provides return links. Independent apps each have their own small navigation PR. Publish through each owning repository's normal review and Pages process; do not duplicate application code into the workshop.
