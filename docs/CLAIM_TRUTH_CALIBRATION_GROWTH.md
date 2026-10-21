# BEAN claim-truth growth laboratory

**Status:** Isolated synthetic research branch. **NOT the deployed ChatGPT plugin or BEAN main.**

## Why

A successful unit-test run does **not** demonstrate that a learner invented the underlying code. A benchmark can pass with flawed methodology. A GitHub artifact can exist while a broader product build fails. These are different claims. BEAN must learn from independently measured feedback rather than rewarding optimistic prose.

We reused existing BEAN mechanisms instead of creating a new language model or ledger:

- Core EpistemicGuard: conservative claim screening, *not factual verification*.
- Core EvidenceRankLedger: source/outcome ranking; source labels still *not authentication*.
- Experimental scoreboard_context: interprets matched scoreboard gains without creating fake source truth.
- **Actual updater**: existing PortfolioLedger.observe and replayable Q cache from experimental BEAN PR #143. Q event ID once, source/event fingerprints, true Q-value changes, detailed sidecar evidence and cold restart.

## An explicit learning environment

The claim_calibration_growth.py experiment feeds BEAN a plausible **synthetic** report of test success, learning gain, self-repair, or release readiness. Each report carries a source category, claimed verification, reported confidence and an observable claim category.

The **hidden synthetic oracle** assigns a truth label but only reveals it to the trainer *after* the learner commits to one of three actions:

1. **Tentative** — cautiously accept provisional evidence, **never** claim externally verified success.
2. **Qualify** — report that the observed result or claimed attribution remains unverified.
3. **Unknown** — withhold the success inference while preserving the claim.

Rewards require the withheld simulation outcome. Making a wrong positive success claim incurs a **-4 penalty**, a correct provisional success earns +2, and supported cautious answers earn smaller rewards. Excessive abstention also loses utility when evidence was genuinely reliable. Reward is **never** based on confident wording, number of successful CI jobs alone, a self-reported URL, or a model's claim that the improvement was autonomous.

Claims from three training domains (quality, scheduling, compression) are evaluated on **new** domains (robotics, maintenance, inventory) with shared evidence/source patterns. The holdout receives **zero** Q updates. Every training claim, chosen response, hidden label, reward and receipt is archived in exact lossless gzip JSON. A separate condensed scoreboard is not a replacement for failed trial evidence.

## The specific scientific hypothesis

Does BEAN's learned model-free claim policy outperform all three frozen controls, while reducing wrongly confident success reports on unseen domains? Controls:

- Trust optimistic "verified" declarations at face value;
- Always qualify;
- Always say unknown.

Use **mean heldout utility**, **wrong positive claims**, **correct positive claims**, **coverage**, seed-by-seed results, and exact replay. No unsupported claim of superiority if results tie or regress.

The code changes a BEAN learning policy; it is **not** a self-generated code patch or proof that BEAN discovered its own algorithm. Q updates are real, but this is a synthetic supervised-reward environment.

## Essential authenticity limitation

The synthetic oracle's digest is a **consistency checksum**, not a digital signature or independent verifier. Anyone controlling the synthetic runner could generate a matching fake oracle record. This experiment **does not authenticate** real GitHub Actions, human reports, physical sensor readings, original source authorship, or externally supplied "verified" flags. Claiming that it does would itself be an invented success!

Before connecting a live BEAN tool to production rewards, an independent evaluator must authenticate measurements and source attribution (ideally signed/verified receipts), with verification secrets and holdout labels unavailable to the learner. A human-written better algorithm cannot be credited as a BEAN-self-generated improvement. Real-world claims remain explicitly **unknown** without such evidence. Existing Core EpistemicGuard and the learning ledger must coexist rather than either one bypassing the other.

## Run

From the BEAN experimental checkout:

    python -m unittest bean.tests.test_claim_calibration_growth -v

    python experiments/claim_truth_growth/run.py --episodes 3000 --holdout 400 --out ./private/claim-growth

The 4-job Windows/Linux Python 3.11/3.12 verification matrix runs before the full 3-seed 9,000-update study. Full JSON/SQLite/gzip artifacts and negative outcomes are kept as GitHub Actions workflow artifacts, not silently promoted to Core main or the existing hosted @BEAN plugin.
