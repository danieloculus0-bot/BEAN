# BeanRivet public concept portal

**Stage:** branding and proposed economics only, November 9, 2026.

**Public Pages path:** `https://danieloculus0-bot.github.io/BEAN/beanrivet/` from `docs/beanrivet/index.html`.

BeanRivet (`BNRVT`) is the working name/ticker for a possible utility token serving the BEAN and AIscend ecosystem. **No token, contract, network, presale, investment offer, wallet collection, token payments, audit, or legal clearance is asserted.**

## Relationship to existing projects

- **BEAN:** experimental model-independent reasoning, memory continuity and evidence research. Its Core is separate from this page.
- **AIscend:** experimental crypto strategy, desktop and wallet research. It is not an established profitable strategy or decentralized compute provider.
- **BeanRivet:** proposed service-metering and treasury economics. The concept page does not wire BEAN and AIscend together.

## Demonstration assumptions

The calculator models illustrative token-denominated eligible protocol fees less costs and obligations, then splits any positive result into equal burn and community treasury allocations.

```text
eligible_surplus = max(0, eligible_fee_receipts - service_costs_and_obligations)
proposed_burn   = eligible_surplus / 2
community_pool  = eligible_surplus / 2
```

The calculator is browser-only, sends no data, makes no price or market forecasts and does not simulate an actual blockchain. All customer-owned prepaid balances must remain outside eligible surplus. Fees or round-ups would require clear consent and published terms.

## Publication gate

This page is a static educational concept, not a token sale. Before any real token launch:

1. Verify that the name/ticker is legally usable and choose a chain.
2. Produce a tokenomics specification, accounting policy and independent legal review.
3. Implement separate metering and accounting, with tests proving customer balances cannot be swept.
4. Complete testnet contracts, fee/treasury accounting, security review and on-chain burn proofs.
5. Publish a specific deployment and its audited artifacts. Do not reuse this concept as evidence of a live token.

All source links and operational claims in the public page must be kept accurate. Never commit credentials, private BEAN memory, real employer data or wallet secrets.

## Local smoke checks

Open `docs/beanrivet/index.html` in a modern browser and verify keyboard navigation and responsive layout. Change the receipt/cost fields to verify the formulas: `10000 - 3000 = 7000` surplus, `3500` burned and `3500` community. Costs greater than receipts should produce zero, not a negative burn. Inspect the page for remote requests and ensure it has no wallet-connect or payment capability.
