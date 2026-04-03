"""
BaseClient — Async httpx wrapper for all backend API calls.

## Traceability
Feature: F001, F002, F004 — All bot features
Scenarios: SC001, SC002, SC003, SC004

## Business context
Centralises HTTP session management (timeout, base URL, error mapping) so
concrete clients stay thin. Maps backend HTTP error codes to readable
Python exceptions the widget Code stages can catch and route.
"""

from typing import Any

import httpx

from bot.core.config import bot_settings


class BackendHTTPError(Exception):
    """Raised when the backend returns a non-2xx response."""

    def __init__(self, status_code: int, error_code: str, message: str) -> None:
        self.status_code = status_code
        self.error_code = error_code
        self.message = message
        super().__init__(f"[{status_code}] {error_code}: {message}")


class FreemiumLimitError(BackendHTTPError):
    """HTTP 402 — user has reached the monthly sync limit."""


class AuthNotConnectedError(BackendHTTPError):
    """HTTP 401 — user has not completed Google OAuth."""


class BaseClient:
    def __init__(self) -> None:
        self._client = httpx.AsyncClient(
            base_url=bot_settings.backend_base_url,
            timeout=bot_settings.request_timeout_seconds,
        )

    async def _get(self, path: str, params: dict | None = None) -> Any:
        response = await self._client.get(path, params=params)
        return self._handle(response)

    async def _post(self, path: str, json: dict) -> Any:
        response = await self._client.post(path, json=json)
        return self._handle(response)

    @staticmethod
    def _handle(response: httpx.Response) -> Any:
        if response.is_success:
            return response.json()

        try:
            detail = response.json().get("detail", {})
            code = detail.get("code", "UNKNOWN")
            message = detail.get("message", response.text)
        except Exception:
            code = "UNKNOWN"
            message = response.text

        if response.status_code == 402:
            raise FreemiumLimitError(response.status_code, code, message)
        if response.status_code == 401:
            raise AuthNotConnectedError(response.status_code, code, message)

        raise BackendHTTPError(response.status_code, code, message)

    async def close(self) -> None:
        await self._client.aclose()
