"""
OncoSentinel v2.0 — Audit & Provenance Service
Satisfies: FR-29, NFR-06 (INSERT-ONLY audit trail, end-to-end decision provenance)
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from services.core.logging import get_logger
from services.db.models import AuditEvent

logger = get_logger(__name__)


class AuditService:
    """Manages immutable audit logging for all user requests, inferences, and clinical actions."""

    @staticmethod
    def record_audit_sync(
        db: Session,
        request_id: str,
        actor_id: str,
        actor_role: str,
        action: str,
        model_id: Optional[str] = None,
        model_version: Optional[str] = None,
        evidence_ids: Optional[list[str]] = None,
        explanation_id: Optional[str] = None,
        uncertainty_record_id: Optional[str] = None,
        clinician_action: Optional[str] = None,
        outcome_id: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
        trace_id: Optional[str] = None,
    ) -> AuditEvent:
        event = AuditEvent(
            id=str(uuid.uuid4()),
            request_id=request_id,
            actor_id=actor_id,
            actor_role=actor_role,
            action=action,
            model_id=model_id,
            model_version=model_version,
            evidence_ids=evidence_ids or [],
            explanation_id=explanation_id,
            uncertainty_record_id=uncertainty_record_id,
            clinician_action=clinician_action,
            outcome_id=outcome_id,
            metadata_json=metadata or {},
            service_name="oncosentinel_v2",
            trace_id=trace_id or request_id,
        )
        db.add(event)
        db.flush()
        logger.info(
            "audit_event_recorded",
            request_id=request_id,
            action=action,
            actor_role=actor_role,
        )
        return event

    @staticmethod
    async def record_audit_async(
        db: AsyncSession,
        request_id: str,
        actor_id: str,
        actor_role: str,
        action: str,
        model_id: Optional[str] = None,
        model_version: Optional[str] = None,
        evidence_ids: Optional[list[str]] = None,
        explanation_id: Optional[str] = None,
        uncertainty_record_id: Optional[str] = None,
        clinician_action: Optional[str] = None,
        outcome_id: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
        trace_id: Optional[str] = None,
    ) -> AuditEvent:
        event = AuditEvent(
            id=str(uuid.uuid4()),
            request_id=request_id,
            actor_id=actor_id,
            actor_role=actor_role,
            action=action,
            model_id=model_id,
            model_version=model_version,
            evidence_ids=evidence_ids or [],
            explanation_id=explanation_id,
            uncertainty_record_id=uncertainty_record_id,
            clinician_action=clinician_action,
            outcome_id=outcome_id,
            metadata_json=metadata or {},
            service_name="oncosentinel_v2",
            trace_id=trace_id or request_id,
        )
        db.add(event)
        await db.flush()
        return event

    @staticmethod
    def get_audit_trail_sync(db: Session, request_id: str) -> list[AuditEvent]:
        stmt = (
            select(AuditEvent)
            .where(AuditEvent.request_id == request_id)
            .order_by(AuditEvent.timestamp.asc())
        )
        return list(db.scalars(stmt).all())

    @staticmethod
    async def get_audit_trail_async(db: AsyncSession, request_id: str) -> list[AuditEvent]:
        stmt = (
            select(AuditEvent)
            .where(AuditEvent.request_id == request_id)
            .order_by(AuditEvent.timestamp.asc())
        )
        res = await db.execute(stmt)
        return list(res.scalars().all())

    @staticmethod
    async def query_audit_async(
        db: AsyncSession,
        actor_id: Optional[str] = None,
        actor_role: Optional[str] = None,
        patient_mrn: Optional[str] = None,
        request_id: Optional[str] = None,
        limit: int = 100,
    ) -> list[AuditEvent]:
        stmt = select(AuditEvent)
        if request_id:
            stmt = stmt.where(AuditEvent.request_id == request_id)
        if actor_id:
            stmt = stmt.where(AuditEvent.actor_id == actor_id)
        if actor_role:
            stmt = stmt.where(AuditEvent.actor_role == actor_role)
        stmt = stmt.order_by(AuditEvent.timestamp.desc()).limit(limit)
        res = await db.execute(stmt)
        events = list(res.scalars().all())
        if patient_mrn:
            events = [
                e for e in events
                if (e.metadata_json and e.metadata_json.get("patient_mrn") == patient_mrn)
                or (e.metadata_json and patient_mrn.lower() in str(e.metadata_json).lower())
            ]
        return events
