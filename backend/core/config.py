"""
Config — Application settings loaded from environment variables.

## Traceability
Feature: F001 — Google OAuth Authentication, F002 — Multimodal Input Processing
Scenarios: SC001, SC002, SC003

## Business context
Central settings object for all services. Uses pydantic-settings so every
required secret is validated at startup, preventing silent misconfiguration.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",  # ignore bot-specific vars (TELEGRAM_BOT_TOKEN etc.)
    )

    # ── Application ────────────────────────────────────────────────────────────
    app_name: str = "CalenMind AI"
    app_env: str = "development"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    secret_key: str  # used by Fernet for token encryption

    # ── Database ───────────────────────────────────────────────────────────────
    database_url: str  # e.g. postgresql+asyncpg://user:pass@localhost:5432/calenmind

    # ── Google OAuth ───────────────────────────────────────────────────────────
    google_client_id: str
    google_client_secret: str
    google_redirect_uri: str  # e.g. http://localhost:8000/api/v1/auth/callback

    # ── AI Providers ───────────────────────────────────────────────────────────
    anthropic_api_key: str        # Claude — image & text parsing
    openai_api_key: str = ""      # kept for compatibility, not actively used
    groq_api_key: str             # Groq Whisper — voice transcription

    # ── Freemium ───────────────────────────────────────────────────────────────
    free_monthly_limit: int = 10  # F004 — max events for free tier

    # ── Telegram (for backend → user notifications) ────────────────────────────
    telegram_bot_token: str


settings = Settings()
