"""Errors raised by the client.

Every error carries a stable ``kind`` so the skill can branch on JSON output
without parsing prose.
"""


class CcnuError(Exception):
    kind = "error"

    def __init__(self, message):
        super().__init__(message)
        self.message = str(message)

    def to_dict(self):
        return {"kind": self.kind, "message": self.message}


class NotConfigured(CcnuError):
    kind = "not_configured"


class InvalidCredentials(CcnuError):
    kind = "invalid_credentials"


class LoginFailed(CcnuError):
    kind = "login_failed"


class SessionExpired(CcnuError):
    kind = "session_expired"


class UpstreamBlocked(CcnuError):
    """The reservation site refuses traffic, e.g. its overnight closure."""

    kind = "upstream_blocked"


class InvalidWindow(CcnuError):
    kind = "invalid_window"


class NetworkError(CcnuError):
    kind = "network_error"


class ProtocolError(CcnuError):
    kind = "protocol_error"


class UsageError(CcnuError):
    kind = "usage_error"


class NoReservationId(CcnuError):
    kind = "no_reservation_id"


class ApiError(CcnuError):
    kind = "api_error"

    def __init__(self, code, message):
        super().__init__(message)
        self.code = code

    def to_dict(self):
        payload = super().to_dict()
        payload["code"] = self.code
        return payload
