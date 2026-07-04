"""Claim vocabularies for Brain 0.13."""

VALID_CLAIM_TYPES = {"observation", "memory", "inference", "hypothesis", "speculation", "counterfactual", "prediction", "unknown"}
VALID_EVIDENCE_LEVELS = {"observed", "strongly_supported", "supported", "weakly_supported", "speculative", "hypothetical", "unknown", "contradicted"}
VALID_ACTION_PERMISSIONS = {"thought_only", "may_ask_question", "may_observe", "may_recommend", "requires_supervisor_review", "forbidden_for_action"}
VALID_HYPOTHESIS_STATUSES = {"open", "strengthened", "weakened", "contradicted", "resolved", "superseded", "archived"}
NON_FACTUAL_CLAIM_TYPES = {"inference", "hypothesis", "speculation", "counterfactual", "prediction", "unknown"}
DEFAULT_FORBIDDEN_CLAIM_TYPES = {"hypothesis", "speculation", "counterfactual", "prediction", "unknown"}
GROUNDED_EVIDENCE_LEVELS = {"observed", "strongly_supported", "supported"}
CERTAINTY_PHRASES = ["definitely", "certainly", "proven", "guaranteed"]
