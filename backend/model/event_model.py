"""
EventModel — Stores parsed calendar events created via AI processing.

## Traceability
Feature: F002 — Multimodal Input Processing
Scenarios: SC002, SC003

## Business context
Each row represents one structured calendar event extracted by the AI
service from a user's photo, voice note, or text. raw_ai_output preserves
the original LLM response for debugging and accuracy auditing.
The google_event_id column is populated after a successful Calendar sync.
"""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.core.database import Base
from backend.model.base_model import TimestampMixin, UUIDPrimaryKeyMixin


class EventModel(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "events"

    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Core event fields
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    location: Mapped[str | None] = mapped_column(String(500), nullable=True)
    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Source tracking
    input_type: Mapped[str] = mapped_column(String(20), nullable=False)  # "photo" | "voice" | "text"
    raw_ai_output: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Google Calendar reference (populated after sync)
    google_event_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_synced: Mapped[bool] = mapped_column(default=False, nullable=False)

    # Relationship
    user: Mapped["UserModel"] = relationship("UserModel", back_populates="events")  # noqa: F821

    def __repr__(self) -> str:
        return f"<EventModel title={self.title!r} start={self.start_time}>"
