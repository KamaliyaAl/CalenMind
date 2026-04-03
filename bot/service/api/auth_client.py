"""
AuthClient — Bot-side API client for Google OAuth endpoints.

## Traceability
Feature: F001 — Google OAuth Authentication
Scenarios: SC001

## Business context
The bot never performs OAuth directly — it asks the backend for a
consent URL, sends it to the user, and later calls /auth/success to
confirm connection. No credentials ever pass through the bot process.
"""

from bot.service.api.base_client import BaseClient


class AuthClient(BaseClient):
    async def get_auth_url(self, telegram_id: int) -> str:
        """Request the Google OAuth consent URL for the given user."""
        data = await self._get("/api/v1/auth/login", params={"telegram_id": telegram_id})
        return data["auth_url"]

    async def get_user_status(self, telegram_id: int) -> dict:
        """Fetch the user's profile including is_google_connected flag."""
        return await self._get("/api/v1/users/me", params={"telegram_id": telegram_id})

    async def get_freemium_status(self, telegram_id: int) -> dict:
        """Fetch the user's freemium usage summary."""
        return await self._get("/api/v1/users/me/freemium", params={"telegram_id": telegram_id})

    async def disconnect(self, telegram_id: int) -> dict:
        """Remove stored OAuth tokens and mark user as disconnected."""
        response = await self._client.post(
            "/api/v1/auth/disconnect",
            params={"telegram_id": telegram_id},
        )
        return self._handle(response)
