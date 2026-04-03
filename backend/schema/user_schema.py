"""
UserSchema — Pydantic models for user creation, response, and state.

## Traceability
Feature: F001 — Google OAuth Authentication, F004 — Freemium Limits
Scenarios: SC001, SC004

## Business context
These schemas are the contract between the API layer and callers (bot, tests).
They intentionally exclude internal fields (id, timestamps) from public
responses and never expose encrypted token data.
"""

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class UserCreateSchema(BaseModel):
    """Payload for registering a new Telegram user."""

    telegram_id: int = Field(..., description="Telegram numeric user ID")
    telegram_username: str | None = Field(None, description="Telegram @username, if public")


class UserResponseSchema(BaseModel):
    """Public representation of a user returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    telegram_id: int
    telegram_username: str | None
    google_email: str | None
    is_google_connected: bool
    is_premium: bool
    sync_count: int
    sync_reset_date: date | None
    created_at: datetime


class FreemiumStatusSchema(BaseModel):
    """Summary of a user's current freemium usage (F004)."""

    model_config = ConfigDict(from_attributes=True)

    sync_count: int
    monthly_limit: int
    remaining: int
    reset_date: date | None
    is_limit_reached: bool
