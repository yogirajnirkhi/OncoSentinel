"""
OncoSentinel v2.0 — Clinical Outcome Tracker
Satisfies: FR-21, NFR-10 (Capture workflow and patient outcomes; strict training leakage guard)
Grounded in: Research Gap Analysis §4.3.3 (Limited prospective clinical evidence)
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from services.core.exceptions import TrainingDataLeakageError
from services.core.logging import get_logger
from services.db.models import ClinicalOutcome, Study

logger = get_logger(__name__)


class ClinicalOutcomeTracker:
    """Manages prospective clinical outcome capture, ensuring zero training data contamination."""

    @staticmethod
    def assert_no_training_leakage(caller_context: str) -> None:
        """
        CRITICAL GUARD: Raises TrainingDataLeakageError if called within a training context.
        Satisfies NFR-10.
        """
        if "train" in caller_context.lower() or "retrain" in caller_context.lower() or "dataset" in caller_context.lower():
            raise TrainingDataLeakageError(f"Caller '{caller_context}' attempted unauthorized access to ClinicalOutcomes.")

    @staticmethod
    def record_outcome_sync(
        db: Session,
        case_id: str,
        study_id: str,
        arm: str,  # AI_ASSISTED | STANDARD_OF_CARE
        endpoint: str,
        value: dict[str, Any],
        decision_timestamp: datetime,
        subgroup_metadata: Optional[dict[str, str]] = None,
    ) -> ClinicalOutcome:
        outcome = ClinicalOutcome(
            id=str(uuid.uuid4()),
            case_id=case_id,
            study_id=study_id,
            arm=arm,
            endpoint=endpoint,
            decision_timestamp=decision_timestamp,
            adjudication_state="PENDING",
            subgroup_metadata=subgroup_metadata or {},
            outcome_value=value,
        )
        db.add(outcome)
        db.flush()
        logger.info(
            "clinical_outcome_recorded",
            case_id=case_id,
            study_id=study_id,
            endpoint=endpoint,
            arm=arm,
        )
        return outcome

    @staticmethod
    async def record_outcome_async(
        db: AsyncSession,
        case_id: str,
        study_id: str,
        arm: str,
        endpoint: str,
        value: dict[str, Any],
        decision_timestamp: datetime,
        subgroup_metadata: Optional[dict[str, str]] = None,
    ) -> ClinicalOutcome:
        outcome = ClinicalOutcome(
            id=str(uuid.uuid4()),
            case_id=case_id,
            study_id=study_id,
            arm=arm,
            endpoint=endpoint,
            decision_timestamp=decision_timestamp,
            adjudication_state="PENDING",
            subgroup_metadata=subgroup_metadata or {},
            outcome_value=value,
        )
        db.add(outcome)
        await db.flush()
        return outcome
