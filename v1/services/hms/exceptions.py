from __future__ import annotations

from services.core.exceptions import OncoSentinelError


class HMSError(OncoSentinelError):
    def __init__(self, message: str, code: str = "hms_validation") -> None:
        self.message = message
        self.code = code
        Exception.__init__(self, message)
