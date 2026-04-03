"""
BaseRepository — Generic async CRUD repository for SQLAlchemy models.

## Traceability
Feature: F001, F002, F004 — All features
Scenarios: SC001, SC002, SC003, SC004

## Business context
Provides a typed, reusable base so concrete repositories only implement
domain-specific query methods. All operations are async and take an
explicit AsyncSession to stay compatible with FastAPI's dependency injection.
"""

from typing import Generic, TypeVar

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.database import Base

ModelT = TypeVar("ModelT", bound=Base)


class BaseRepository(Generic[ModelT]):
    """Generic repository providing get, list, create, update, delete."""

    def __init__(self, model: type[ModelT], session: AsyncSession) -> None:
        self._model = model
        self._session = session

    async def get_by_id(self, record_id: str) -> ModelT | None:
        result = await self._session.execute(
            select(self._model).where(self._model.id == record_id)
        )
        return result.scalar_one_or_none()

    async def list_all(self, limit: int = 100, offset: int = 0) -> list[ModelT]:
        result = await self._session.execute(
            select(self._model).limit(limit).offset(offset)
        )
        return list(result.scalars().all())

    async def create(self, instance: ModelT) -> ModelT:
        self._session.add(instance)
        await self._session.flush()
        await self._session.refresh(instance)
        return instance

    async def update(self, instance: ModelT) -> ModelT:
        merged = await self._session.merge(instance)
        await self._session.flush()
        await self._session.refresh(merged)
        return merged

    async def delete(self, instance: ModelT) -> None:
        await self._session.delete(instance)
        await self._session.flush()
