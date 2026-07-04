from .hypothesis import HypothesisRecord
from .hypothesis_store import init_speculation_schema, persist_hypothesis, get_hypothesis, list_open_hypotheses, update_hypothesis_status, record_review
from .speculative_engine import SpeculativeEngine


def init_speculation(conn=None):
    init_speculation_schema(conn)
    return SpeculativeEngine(conn)
