"""Brain 0.11 reasoning engine."""

import json

from .context_builder import build_reasoning_context
from .mock_llm import MockLLMAdapter
from .openai_provider import OpenAIProvider
from .ollama_provider import OllamaProvider
from .openrouter_provider import OpenRouterProvider
from .prompt_builder import build_prompt, build_ollama_prompt
from .proposal_filter import all_passed, filter_proposal
from .proposal_store import create_filter_result, create_proposal, create_request, create_response
from .response_parser import parse_response
from .schema import init_reasoning_schema


def adapter_from_name(name: str | None):
    if name == "openai":
        return OpenAIProvider()
    if name == "ollama":
        return OllamaProvider()
    if name == "openrouter":
        return OpenRouterProvider()
    if name in (None, "mock"):
        return MockLLMAdapter()
    raise ValueError("Unknown BEAN reasoning provider: " + str(name))


class ReasoningEngine:
    def __init__(self, conn=None, adapter=None):
        self.conn = init_reasoning_schema(conn)
        self.adapter = adapter

    def run(self, session_uuid: str, request_type: str = "reflection", source_event_id: int | None = None, adapter_name: str = "mock", model_name: str | None = None) -> dict:
        packet = build_reasoning_context(session_uuid, source_event_id, request_type, self.conn)
        adapter = self.adapter or adapter_from_name(adapter_name)
        prompt = (build_ollama_prompt(packet["context"], request_type)
                  if adapter.adapter_name == "ollama"
                  else build_prompt(packet["context"], request_type))
        request_id = create_request(session_uuid, packet["packet_id"], request_type, prompt, adapter.adapter_name, model_name or adapter.model_name, self.conn)
        completion = adapter.complete(prompt, packet["context"])
        raw = completion.get("raw_text") if completion.get("ok") else '{"summary":"provider unavailable","risk_flags":["provider_unavailable"],"confidence":0.0}'
        parsed = parse_response(raw)
        # A syntactically valid JSON object can still violate the provider's
        # contract. Treat schema omissions/malformed fields as untrusted.
        if (adapter.adapter_name == "ollama" and completion.get("ok")
                and parsed.get("parse_success")):
            required = ("summary", "observations", "interpretations", "assumptions",
                        "uncertainties", "evidence_refs", "candidate_steps",
                        "risk_flags", "confidence")
            shape_ok = (
                isinstance(parsed.get("summary"), str)
                and bool(parsed["summary"].strip())
                and all(isinstance(parsed.get(key), list)
                        and all(isinstance(v, str) for v in parsed[key])
                        for key in required[1:8])
                and isinstance(parsed.get("confidence"), (int, float))
            )
            if not shape_ok or not all(key in json.loads(raw) for key in required):
                parsed["parse_success"] = False
                parsed["parse_error"] = "Ollama response did not match BEAN's required schema"
        if not parsed.get("parse_success"):
            # Keep the unmodified raw_text in reasoning_responses as evidence.
            parsed["summary"] = "Structured response validation failed"
            parsed["confidence"] = 0.0
            parsed["risk_flags"] = ["parse_failed"]
        valid = bool(completion.get("ok")) and bool(parsed.get("parse_success"))
        response_id = create_response(request_id, raw, parsed, self.conn)
        proposal_id = create_proposal(session_uuid, request_id, response_id, parsed, self.conn)
        filters = filter_proposal(parsed)
        if not valid:
            filters.append({"filter_name": "structured_response",
                            "passed": False, "reasons": [
                                "provider unavailable or structured response invalid"
                            ]})
        for result in filters:
            create_filter_result(proposal_id, result, self.conn)
        return {"success": True, "structured_response_valid": valid,
                "proposal_id": proposal_id, "request_id": request_id,
                "response_id": response_id, "filter_passed": all_passed(filters),
                "requires_supervisor_review": True,
                "motion_command_generated": False, "memory_written": False,
                "filters": filters}
