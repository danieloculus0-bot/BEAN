# BEAN local reasoning first, cheap external counsel only when needed

**Status:** native Python Core experimental capability, intentionally CPU-only; no requirement for a local language model, CUDA, OpenRouter usage or background agent. Integrates into existing `NativeReasoningService` and existing SHA-chain `ExperienceBank`.

## Source-checked provider costs (October 25, 2026)

[OpenRouter Qwen3.5-Flash](https://openrouter.ai/qwen/qwen3.5-flash-02-23) currently advertises **$0.065 / 1 million input tokens** and **$0.26 / 1 million output tokens**. This is a low-cost cloud *language inference provider*, not BEAN's memory or reasoning policy. Provider price may change. [OpenRouter free model limits](https://openrouter.ai/pricing) include **50 requests per day before credits** and **1,000 after $10 purchased credits**, with 20 per minute; failed requests count. Our previous Nemotron web research retrieved source pages but failed on its free daily quota.

The existing adapter defaults to **free Nemotron**. The only optional paid allowlist entry is `qwen/qwen3.5-flash-02-23`. To enable that paid provider a user must explicitly set all three:

```powershell
$env:BEAN_REASONING_PROVIDER = "openrouter"
$env:BEAN_OPENROUTER_MODEL = "qwen/qwen3.5-flash-02-23"
$env:BEAN_OPENROUTER_PAID_ENABLED = "1"
$env:BEAN_OPENROUTER_PAID_CALL_LIMIT = "10"
# OPENROUTER_API_KEY is separately required for real requests.
```

No connection, account purchase, payment method, or charges have been initiated by the repository change. The paid adapter caps output at 512 tokens and the request at 10,000 characters, and stops at the configured **per-Python-instance** request limit. This is **not a durable dollar budget across processes or machines**; use OpenRouter's account/API-key spending controls for an account-wide limit. No automatic fallback to paid inference is allowed. Provider rate estimates are returned when token usage is supplied, not represented as actual bills.

## What BEAN now does without an LLM

`bean/learning/local_reasoner.py` introduces a small transparent **hypothesis → test → preserve → apply** loop on a strict, finite rule grammar:

1. Parse structured tags or numeric readings into a typed problem.
2. Propose multiple plausible procedures (sort by numeric value vs letter, median/minimum/maximum, etc.).
3. Falsify those procedures against at least **three independent development questions with expected answers**. If no unique procedure survives, abstain and do not store a fake conclusion.
4. Preserve the unique procedure, training question/answer fingerprints and input provenance in the **same SHA-verified ExperienceBank journal**, not a new memory service.
5. Parse and solve **new problems in the same grammar/domain** without touching a network or model, including after a process restart. Retain source-linked inference receipts and an explicit trace. The solution is **not** labeled externally verified.
6. Accept feedback on the native inference through the existing Core feedback command.

This is deliberately **symbolic/algorithmic reasoning**, not a pretrained language model or a generic natural-language inference system. It only solves the defined rule families, and unknown tasks are explicitly declined rather than guessed.

### Core commands

- `reasoning_learn_local` — development examples → unambiguous rule or abstention.
- `reasoning_local` — solve from BEAN's own retained rule; report trace and provenance.
- `reasoning_auto` — first try local, then **only if the caller sets `allow_provider=true`** call the existing measured-strategy external reasoning path. With the default `allow_provider=false`, never spend model tokens. The existing counsel/judgment and experienced strategy selection remain intact.

Example:

```python
from bean.learning.reasoning_service import NativeReasoningService

bean = NativeReasoningService("bean-reasoning.sqlite3")
try:
    print(bean.learn_local(
        domain="routing", task_ref="training-1",
        evidence_refs=["training:source-1"],
        examples=[
            {"question":"ORCHID-7 tags A3 B9 C5","answer":"BCA"},
            {"question":"ORCHID-7 tags X7 Q1 D5","answer":"XDQ"},
            {"question":"ORCHID-7 tags K2 L8 M4","answer":"LMK"},
        ]))
    print(bean.reason_auto(domain="routing", task_ref="heldout-1",
                           query="ORCHID-7 tags R7 C9 F2"))
    # Expected: locally_solved, answer CRF, external_cost_usd 0.
finally:
    bean.close()
```

## What testing actually establishes

Offline Windows/Ubuntu tests require: cold-start abstention; distinct unseen examples after restart; a second numerical family; contradictory/ambiguous teaching refusal; source receipt and feedback; NO network/model when BEAN can solve locally; NO paid model unless environment and per-instance call limit explicitly permit it.

Claims not supported: human-level or general language reasoning, semantically understanding arbitrary PDFs, independently authenticating host feedback, learned neural weights, quantitative trading profitability. More rule families can be added only with new test evidence; external providers stay optional counsel, not the reasoning owner.

## Next measured science

Combine this local-first path with BEAN's public-source research. Feed genuinely distinct, checked examples into the local induction engine when their structure fits; use low-cost counsel only for tasks that native rules and established expert evidence cannot settle. Evaluate cold versus local versus provider at identical question/answer pairs, with holdout inputs never used to pick or rewrite the rule. Preserve all mistakes in the same Core journal.
