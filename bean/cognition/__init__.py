"""BEAN cognition layer."""

from .significance import SignificanceScorer, SignificanceScore
from .significance_weights import SignificanceWeightManager, SignificanceWeights
from .surprise import SurpriseDetector, SurpriseRecord
from .preference import PreferenceEngine, PreferenceStore, Preference, PreferenceDirection
from .drive import DriveEvaluator, DriveState, DrivePriority
from .goal_state import GoalStateEngine, GoalProposal, ActionType, ApprovalRequired
from .consolidation import ConsolidationEngine, ConsolidationReport
from .possibility import PossibilityState, StateOption
from .state_collapse import StateCollapseManager
from .coherence import CoherenceEngine, CoherenceReport
from .entropy import EntropySource, EntropySourceType, EntropyReading
from .epistemic_guard import EpistemicGuard, EpistemicAudit, CandidateClaim, EpistemicVerdict
from .contradiction_court import ContradictionCourt, ClaimConflict, ClaimVerdict, ConflictType, CourtVerdict
from .falsification import FalsificationEngine, FalsificationRule, FalsificationResult, FalsificationType
