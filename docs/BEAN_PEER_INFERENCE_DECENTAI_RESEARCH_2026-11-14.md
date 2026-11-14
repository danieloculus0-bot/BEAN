# BEAN peer inference: DecentAI / DcentAI architecture comparison

## Public-source findings (November 14, 2026)

| Project | Public artifact | Transferable idea | Evidence limit |
| --- | --- | --- | --- |
| Catena Labs DecentAI | https://github.com/catena-labs/decent-ai | User chooses and mixes models; local conversation data and BYO provider | Archived Expo client, MIT; API backend is **not** open-source, and the mobile app is no longer maintained |
| Catena Labs moa-llm | https://github.com/catena-labs/moa-llm | Independent proposal models followed by an aggregator; per-model latency metrics | Archived MIT library; claims of accuracy gains require BEAN-specific paired evaluation |
| HYBRIDY DecentAI | https://github.com/HYBRIDY/DecentAI | Node catalog, advertised prices, request routing and receipts | At inspection the public tree contains README + environment sample, **not** the claimed full contracts/router implementation; no upstream code copied |
| DcentAI | https://www.dcentai.org/ | Separate compute suppliers, storage providers and validators | Public marketing descriptions, not independently authenticated runtime performance or settlement receipts |

## Adaptation on BEAN mainline

BEAN already has its own local llama.cpp adapter, provider interface, and SHA-chained native reasoning journal. Do not replace the memory engine or the existing local default. The new **peer_inference** provider accepts a small explicit catalog of OpenAI-compatible HTTPS compute peers. It selects the lowest quoted maximum cost (then advertised latency and stable ID) for a requested model, makes **one** bounded request, and preserves a node-qualified provider receipt. If a peer fails, it reports the failure and **does not automatically retry** with another remote service.

No background peer discovery, cryptocurrency transfers, wallet, paid-provider activation, or external model invocation happens just by importing BEAN or merging this code. A peer model supplies text only; BEAN retains memory, feedback, strategy selection and execution authority. A peer's model identification, availability, price quote and latency advertisement remain **self-reported** until independently evaluated. Quoted cost is *not* a billing guarantee.

To explicitly use the adapter, configure the authorized environment of the host that runs BEAN:

- BEAN_PEER_INFERENCE_ENABLED=1
- BEAN_PEER_MODEL=local-qwen
- BEAN_PEER_MAX_QUOTE_USD=0
- BEAN_PEER_NODES_JSON=[{"id":"home-gpu","endpoint":"https://your-trusted-gpu.example/v1/chat/completions","model":"local-qwen","quoted_max_cost_usd":0,"advertised_latency_ms":100}]
- Optional BEAN_PEER_TOKEN (held only in the runtime environment, never in the node metadata or committed source)

The peer must expose an HTTPS OpenAI-compatible chat-completions endpoint that returns a model alias, a response ID and nonempty response text. Configure the host's existing BEAN reasoning adapter as peer_inference; when absent, the default local model path is unchanged. An operator who opts into a remote node also chooses to transmit the selected prompt/context to that node. No raw source material or credentials belong in the published registry.

The executable offline acceptance test is:

    python -m unittest bean.tests.test_peer_inference_provider -v

It uses synthetic nodes and an injected HTTP transport, and checks deterministic eligible-node selection, quote limits, disabled-by-default behavior, HTTPS endpoint validation, model identity, bounded responses, failure receipts, secret-free errors, no retry/fallback and native Core response registration. Full BEAN regressions on the PR/main SHA are separate CI evidence.

## Follow-on falsifiable experiment

Run identical held-out question sets against (1) BEAN's existing local model, (2) a single explicitly opted-in peer, and (3) a Catena-style multi-model aggregator. Preserve separate raw answers, objective evaluator scores, cost quotes vs actual bills, network failures, p50/p95 response times and prompt-disclosure choices in the *existing* Core research ledger. Prefer the peer/mixture only if an independently measured benefit survives a held-out evaluation. Nothing here implies a new learned policy, an independently functioning P2P network, or consciousness.
