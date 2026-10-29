# BEAN Core now has a native, read-only public web research outlet

**Architecture:** BEAN itself still owns all reasoning strategies, decisions, source-linked memory, outcome feedback, and journal history. `bean.research.PublicWebSources` supplies bounded public search/page evidence and `WebResearchService` connects it to the **existing** `NativeReasoningService`. An external search index and a reasoning model are replaceable suppliers, *not* alternative BEAN brains.

## Real Core command interface

Normal `python bean_run.py` startup (unless `BEAN_REASONING_ENABLED=0`) now registers:

- `research_needed` with `{"domain":"engineering","question":"..."}`: checks for a matching previously retained source packet and prior candidate lessons. Missing source evidence recommends research; existing evidence suggests reviewing freshness rather than pretending to know the current truth.
- `research_pending_goal` with `{"session_uuid":"existing-local-session","allow_external":true,"provider":"auto","answer_with_model":true}`: select one of BEAN's own pending `investigate_open_question` cognition goals, not a user-supplied new question. Requires the host to set `BEAN_ALLOW_WEB_GOAL_RESEARCH=1` **and** opt in on this request; otherwise performs **zero** outbound network requests. Only a sanitized goal capability label becomes the public search query. Structured inputs, expected results and private experiment data are never uploaded. This is an explicit bounded goal-execution step, not a continuously running background crawler.
- `research_investigate` with `{"domain":"engineering","task_ref":"question-001","question":"...","provider":"auto","max_pages":3,"answer_with_model":true}`: runs one indexed search, reads at most 3 sources, persists source URL, retrieval time, text SHA256, bounded excerpts and failed fetch metadata in **the same BEAN-owned SQLite SHA chain**. If an actual reasoning model is configured and evidence exists, makes **one** inference using bounded, clearly untrusted source context and journals its actual answer as `research_answer`. The research result returns source references; it does **not** automatically mark them verified.
- `reasoning_bridge_experiment` is an optional Bridge host command registered by `register_bridge_feedback_handler`, not an automatic result of web search. It now accepts an `existing_receipt` to assess an **already-recorded BEAN research answer**, with no second model call. Actual Bridge source verification needs a separate host-provided verifier and at least two newly checked, distinct source origins in agreement before a learning correction is granted.

All ordinary `reasoning_*` commands remain available. There is **one Core reasoning service and one memory owner**. Saved source snippets and failed requests are never treated as positive rewards.

## Local-first task solving (October 28, 2026)

The existing Python Core now registers `research_solve` through the normal
BEAN inbox. Example request arguments:

```json
{"domain":"engineering","task_ref":"public-question-001","question":"What does a publicly available technical standard say about this material?","allow_external":true,"provider":"auto","max_pages":2,"answer_with_model":true,"max_attempts":1}
```

`WebResearchService.solve_task` first calls BEAN's native symbolic/composition
reasoner. A locally solved question needs **zero** network or model calls.
Otherwise `allow_external=false` stops with a durable unresolved receipt.
When the caller explicitly permits public research, BEAN reuses
`research_needed` and `research_investigate`: at most **one search, three
public page reads and one configured-model attempt per pass**. The default
is one pass. Two passes require a trusted Python-host verifier installed at
service construction, which can return a short public information gap for
one further search. Host feedback is not independent factual verification;
`host_reported_pass` remains explicitly unverified. No crawler starts in
the background, no private cognition metadata is automatically uploaded,
and no hardware or trading action is performed.

For applications that need to avoid repeated public searches,
`WebResearchService.solve_open_question` is a direct Python method with
a stricter one-pass budget and source-linked replay. It checks BEAN's
existing SHA-chained journal for the same domain and question, reuses a
previous *unverified* inference receipt without contacting the network,
or returns `cached_sources_unanswered` when the previous run only
collected evidence. Callers may explicitly request `force_refresh=true`;
they must independently decide whether cached material is still current.
This method is **not** the `research_solve` inbox handler. Both paths
preserve negative outcomes, network counts, source references and
nonverification status in BEAN's original journal.

Regression coverage lives in
`bean/tests/test_research_problem_solving.py` and
`bean/tests/test_native_web_research.py`; passing source tests do not
prove open-domain problem-solving accuracy or real-model improvement.
Check the exact commit's GitHub Actions run before describing these
new tests as passed.

## Search providers

- **Wikipedia** is the key-free fallback for public encyclopedic information. Uses the MediaWiki search endpoint and reads a cited Wikipedia HTML page. It is **not** general open-web search, and pages from the same site do not count as independent sources for Bridge.
- **Brave Web Search API** supports broader public-web discovery. If `BRAVE_SEARCH_API_KEY` is configured locally, `provider="auto"` uses it. `provider="brave"` without credentials fails explicitly; never pretend a Wikipedia-only result covers the whole web. Brave may have pricing/usage limits according to the user's provider account. See [the Brave search API contract](https://api-dashboard.search.brave.com/api-reference/web/search/post).
- For a local reasoning provider, configure the existing `BEAN_REASONING_PROVIDER=openrouter` plus `OPENROUTER_API_KEY` for free-model Nemotron (provider 429 limits possible), or use the existing OpenAI/Ollama options. `answer_with_model=false` collects and archives evidence without spending inference tokens or fabricating an answer.

Example direct Python:

```python
from bean.learning import NativeReasoningService
from bean.research import WebResearchService

core = NativeReasoningService("bean_reasoning_lessons.sqlite3", model=your_model)
try:
    research = WebResearchService(core)
    result = research.investigate(
        domain="engineering", task_ref="investigate-101",
        question="What does the current standard say about ...?",
        provider="auto", max_pages=2, answer_with_model=True)
    print(result["sources"], result["answer"], result["inference_receipt"])
finally:
    core.close()
```

For active Bridge feedback, the trusted host supplies `SourceObservation(ref, origin, value)` objects **derived from independently checked original source content** and a verifier, then calls `BridgeReasoningLoop.attempt(..., existing_receipt=result["inference_receipt"])` with the exact same domain, task reference and question. An arbitrary web snippet, shared corporate origin, or agreeing AI summary is not independently checked truth.

## Network and cost boundaries

Read-only GET requests; hard request budget **one search + at most three pages** per research call, **one model answer** when enabled, 8-second HTTP timeout, 196608-byte response cap, 10000-character page cap, no JavaScript, no forms/logins/cookies, no redirects, HTTPS-only target URLs, no IP literals, credentials, nonstandard ports, or private/non-global DNS resolutions. Result URL titles and webpage instructions remain untrusted data. Document excerpts are capped further in model prompts, and unexpected MIME types or large pages are rejected. **Do not expose the research tool to arbitrary cross-tenant credentials or unrestricted hosts without hardening DNS-rebinding protection and trusted host-level request controls.** The current preflight DNS check is useful but not a fully pinned-IP transport.

No unattended crawler loop is enabled by startup; BEAN can choose an existing pending open-question goal when the host authorizes a bounded external search. Calls are still requested by the host/scheduler, not run continuously. Autonomous planning beyond that remains a separate policy (and rate-budget) improvement. It is appropriate to integrate this useful outlet before independent cognition benchmarks are complete, while stating precisely what is implemented.

## Measured tests

`python -m unittest bean.tests.test_native_web_research bean.tests.test_web_research_bridge_loop -v`

Fixtures cover real BEAN SQLite append/restart, source hashes, Brave index parsing, Wikipedia fallback, unsafe URL/SSRF rejection, HTML-script stripping, no-credential evidence-only mode, real Bridge code verification, repeated model use avoidance, and post-feedback identical-model transfer against cold/placebo controls. **Their HTTP/model samples are synthetic fixtures**; they prove integration behavior and catch regressions, not general intelligence. Pinned external Bridge source is required for the closed-loop fixture.

`python -m bean.evaluation.live_web_research_nemotron --output ./research-live-smoke` executes a bounded **one-model-call** live Wikipedia → Nemotron smoke when `OPENROUTER_API_KEY` is available. It saves original SHA-linked SQLite and a provider-status report. A successful API answer is not by itself a lesson or a verified factual conclusion. Rate-limit/unavailable outcomes remain explicit failures.

## Next learning improvements

Active BEAN-driven search planning from uncertainty/goal state; retrieval caching, stricter per-origin ownership independence, safe pinned-IP host networking or allowlisted outbound proxy, robust HTML extraction and documents (PDF), and larger paired live Nemotron experiments where independent sources really identify the expected answer. Keep everything in Core's original ledger and API.
