"""
UserRepository — Database access for UserModel.

## Traceability
Feature: F001 — Google OAuth Authentication, F004 — Freemium Limits
Scenarios: SC001, SC004

## Business context
Provides Telegram-ID-based lookup (the natural key for bot interactions)
and upsert logic so the bot can call /process without a separate registration
step. Also exposes freemium counter mutations used by FreemiumService.
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.model.user_model import UserModel
from backend.repository.base_repository import BaseRepository


class UserRepository(BaseRepository[UserModel]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(UserModel, session)

    async def get_by_telegram_id(self, telegram_id: int) -> UserModel | None:
        result = await self._session.execute(
            select(UserModel).where(UserModel.telegram_id == telegram_id)
        )
        return result.scalar_one_or_none()

    async def get_or_create(self, telegram_id: int, username: str | None = None) -> tuple[UserModel, bool]:
        """
        Return (user, created). Creates the user if not found.
        Used on every bot interaction to ensure the user exists.
        """
        user = await self.get_by_telegram_id(telegram_id)
        if user:
            return user, False

        user = UserModel(telegram_id=telegram_id, telegram_username=username)
        user = await self.create(user)
        return user, True

    async def increment_sync_count(self, user: UserModel) -> UserModel:
        user.sync_count += 1
        return await self.update(user)

    async def reset_sync_count(self, user: UserModel) -> UserModel:
        user.sync_count = 0
        return await self.update(user)

    async def mark_google_connected(self, user: UserModel, email: str) -> UserModel:
        user.is_google_connected = True
        user.google_email = email
        return await self.update(user)
