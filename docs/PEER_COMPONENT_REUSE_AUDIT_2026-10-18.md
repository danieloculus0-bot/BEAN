# BEAN peer-component reuse audit, 2026-10-18

**Scope:** Independently written BEAN experiment-evidence module. This is not legal or patent clearance. No external source files were copied and no runtime dependency was added.

## License files inspected directly

| Project | Original source | License | Decision |
|---|---|---|---|
| OpenHands | [LICENSE](https://github.com/OpenHands/OpenHands/blob/main/LICENSE) | MIT | Adopt independent-test and benchmark receipt ideas |
| SWE-agent | [LICENSE](https://github.com/SWE-agent/SWE-agent/blob/main/LICENSE) | MIT | Adopt replayable task trajectory concepts |
| Letta | [LICENSE](https://github.com/letta-ai/letta/blob/main/LICENSE) | Apache 2.0 | Adopt persistence/versioned-memory concepts, no Letta package |
| LangGraph | [LICENSE](https://github.com/langchain-ai/langgraph/blob/main/LICENSE) | MIT | Adopt durable checkpointing concepts |
| Microsoft AutoGen | [LICENSE-CODE](https://github.com/microsoft/autogen/blob/main/LICENSE-CODE) | MIT for code; separate documentation rights | Orchestration architecture reference only |
| Microsoft Agent Framework | [LICENSE](https://github.com/microsoft/agent-framework/blob/main/LICENSE) | MIT | Potential future adapter, not adopted |

These are upstream main-branch license files, **not version-pinned dependency attestations**. The rights of model weights, datasets, fonts, images, plugins, and transitive dependencies need separate review if actually bundled.

## Code actually adopted

The new [learning_evidence.py](../bean/evaluation/learning_evidence.py) independently implements, in Python's standard library only:
- Stage-typed observations, hypotheses, experiments, reflections, changes, and reviews.
- SQLite namespaced append-only-by-API receipts with source references, timestamp, and SHA-256 linked hashes.
- Replay verification, duplicate-idempotency, and collision detection.
- Paired three-arm experiments with equal declared model, model revision, document/protocol digests, token budgets, and scoring reference.
- Score and latency differences without claiming causal learning.

**No upstream code copied.** Original copyright ownership and licensing remain with upstream authors. If later incorporating any third-party source, verify exact revision and file licenses, preserve required license and copyright notices, and record changes and attribution.

## Safety and legal boundaries

MIT generally allows commercial use but requires preserving the applicable license/copyright notices when reusing covered software. Apache-2.0 also requires its attribution, license and any applicable NOTICE handling, and contains patent provisions. Avoid silently incorporating GPL/AGPL/unknown-licensed code into proprietary software. This is an engineering screening, not legal advice or noninfringement assurance.

No change to BEAN's chosen redistribution posture occurs. No code in this addition provides remote actions, model access, trading or actuator control. A self-consistent DB hash chain cannot authenticate external sources or defend against full DB replacement. Trial scores are host assertions, and matched experiments still need independent replication and blind holdouts.

## Promotion criteria

The new source and tests should pass BEAN full regression across Windows/Linux and supported Python versions. Later integration with BEAN's canonical event history requires design review to prevent competing sources of truth. Any new binary distribution needs a dependency/SBOM and asset-license audit.
