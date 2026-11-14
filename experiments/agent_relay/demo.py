"""Two independent authenticated agent clients exchange synthetic signals."""
from __future__ import annotations

import json
import threading

from .agent import local_preference_review
from .client import AgentClient
from .protocol import message
from .relay import Relay, make_server

TOKENS = {"agentA": "demo-synthetic-capability-alpha-2026",
          "agentB": "demo-synthetic-capability-bravo-2026"}


def run_demo():
    relay = Relay(TOKENS)
    server = make_server(relay)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        address = "http://127.0.0.1:" + str(server.server_port)
        left = AgentClient(address, TOKENS["agentA"])
        right = AgentClient(address, TOKENS["agentB"])
        left.send(message(message_id="m001", session_id="demo001",
                          sender="agentA", recipient="agentB", kind="probe",
                          topic="hobbies", detail="creative_making", signal="interested"))
        received = right.inbox()
        assert len(received) == 1
        right.send(message(message_id="m002", session_id="demo001",
                           sender="agentB", recipient="agentA", kind="reply",
                           topic="hobbies", detail="creative_making", signal="compatible"))
        response = left.inbox()
        assert len(response) == 1 and response[0]["signal"] == "compatible"
        # The numerical preference is NEVER placed in an outbound envelope.
        local_only = local_preference_review(
            requested_minimum=160, candidate_value=150, flexible=True)
        assert local_only["decision"] == "ask_local"
        return {"schema": "bean.agent_relay.demo.v1",
                "scope": "synthetic_agents_local_http_no_human_profiles",
                "delivered_messages": 2,
                "anonymous_transport": True,
                "local_preference_review": local_only["decision"],
                "real_model_inference": False,
                "predictive_match_validation": False}
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)


if __name__ == "__main__":
    print(json.dumps(run_demo(), sort_keys=True))
