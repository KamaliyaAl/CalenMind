"""
UserModel — Stores Telegram users and their freemium usage counters.

## Traceability
Feature: F001 — Google OAuth Authentication, F004 — Freemium Limits
Scenarios: SC001, SC004

## Business context
One row per Telegram user. The sync_count and sync_reset_date fields
are the enforcement mechanism for the 10-syncs/month freemium rule (F004).
The google_email field is populated after OAuth is completed (F001).
"""

from datetime import date

from sqlalchemy import BigInteger, Boolean, Date, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.core.database import Base
from backend.model.base_model import TimestampMixin, UUIDPrimaryKeyMixin


class UserModel(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "users"

    # Telegram identity
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False, index=True)
    telegram_username: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Google identity (populated after F001 OAuth flow)
    google_email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    is_google_connected: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Freemium counters (F004)
    sync_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    sync_reset_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    # Subscription flag
    is_premium: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Relationships
    oauth_token: Mapped["TokenModel"] = relationship(  # noqa: F821
        "TokenModel", back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    events: Mapped[list["EventModel"]] = relationship(  # noqa: F821
        "EventModel", back_populates="user", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<UserModel telegram_id={self.telegram_id} email={self.google_email}>"
