"""Brain 0.9 Wisdom Module."""

from .schema import init_wisdom_schema, PRESSURE_DIMENSIONS, FORBIDDEN_EMOTION_PHRASES
from .trigger_engine import TriggerMatch, match_triggers
from .activation_engine import WisdomActivationEngine
from .meaning_engine import build_meaning_frame
from .pressure_engine import compute_pressure_delta
from .repair_engine import record_repair_attempt
from .loop_detector import update_loop_signature, list_loop_signatures
from .maintenance import run_wisdom_maintenance
