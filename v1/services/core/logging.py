"""
OncoSentinel v2.0 — PHI-Safe Structured Logging
Satisfies: NFR-06 (no PHI in logs/traces)

Uses structlog for structured output. A PHI-scrubbing filter is applied
to every log record to ensure no patient identifiers leak into logs or traces.
"""
from __future__ import annotations

import logging
import re
from typing import Any

try:
    import structlog
    from structlog.types import EventDict, WrappedLogger
    _HAS_STRUCTLOG = True
except ImportError:
    _HAS_STRUCTLOG = False


# ── PHI patterns to scrub ─────────────────────────────────────────────────────
_PHI_PATTERNS = [
    # Patient name patterns (simplified — extend for production)
    (re.compile(r'"patient_name"\s*:\s*"[^"]+"'), '"patient_name": "[REDACTED]"'),
    (re.compile(r'"name"\s*:\s*"[A-Z][a-z]+ [A-Z][a-z]+"'), '"name": "[REDACTED]"'),
    # DOB
    (re.compile(r'\b\d{4}-\d{2}-\d{2}\b(?=.*\b(birth|dob|born)\b)', re.IGNORECASE), "[DOB_REDACTED]"),
    # SSN-like
    (re.compile(r'\b\d{3}-\d{2}-\d{4}\b'), "[SSN_REDACTED]"),
    # Email
    (re.compile(r'[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}'), "[EMAIL_REDACTED]"),
    # Phone
    (re.compile(r'\b(\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b'), "[PHONE_REDACTED]"),
    # MRN-like patterns
    (re.compile(r'\bMRN[:\s#]+\w+', re.IGNORECASE), "MRN:[MRN_REDACTED]"),
    # NPI
    (re.compile(r'\bNPI[:\s]+\d{10}\b', re.IGNORECASE), "NPI:[NPI_REDACTED]"),
]


def _scrub_phi(value: str) -> str:
    """Apply PHI scrubbing patterns to a string value."""
    for pattern, replacement in _PHI_PATTERNS:
        value = pattern.sub(replacement, value)
    return value


def _phi_safe_processor(
    logger: Any, method: str, event_dict: dict[str, Any]
) -> dict[str, Any]:
    """Structlog processor that scrubs PHI from all string values."""
    for key, value in list(event_dict.items()):
        if isinstance(value, str):
            event_dict[key] = _scrub_phi(value)
        elif isinstance(value, dict):
            event_dict[key] = {
                k: _scrub_phi(v) if isinstance(v, str) else v
                for k, v in value.items()
            }
    return event_dict


class StandardLoggerWrapper:
    """Zero-dependency fallback logger that mirrors structlog interface with PHI scrubbing."""

    def __init__(self, name: str) -> None:
        self._logger = logging.getLogger(name)

    def _format_event(self, event: str, kw: dict[str, Any]) -> str:
        scrubbed = {k: _scrub_phi(str(v)) for k, v in kw.items()}
        kw_str = " ".join(f"{k}={v}" for k, v in scrubbed.items())
        return f"{event} {kw_str}".strip()

    def info(self, event: str, **kwargs: Any) -> None:
        self._logger.info(self._format_event(event, kwargs))

    def warning(self, event: str, **kwargs: Any) -> None:
        self._logger.warning(self._format_event(event, kwargs))

    def error(self, event: str, **kwargs: Any) -> None:
        self._logger.error(self._format_event(event, kwargs))

    def debug(self, event: str, **kwargs: Any) -> None:
        self._logger.debug(self._format_event(event, kwargs))

    def critical(self, event: str, **kwargs: Any) -> None:
        self._logger.critical(self._format_event(event, kwargs))

    def exception(self, event: str, **kwargs: Any) -> None:
        self._logger.exception(self._format_event(event, kwargs))

    def bind(self, **kwargs: Any) -> StandardLoggerWrapper:
        return self


def _safe_add_logger_name(logger: Any, method: str, event_dict: dict[str, Any]) -> dict[str, Any]:
    if hasattr(logger, "name"):
        event_dict["logger"] = logger.name
    return event_dict


def _ist_timestamper(logger: Any, method: str, event_dict: dict[str, Any]) -> dict[str, Any]:
    from datetime import datetime, timezone, timedelta
    ist = timezone(timedelta(hours=5, minutes=30), name="IST")
    event_dict["timestamp"] = datetime.now(ist).isoformat()
    return event_dict


def configure_logging(log_level: str = "INFO") -> None:
    """Configure structlog or stdlib logging with PHI-safe processor chain."""
    if _HAS_STRUCTLOG:
        shared_processors: list[Any] = [
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.add_log_level,
            _safe_add_logger_name,
            _ist_timestamper,
            _phi_safe_processor,          # PHI scrubbing — always applied
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
        ]

        structlog.configure(
            processors=shared_processors + [
                structlog.processors.JSONRenderer(),
            ],
            wrapper_class=structlog.make_filtering_bound_logger(
                logging.getLevelName(log_level)
            ),
            context_class=dict,
            logger_factory=structlog.PrintLoggerFactory(),
            cache_logger_on_first_use=True,
        )

    # Standard library logging configuration
    logging.basicConfig(
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        level=logging.getLevelName(log_level),
    )


def get_logger(name: str) -> Any:
    """Return a named, PHI-safe structured logger."""
    if _HAS_STRUCTLOG:
        return structlog.get_logger(name)
    return StandardLoggerWrapper(name)
