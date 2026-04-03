"""
BaseModel — Abstract mixin providing id, created_at, updated_at for all tables.

## Traceability
Feature: F001, F002, F004 — All features
Scenarios: SC001, SC002, SC003, SC004

## Business context
All domain models inherit this mixin so every row has a UUID primary key
and automatic audit timestamps. Using a mixin (not a concrete base table)
keeps the Alembic migration graph simple.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column


class TimestampMixin:
    """Adds created_at / updated_at audit columns to any model."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


class UUIDPrimaryKeyMixin:
    """Adds a UUID primary key column to any model."""

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        index=True,
    )
