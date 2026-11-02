"""
OncoSentinel v2.0 — Longitudinal Timeline Manager
Satisfies: FR-16, NFR-09 (Append-only time-stamped event model; immutability; explicit missingness)
Grounded in: Architecture v2.0 §6 (never overwrite historical facts; append time-stamped events with provenance)
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from services.core.exceptions import ImmutabilityViolationError
from services.core.logging import get_logger
from services.db.models import PatientTimelineEvent

logger = get_logger(__name__)

EVENT_DIAGNOSIS = "DIAGNOSIS"
EVENT_IMAGING = "IMAGING"
EVENT_PATHOLOGY = "PATHOLOGY"
EVENT_LABORATORY = "LABORATORY"
EVENT_TREATMENT = "TREATMENT"
EVENT_RESPONSE = "RESPONSE"
EVENT_OUTCOME = "OUTCOME"

MISSINGNESS_PRESENT = "PRESENT"
MISSINGNESS_MISSING = "MISSING"
MISSINGNESS_IMPUTED = "IMPUTED"
MISSINGNESS_UNKNOWN = "UNKNOWN"


class TimelineManager:
    """Manages the append-only longitudinal event timeline for a case."""

    @staticmethod
    def append_event_sync(
        db: Session,
        case_id: str,
        event_time: datetime,
        event_type: str,
        source: str,
        payload: dict[str, Any],
        provenance: Optional[dict[str, Any]] = None,
        confidence: Optional[float] = None,
        missingness_state: str = MISSINGNESS_PRESENT,
        references_event_id: Optional[str] = None,
    ) -> PatientTimelineEvent:
        """
        Appends an event to the patient timeline.
        Strictly append-only: no updates or deletes permitted.
        """
        valid_states = {
            MISSINGNESS_PRESENT,
            MISSINGNESS_MISSING,
            MISSINGNESS_IMPUTED,
            MISSINGNESS_UNKNOWN,
        }
        if missingness_state not in valid_states:
            raise ValueError(f"Invalid missingness_state '{missingness_state}'. Must be one of {valid_states}")

        event = PatientTimelineEvent(
            id=str(uuid.uuid4()),
            case_id=case_id,
            event_time=event_time,
            event_type=event_type,
            source=source,
            provenance_json=provenance or {"app": "oncosentinel_v2", "actor": "system"},
            confidence=confidence,
            missingness_state=missingness_state,
            references_event_id=references_event_id,
            payload_json=payload,
        )
        db.add(event)
        db.flush()
        logger.info(
            "timeline_event_appended",
            case_id=case_id,
            event_id=event.id,
            event_type=event_type,
            event_time=event_time.isoformat(),
        )
        return event

    @staticmethod
    async def append_event_async(
        db: AsyncSession,
        case_id: str,
        event_time: datetime,
        event_type: str,
        source: str,
        payload: dict[str, Any],
        provenance: Optional[dict[str, Any]] = None,
        confidence: Optional[float] = None,
        missingness_state: str = MISSINGNESS_PRESENT,
        references_event_id: Optional[str] = None,
    ) -> PatientTimelineEvent:
        """Asynchronously appends an event to the patient timeline."""
        event = PatientTimelineEvent(
            id=str(uuid.uuid4()),
            case_id=case_id,
            event_time=event_time,
            event_type=event_type,
            source=source,
            provenance_json=provenance or {"app": "oncosentinel_v2", "actor": "system"},
            confidence=confidence,
            missingness_state=missingness_state,
            references_event_id=references_event_id,
            payload_json=payload,
        )
        db.add(event)
        await db.flush()
        return event

    @staticmethod
    def get_case_timeline_sync(db: Session, case_id: str) -> list[PatientTimelineEvent]:
        """Returns chronological list of timeline events for a case."""
        stmt = (
            select(PatientTimelineEvent)
            .where(PatientTimelineEvent.case_id == case_id)
            .order_by(PatientTimelineEvent.event_time.asc())
        )
        return list(db.scalars(stmt).all())

    @staticmethod
    async def get_case_timeline_async(db: AsyncSession, case_id: str) -> list[PatientTimelineEvent]:
        """Asynchronously returns chronological list of timeline events for a case."""
        stmt = (
            select(PatientTimelineEvent)
            .where(PatientTimelineEvent.case_id == case_id)
            .order_by(PatientTimelineEvent.event_time.asc())
        )
        res = await db.execute(stmt)
        return list(res.scalars().all())
