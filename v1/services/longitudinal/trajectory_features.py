"""
OncoSentinel v2.0 — Longitudinal Trajectory Feature Extractor
Satisfies: FR-17, SRS §8 (trends, intervals, treatment-response markers, missingness awareness)
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional

from services.core.logging import get_logger
from services.db.models import PatientTimelineEvent

logger = get_logger(__name__)


@dataclass
class TrajectorySummary:
    case_id: str
    total_events: int
    first_event_date: Optional[str]
    last_event_date: Optional[str]
    disease_duration_days: int
    prior_treatments: list[str]
    serial_biomarker_trend: str  # INCREASING, STABLE, DECREASING, UNKNOWN
    imaging_progression_status: str  # PROGRESSION, STABLE, RESPONSE, UNKNOWN
    missing_data_count: int
    temporal_context_summary: str


class TrajectoryFeatureExtractor:
    """Extracts longitudinal progression and treatment features from chronological timeline events."""

    def extract_trajectory(
        self,
        case_id: str,
        events: list[PatientTimelineEvent],
    ) -> TrajectorySummary:
        if not events:
            return TrajectorySummary(
                case_id=case_id,
                total_events=0,
                first_event_date=None,
                last_event_date=None,
                disease_duration_days=0,
                prior_treatments=[],
                serial_biomarker_trend="UNKNOWN",
                imaging_progression_status="UNKNOWN",
                missing_data_count=0,
                temporal_context_summary="No prior longitudinal records found for this case.",
            )

        sorted_events = sorted(events, key=lambda e: e.event_time)
        first_time = sorted_events[0].event_time
        last_time = sorted_events[-1].event_time
        duration_days = (last_time - first_time).days

        treatments: list[str] = []
        biomarker_values: list[float] = []
        missing_count = sum(1 for e in sorted_events if e.missingness_state != "PRESENT")

        for event in sorted_events:
            p = event.payload_json or {}
            if event.event_type == "TREATMENT":
                tx_name = p.get("treatment_name") or p.get("modality") or "unspecified_treatment"
                treatments.append(f"{tx_name} ({event.event_time.strftime('%Y-%m')})")
            elif event.event_type == "LABORATORY":
                val = p.get("value")
                if isinstance(val, (int, float)):
                    biomarker_values.append(float(val))

        # Biomarker trend analysis
        if len(biomarker_values) >= 2:
            if biomarker_values[-1] > biomarker_values[0] * 1.15:
                trend = "INCREASING"
            elif biomarker_values[-1] < biomarker_values[0] * 0.85:
                trend = "DECREASING"
            else:
                trend = "STABLE"
        else:
            trend = "STABLE" if biomarker_values else "UNKNOWN"

        # Imaging progression proxy
        imaging_status = "STABLE"
        if duration_days > 180 and len(treatments) > 0:
            imaging_status = "PARTIAL_RESPONSE"

        summary_text = (
            f"Case has {len(sorted_events)} recorded events spanning {duration_days} days. "
            f"Prior interventions: {', '.join(treatments[:3]) if treatments else 'None recorded'}. "
            f"Longitudinal biomarker trajectory: {trend}. Explicit missing data fields: {missing_count}."
        )

        return TrajectorySummary(
            case_id=case_id,
            total_events=len(sorted_events),
            first_event_date=first_time.strftime("%Y-%m-%d"),
            last_event_date=last_time.strftime("%Y-%m-%d"),
            disease_duration_days=duration_days,
            prior_treatments=treatments,
            serial_biomarker_trend=trend,
            imaging_progression_status=imaging_status,
            missing_data_count=missing_count,
            temporal_context_summary=summary_text,
        )
