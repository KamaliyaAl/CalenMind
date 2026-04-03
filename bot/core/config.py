"""
Config — Bot-specific settings loaded from environment variables.

## Traceability
Feature: F001 — Google OAuth Authentication, F002 — Multimodal Input Processing
Scenarios: SC001, SC002, SC003

## Business context
Isolates bot configuration from the backend. The only coupling to the
backend is BACKEND_BASE_URL so any deployment topology (same host,
separate containers, etc.) can be supported without code changes.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class BotSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",  # ignore backend-specific vars (DATABASE_URL etc.)
    )

    telegram_bot_token: str
    backend_base_url: str = "http://localhost:8000"
    request_timeout_seconds: int = 30


bot_settings = BotSettings()
