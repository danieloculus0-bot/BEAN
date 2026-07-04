"""Persistence helpers for Brain 0.11 reasoning."""

import json
import uuid
from .schema import init_reasoning_schema


def create_request(session_uuid, packet_id, request_type, prompt_text, adapter_name, model_name=None, conn=None):
    conn = init_reasoning_schema(conn)
    rid = f"req_{uuid.uuid4().hex[:12]}"
    conn.execute("INSERT INTO reasoning_requests (request_id, session_uuid, packet_id, request_type, prompt_text, model_name, adapter_name) VALUES (?, ?, ?, ?, ?, ?, ?)", (rid, session_uuid, packet_id, request_type, prompt_text, model_name, adapter_name))
    conn.commit()
    return rid


def create_response(request_id, raw_text, parsed, conn=None):
    conn = init_reasoning_schema(conn)
    resp_id = f"resp_{uuid.uuid4().hex[:12]}"
    conn.execute("INSERT INTO reasoning_responses (response_id, request_id, raw_text, parsed_json, parse_success) VALUES (?, ?, ?, ?, ?)", (resp_id, request_id, raw_text, json.dumps(parsed), 1 if parsed.get("parse_success") else 0))
    conn.commit()
    return resp_id


def create_proposal(session_uuid, request_id, response_id, parsed, conn=None):
    conn = init_reasoning_schema(conn)
    pid = f"proposal_{uuid.uuid4().hex[:12]}"
    conn.execute("INSERT INTO reasoning_proposals (proposal_id, request_id, response_id, session_uuid, proposal_type, summary, observations_json, interpretations_json, assumptions_json, uncertainties_json, evidence_refs_json, candidate_steps_json, risk_flags_json, referenced_hypothesis_ids_json, confidence, status) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending_review')", (pid, request_id, response_id, session_uuid, "reasoning", parsed.get("summary", ""), json.dumps(parsed.get("observations", [])), json.dumps(parsed.get("interpretations", [])), json.dumps(parsed.get("assumptions", [])), json.dumps(parsed.get("uncertainties", [])), json.dumps(parsed.get("evidence_refs", [])), json.dumps(parsed.get("candidate_steps", [])), json.dumps(parsed.get("risk_flags", [])), json.dumps(parsed.get("referenced_hypothesis_ids", [])), float(parsed.get("confidence", 0.5))))
    conn.commit()
    return pid


def create_filter_result(proposal_id, result, conn=None):
    conn = init_reasoning_schema(conn)
    fid = f"filter_{uuid.uuid4().hex[:12]}"
    conn.execute("INSERT INTO reasoning_filter_results (filter_id, proposal_id, filter_name, passed, severity, reasons_json) VALUES (?, ?, ?, ?, ?, ?)", (fid, proposal_id, result.get("filter_name", "unknown"), 1 if result.get("passed") else 0, result.get("severity", "info"), json.dumps(result.get("reasons", []))))
    conn.commit()
    return fid


def get_proposal(proposal_id, conn=None):
    conn = init_reasoning_schema(conn)
    row = conn.execute("SELECT * FROM reasoning_proposals WHERE proposal_id=?", (proposal_id,)).fetchone()
    return dict(row) if row else None
