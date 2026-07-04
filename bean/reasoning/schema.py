"""Brain 0.11 reasoning schema."""

def init_reasoning_schema(conn=None):
    if conn is None:
        from ..memory.store import get_store
        conn = get_store()._conn()
    conn.execute("CREATE TABLE IF NOT EXISTS reasoning_context_packets (id INTEGER PRIMARY KEY AUTOINCREMENT, packet_id TEXT NOT NULL UNIQUE, session_uuid TEXT NOT NULL, context_json TEXT NOT NULL DEFAULT '{}', created_at TEXT NOT NULL DEFAULT (datetime('now','utc')))")
    conn.execute("CREATE TABLE IF NOT EXISTS reasoning_requests (id INTEGER PRIMARY KEY AUTOINCREMENT, request_id TEXT NOT NULL UNIQUE, session_uuid TEXT NOT NULL, packet_id TEXT NOT NULL, request_type TEXT NOT NULL, prompt_text TEXT NOT NULL, model_name TEXT, adapter_name TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'created', created_at TEXT NOT NULL DEFAULT (datetime('now','utc')))")
    conn.execute("CREATE TABLE IF NOT EXISTS reasoning_responses (id INTEGER PRIMARY KEY AUTOINCREMENT, response_id TEXT NOT NULL UNIQUE, request_id TEXT NOT NULL, raw_text TEXT NOT NULL, parsed_json TEXT NOT NULL DEFAULT '{}', parse_success INTEGER NOT NULL DEFAULT 0, created_at TEXT NOT NULL DEFAULT (datetime('now','utc')))")
    conn.execute("CREATE TABLE IF NOT EXISTS reasoning_proposals (id INTEGER PRIMARY KEY AUTOINCREMENT, proposal_id TEXT NOT NULL UNIQUE, request_id TEXT NOT NULL, response_id TEXT, session_uuid TEXT NOT NULL, proposal_type TEXT NOT NULL, summary TEXT NOT NULL, observations_json TEXT NOT NULL DEFAULT '[]', interpretations_json TEXT NOT NULL DEFAULT '[]', assumptions_json TEXT NOT NULL DEFAULT '[]', uncertainties_json TEXT NOT NULL DEFAULT '[]', evidence_refs_json TEXT NOT NULL DEFAULT '[]', candidate_steps_json TEXT NOT NULL DEFAULT '[]', risk_flags_json TEXT NOT NULL DEFAULT '[]', referenced_hypothesis_ids_json TEXT NOT NULL DEFAULT '[]', confidence REAL NOT NULL DEFAULT 0.5, status TEXT NOT NULL DEFAULT 'pending_review', created_at TEXT NOT NULL DEFAULT (datetime('now','utc')))")
    conn.execute("CREATE TABLE IF NOT EXISTS reasoning_filter_results (id INTEGER PRIMARY KEY AUTOINCREMENT, filter_id TEXT NOT NULL UNIQUE, proposal_id TEXT NOT NULL, filter_name TEXT NOT NULL, passed INTEGER NOT NULL, severity TEXT NOT NULL DEFAULT 'info', reasons_json TEXT NOT NULL DEFAULT '[]', created_at TEXT NOT NULL DEFAULT (datetime('now','utc')))")
    conn.commit()
    return conn
