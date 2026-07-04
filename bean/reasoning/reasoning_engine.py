"""Brain 0.11 reasoning engine."""

from .context_builder import build_reasoning_context
from .mock_llm import MockLLMAdapter
from .openai_provider import OpenAIProvider
from .prompt_builder import build_prompt
from .proposal_filter import all_passed, filter_proposal
from .proposal_store import create_filter_result, create_proposal, create_request, create_response
from .response_parser import parse_response
from .schema import init_reasoning_schema


def adapter_from_name(name: str | None):
    if name == "openai":
        return OpenAIProvider()
    return MockLLMAdapter()


class ReasoningEngine:
    def __init__(self, conn=None, adapter=None):
        self.conn = init_reasoning_schema(conn)
        self.adapter = adapter

    def run(self, session_uuid: str, request_type: str = "reflection", source_event_id: int | None = None, adapter_name: str = "mock", model_name: str | None = None) -> dict:
        packet = build_reasoning_context(session_uuid, source_event_id, request_type, self.conn)
        prompt = build_prompt(packet["context"], request_type)
        adapter = self.adapter or adapter_from_name(adapter_name)
        request_id = create_request(session_uuid, packet["packet_id"], request_type, prompt, adapter.adapter_name, model_name or adapter.model_name, self.conn)
        completion = adapter.complete(prompt, packet["context"])
        raw = completion.get("raw_text") if completion.get("ok") else '{"summary":"provider unavailable","risk_flags":["provider_unavailable"],"confidence":0.0}'
        parsed = parse_response(raw)
        response_id = create_response(request_id, raw, parsed, self.conn)
        proposal_id = create_proposal(session_uuid, request_id, response_id, parsed, self.conn)
        filters = filter_proposal(parsed)
        for result in filters:
            create_filter_result(proposal_id, result, self.conn)
        return {"success": True, "proposal_id": proposal_id, "request_id": request_id, "response_id": response_id, "filter_passed": all_passed(filters), "requires_supervisor_review": True, "motion_command_generated": False, "memory_written": False, "filters": filters}
