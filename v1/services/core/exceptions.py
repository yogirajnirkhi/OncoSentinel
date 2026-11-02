"""
OncoSentinel v2.0 — Domain Exceptions and Safety Errors
Satisfies: FR-02, FR-04, FR-08, FR-30, NFR-01, NFR-09, NFR-10
"""
from __future__ import annotations


class OncoSentinelError(Exception):
    """Base exception for all OncoSentinel errors."""
    pass


class QualityCheckError(OncoSentinelError):
    """Raised when input fails minimum image or document quality gate."""
    def __init__(self, message: str, score: float, flags: list[str] | None = None):
        super().__init__(message)
        self.score = score
        self.flags = flags or []


class ModalityMismatchError(OncoSentinelError):
    """Raised when requested category does not support the given input modality."""
    def __init__(self, category: str, modality: str, supported: list[str]):
        super().__init__(
            f"Modality '{modality}' is not supported for category '{category}'. "
            f"Supported modalities: {supported}"
        )
        self.category = category
        self.modality = modality
        self.supported = supported


class CancerRelevanceError(OncoSentinelError):
    """Raised when request relevance score is below safety threshold (0.55)."""
    def __init__(self, score: float, threshold: float = 0.55):
        super().__init__(
            f"Input cancer relevance score {score:.3f} is below minimum threshold {threshold:.3f}. "
            "Input routed to safe-fail / off-topic handling."
        )
        self.score = score
        self.threshold = threshold


class PhaseNotAvailableError(OncoSentinelError):
    """Raised when category head is not yet enabled in current platform phase."""
    def __init__(self, category: str, required_phase: int, current_phase: int):
        super().__init__(
            f"Category '{category}' is scheduled for Phase {required_phase}, but platform is currently at Phase {current_phase}."
        )
        self.category = category
        self.required_phase = required_phase
        self.current_phase = current_phase


class UncertaintyAbstention(OncoSentinelError):
    """Raised when predictive or OOD uncertainty exceeds thresholds, requiring safe abstention."""
    def __init__(self, message: str, decision: str, uncertainty_vector: dict):
        super().__init__(message)
        self.decision = decision
        self.uncertainty_vector = uncertainty_vector


class NoGroundedAnswerError(OncoSentinelError):
    """Raised when RAG or LLM reasoning cannot ground an answer in clinical evidence."""
    def __init__(self, query: str, coverage_score: float):
        super().__init__(
            f"NO_GROUNDED_ANSWER: Evidence coverage {coverage_score:.3f} insufficient to formulate a verified clinical response."
        )
        self.query = query
        self.coverage_score = coverage_score


class TrainingDataLeakageError(OncoSentinelError):
    """CRITICAL: Raised when clinical outcome or prospective evaluation data is accessed by training pipeline."""
    def __init__(self, resource: str):
        super().__init__(
            f"CRITICAL SAFETY VIOLATION: Clinical outcome data '{resource}' is strictly partitioned and must NEVER be used for model training (NFR-10)."
        )
        self.resource = resource


class ImmutabilityViolationError(OncoSentinelError):
    """CRITICAL: Raised when attempting to mutate append-only timeline or insert-only audit record."""
    def __init__(self, entity: str):
        super().__init__(
            f"CRITICAL INTEGRITY VIOLATION: Attempted update/delete on immutable table '{entity}'."
        )
        self.entity = entity


class FairnessGateFailedError(OncoSentinelError):
    """Raised when a candidate model version fails subgroup fairness or disparity gates."""
    def __init__(self, model_id: str, disparities: dict):
        super().__init__(
            f"Fairness gate failed for model '{model_id}'. Unacceptable subgroup disparities detected: {disparities}"
        )
        self.model_id = model_id
        self.disparities = disparities
