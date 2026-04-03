"""
Exceptions — Domain-specific HTTP exceptions for CalenMind AI.

## Traceability
Feature: F001 — Google OAuth Authentication, F002 — Multimodal Input Processing,
         F004 — Freemium Limits
Scenarios: SC001, SC002, SC003, SC004

## Business context
Centralises all HTTP error semantics so API layer handlers stay thin.
Each exception maps to a well-defined HTTP status code and error code
string that the bot API client can pattern-match on.
"""

from fastapi import HTTPException, status


class AuthNotConnectedException(HTTPException):
    """User has not completed Google OAuth flow."""

    def __init__(self) -> None:
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "AUTH_NOT_CONNECTED", "message": "Google account not connected."},
        )


class TokenDecryptionException(HTTPException):
    """Stored OAuth token could not be decrypted."""

    def __init__(self) -> None:
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "TOKEN_DECRYPT_FAILED", "message": "Failed to read stored credentials."},
        )


class FreemiumLimitExceededException(HTTPException):
    """User has reached the monthly free-tier sync limit (F004 — SC004)."""

    def __init__(self, limit: int) -> None:
        super().__init__(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail={
                "code": "FREEMIUM_LIMIT_EXCEEDED",
                "message": f"You have reached the {limit} free syncs for this month.",
            },
        )


class AIParsingException(HTTPException):
    """AI service failed to extract structured event data."""

    def __init__(self, reason: str = "") -> None:
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "AI_PARSING_FAILED", "message": f"Could not parse input: {reason}"},
        )


class CalendarSyncException(HTTPException):
    """Google Calendar API call failed."""

    def __init__(self, reason: str = "") -> None:
        super().__init__(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"code": "CALENDAR_SYNC_FAILED", "message": f"Calendar sync error: {reason}"},
        )
