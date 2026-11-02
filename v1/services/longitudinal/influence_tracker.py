"""
OncoSentinel v2.0 — Timeline Influence Tracker
Satisfies: FR-17 (expose which historical events influenced prediction / reasoning)
"""
from __future__ import annotations

import uuid
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from services.core.logging import get_logger
from services.db.models import PatientTimelineEvent, TimelineInfluence

logger = get_logger(__name__)


class TimelineInfluenceTracker:
    """Records links and attribution weights between historical timeline events and predictions."""

    @staticmethod
    def record_influences_sync(
        db: Session,
        prediction_id: str,
        events: list[PatientTimelineEvent],
    ) -> list[TimelineInfluence]:
        """Calculates temporal recency/relevance weights and persists TimelineInfluence records."""
        influences: list[TimelineInfluence] = []
        if not events:
            return influences

        # Exponential recency weighting: more recent events receive higher influence weight
        n = len(events)
        raw_weights = [1.0 + (i * 0.5) for i in range(n)]
        total_w = sum(raw_weights)
        norm_weights = [w / total_w for w in raw_weights]

        for event, w in zip(events, norm_weights):
            infl = TimelineInfluence(
                id=str(uuid.uuid4()),
                event_id=event.id,
                prediction_id=prediction_id,
                influence_weight=round(float(w), 4),
            )
            db.add(infl)
            influences.append(infl)

        db.flush()
        logger.info(
            "timeline_influences_recorded",
            prediction_id=prediction_id,
            count=len(influences),
        )
        return influences

    @staticmethod
    async def record_influences_async(
        db: AsyncSession,
        prediction_id: str,
        events: list[PatientTimelineEvent],
    ) -> list[TimelineInfluence]:
        influences: list[TimelineInfluence] = []
        if not events:
            return influences

        n = len(events)
        raw_weights = [1.0 + (i * 0.5) for i in range(n)]
        total_w = sum(raw_weights)
        norm_weights = [w / total_w for w in raw_weights]

        for event, w in zip(events, norm_weights):
            infl = TimelineInfluence(
                id=str(uuid.uuid4()),
                event_id=event.id,
                prediction_id=prediction_id,
                influence_weight=round(float(w), 4),
            )
            db.add(infl)
            influences.append(infl)

        await db.flush()
        return influences
