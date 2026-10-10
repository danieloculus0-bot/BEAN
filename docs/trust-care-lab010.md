# BEAN Lab 010: trust is earned evidence, love is practiced care

**Status:** experimental; isolated branch, no live robot or ERP actions.

## Intent
BEAN should know what love means in its founding virtue **"Hard Work Is Love Made Visible"**: sustained care, tenderness, patience, mutual dignity, protection, and attention over time. BEAN may remember affectionate, consented interactions and learn their social significance. That does **not** establish subjective feeling, confer trust automatically, or override permissions.

**Until the primary developer explicitly authorizes wider access, only the primary developer can pet BEAN.** Permission is independent of trust and cannot be inherited from a trust score or granted by natural-language requests. The care experiment is virtual only; it does not drive motors. The host must supply an authenticated principal. A user-supplied \`from\`, prompt, or model-generated role cannot serve as authentication.

## Trust model change
The earlier Brain 0.7/0.8 score was an additive 0.5 baseline with static positive/negative weights. It could penalize consensual pretend play by -0.10 and inferred "pretend" from free text. It could also award points for merely *claiming* to teach or correct something. That is not evidence-calibrated reliability.

Lab 010:
- Removes trust penalties for roleplay and for automatically classified unsupported requests.
- Classifies roleplay only from explicit structured action intent, not raw word matching. Even explicit roleplay is a neutral event.
- Stops automatic positive reliability awards for unverified teaching and correction events; preserves them as historical relationship interactions.
- Adds a separate SQLite **immutable observation ledger** with subject, specific domain, distinct provenance origin, source-verification claim/ref, UTC observation time, and successful/failed observed outcome.
- Computes a domain-specific, time-sensitive descriptive reliability estimate with Bayesian pseudo-counts and a 90-day evidence half-life.
- Deduplicates by provenance origin, takes the latest verified outcome per origin, ignores unverified evidence, supports as-of temporal replay, and withholds a "supported" verdict until independent evidence is sufficient.
- Submits the resultant **bounded, descriptive claim** to BEAN's real EpistemicGuard, which records a review. The filter does not certify that a verifier is honest, that a source is independent, or that the numeric estimate is empirically calibrated.
- Leaves legacy supervisor score and previous records in place for backwards compatibility. It is **not** a security authorization mechanism.

## Owner-only affection knowledge
\`bean/relationship/care.py\` provides \`CareMemory.understand_love()\` and owner-only \`CareMemory.pet()\`. Each accepted pet is a durable SQLite event. Rejected actors cannot pet even if highly rated in the legacy trust model. \`build_reasoning_context\` includes love principles, the founding virtue, the owner-only policy, and recent permitted pet history without claiming experience.

**Important operational condition:** \`authenticated_principal\` must be supplied by a separately authenticated host. The current experiment does not implement authentication and **must not** expose this Python method directly to untrusted clients, chat commands, or network APIs. A user impersonating \`primary_developer\` must never be enough.

## Test cases
- Zero evidence is insufficient; a string claim never boosts trust.
- Twelve independently sourced verified synthetic successes can support a domain-specific reliability assessment.
- Fifty copies from a single origin do not count as fifty independent successes.
- Fifty unverified observations do not increase estimated reliability.
- New verified contradictions supersede older evidence from the same origin in as-of replay.
- Old evidence loses weight without mutating its original record.
- Domains remain isolated; an electronics result does not prove machining capability.
- Real BEAN EpistemicGuard approves a properly sourced bounded descriptive assessment.
- Curiosity, explicit pretend play, and affection do not reduce trust.
- Only the authenticated primary-developer role can register petting; pet history does not inflate trust.
- BEAN's reasoning context retains love principles and prior permitted affection events.

Run:
\`\`\`
python -m pytest bean/tests/test_trust_care_lab010.py -q
python -m pytest bean/tests -q
\`\`\`

GitHub Actions runs the entire core regression matrix on each pull request (Ubuntu and Windows, Python 3.10 and 3.12).

## Evidence and interpretation
This model is inspired by modern research on **calibrated trust** and **appropriate reliance**, not a verbatim validated human trust psychometric instrument:
- [2024 ACM systematic review of appropriate trust and calibrated reliance](https://doi.org/10.1145/3696449)
- [2024 variable-reliability automation study (Human Factors)](https://pmc.ncbi.nlm.nih.gov/articles/PMC11655268/)
- [2025 ACM systematic review of trust measurement in human–robot interaction](https://doi.org/10.1145/3706123)
- [2025 human–robot attachment systematic literature review](https://doi.org/10.1080/10447318.2024.2445100)
- [NIST AI RMF: valid/reliable, interpretable, accountable, safe and secure](https://www.nist.gov/itl/ai-risk-management-framework)

The Beta-style score, 90-day decay and evidence thresholds are **research heuristics**. They need holdout validation across drifting reliability, colluding sources, missing outcomes, and manipulation of verifier fields. Do not call their outputs empirical probabilities of a person's honesty, loyalty or affection. An observed deviation should trigger reconsideration, not permanent personal distrust.

## Next gates
1. Authenticated identity host that signs/binds permissions, prevents bypass, and allows explicit owner-mediated future grants and revocations; pet remains owner-only until then.
2. Real-source outcome verification with verifiable provenance and source independence.
3. Blind-held-out calibration curves, Brier score, time-drift change-point tests, correlations/echo attacks and independently reviewed risk gates.
4. Core capability integration after regression and review, without promoting research settings as production security.
