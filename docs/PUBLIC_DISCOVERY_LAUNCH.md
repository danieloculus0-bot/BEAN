# BEAN public discoverability launch checklist

The BEAN Core source, public demo and research record live on GitHub. `docs/index.html` is a static search-friendly landing page but **adding it to a repository does not publish a live website on its own**.

## Owner action in GitHub (needs repository Settings access)

1. Open [BEAN repository Pages settings](https://github.com/danieloculus0-bot/BEAN/settings/pages).
2. Under **Build and deployment**, select **Deploy from a branch**, branch **main**, folder **/docs**, then **Save**.
3. After GitHub reports successful deployment, check the published page in Pages settings. Expected project-site form, subject to GitHub's actual settings, is `https://danieloculus0-bot.github.io/BEAN/`.
4. Confirm the live page renders, the guide and research links work, and the site contains no private data.

## Repository metadata (also requires Settings / Edit repository details)

Suggested description (verify before pasting):

> Persistent AI reasoning and evidence architecture in Python: SQLite memory, uncertainty, contradiction review, traceable proposals, reproducible tests.

Suggested topics (pick relevant ones; no unsupported claim of production readiness):

`ai-agents`, `persistent-memory`, `reasoning-engine`, `sqlite`, `evidence-provenance`, `python`, `explainable-ai`.

Suggested website after Pages is live: the GitHub Pages URL confirmed in Settings.

## Follow-up credibility steps

- Add an intentional **LICENSE** after selecting a license. The repository currently does not advertise a reuse grant merely because its source is visible publicly. Avoid calling it open source until this is resolved.
- Define a versioned release with an exact commit, scope, reproducible test run, known limitations and migration notes; do not use raw repository size as proof of capability.
- Add a screenshot or recorded terminal run of the actual offline demo after verifying it. Avoid staged autonomous behaviors.
- When the published site is accessible, check its indexability with relevant search engines. If desired, verify ownership in their webmaster consoles; public indexing is never guaranteed.
- Seek independent reproducibility: an outside developer should be able to run the quickstart and report operating system, Python version, exact commands and results.
- Track real demand with GitHub traffic/referrers and issue reports. Do not invent visitor metrics.

## Engineering boundaries

The site deliberately describes the existing implementation and links the experimental findings rather than claiming fully autonomous intelligence. No ERP or company data, proprietary assets, credentials, or actual device control belong on the public pages. GitHub Pages remains publicly viewable.

Relevant GitHub instructions: https://docs.github.com/en/pages/getting-started-with-github-pages/configuring-a-publishing-source-for-your-github-pages-site
