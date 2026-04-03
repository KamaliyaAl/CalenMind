"""
EventRepository — Database access for EventModel.

## Traceability
Feature: F002 — Multimodal Input Processing
Scenarios: SC002, SC003

## Business context
Provides user-scoped event queries so the calendar service can list
unsynced events and the API can return a user's event history.
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.model.event_model import EventModel
from backend.repository.base_repository import BaseRepository


class EventRepository(BaseRepository[EventModel]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(EventModel, session)

    async def list_by_user(self, user_id: str, limit: int = 50) -> list[EventModel]:
        result = await self._session.execute(
            select(EventModel)
            .where(EventModel.user_id == user_id)
            .order_by(EventModel.start_time.asc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def list_unsynced(self, user_id: str) -> list[EventModel]:
        result = await self._session.execute(
            select(EventModel).where(
                EventModel.user_id == user_id,
                EventModel.is_synced.is_(False),
            )
        )
        return list(result.scalars().all())

    async def mark_synced(self, event: EventModel, google_event_id: str) -> EventModel:
        event.is_synced = True
        event.google_event_id = google_event_id
        return await self.update(event)
