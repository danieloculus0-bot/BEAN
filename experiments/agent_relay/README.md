# BEAN experimental agent relay (unbranded)

**Research prototype, not a deployed dating service.** Source lives on a
separate experiment branch, not BEAN Core's production execution path.
Existing BEAN Core reasoning/provider adapters can be called locally through
`model_signal`; the transport itself is model independent.

## Working contract

Two separate authenticated clients exchange versioned, anonymous,
allowlisted categorical envelopes over a real local HTTP relay. Each agent
has its own bearer capability. Relay validates sender ownership and message
shape, enforces bounded queues, prevents duplicate/replayed message IDs, and
does not store human profiles, conversation text, addresses or credentials.
The human owner's private profile and negotiation prompt remain inside the
local agent. No human was matched, profiled or contacted in this experiment.

Try the executable two-agent demo:

```bash
python -m experiments.agent_relay.demo
python -m unittest experiments.agent_relay.test_relay -v
```

Start the independent server with two private runtime credentials:

```bash
export BEAN_RELAY_AGENTS_JSON='{"agentA":"replace-with-random-capability-at-least-24-chars","agentB":"another-independent-random-capability-at-least-24-chars"}'
python -m experiments.agent_relay.relay --port 8779
```

Other processes can import `AgentClient` and `protocol.message`, sending
to `/v1/messages` and polling `/v1/inbox`. This branch intentionally
binds loopback only. Remote public federation would require separately
reviewed authentication, transport security and explicit profile-disclosure
consent controls.

## Preference negotiation example

A potential candidate with a **synthetic** value of 150 is below another
**synthetic** person's preferred threshold of 160. A local flexible
preference returns `ask_local` for the human instead of silently rejecting.
That value never enters the inter-agent message. Each personal AI decides
what to ask its own human before any introduction.

## Existing BEAN reuse and boundaries

- BEAN Core provider contract: `bean/reasoning/llm_adapter.py`.
- Optional real local inference: `bean/reasoning/ollama_provider.py`.
- Existing interaction model: `bean/relationship/`.
- BEAN Bridge learning and evidence: `bean/learning/bridge.py`.
- Existing separate Bridge repository:
  `danieloculus0-bot/BEAN-AI-Bridge-` (currently ERP/evidence oriented).
- Do not copy ERP data, private notes, user histories, or credentials to
  this repo or GitHub Actions.

The relay provides **no end-to-end encryption**, no guaranteed anonymous
network identity, no durable multi-server delivery, no real-world relationship
predictive validation, and no live provider proof. Topic-category disclosure
can still enable inference or linkage across interactions. This deliberately
minimal exchange is a starting point for privacy review, not a privacy
guarantee. Real agent intelligence depends on an available model provider.
Synthetic test success proves transport and bounded behavior only.

## First feature acceptance

Two independent HTTP clients exchange messages successfully; a flexible
preference narrowly misses by 10 units; the recipient's own agent asks
locally instead of rejecting. The local-only preference data never crosses
the relay. This is the testable precursor to the launch-film scene.
