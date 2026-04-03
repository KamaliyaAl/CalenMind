"""
FreemiumService — Enforces the 10 free event-syncs per calendar month limit.

## Traceability
Feature: F004 — Freemium Limits
Scenarios: SC004

## Business context
Free-tier users are allowed 10 syncs per calendar month. On the first sync
of each new month the counter resets. Premium users bypass the check entirely.
FreemiumLimitExceededException (HTTP 402) triggers a payment prompt in the bot.
"""

from datetime import date

from backend.core.config import settings
from backend.core.exceptions import FreemiumLimitExceededException
from backend.model.user_model import UserModel
from backend.repository.user_repository import UserRepository
from backend.schema.user_schema import FreemiumStatusSchema


class FreemiumService:
    def __init__(self, user_repo: UserRepository) -> None:
        self._user_repo = user_repo

    async def check_and_increment(self, user: UserModel) -> UserModel:
        """
        Verify the user is within their monthly limit, then increment.
        Raises FreemiumLimitExceededException (SC004) if limit is reached.
        Returns the updated UserModel.
        """
        if user.is_premium:
            return user

        today = date.today()
        self._maybe_reset_counter(user, today)

        if user.sync_count >= settings.free_monthly_limit:
            raise FreemiumLimitExceededException(settings.free_monthly_limit)

        user = await self._user_repo.increment_sync_count(user)
        return user

    def get_status(self, user: UserModel) -> FreemiumStatusSchema:
        """Return a snapshot of the user's current freemium usage."""
        today = date.today()
        self._maybe_reset_counter(user, today)
        remaining = max(0, settings.free_monthly_limit - user.sync_count)
        return FreemiumStatusSchema(
            sync_count=user.sync_count,
            monthly_limit=settings.free_monthly_limit,
            remaining=remaining,
            reset_date=user.sync_reset_date,
            is_limit_reached=user.sync_count >= settings.free_monthly_limit,
        )

    @staticmethod
    def _maybe_reset_counter(user: UserModel, today: date) -> None:
        """Reset counter if we're in a new calendar month (mutates in-place)."""
        if user.sync_reset_date is None or today.month != user.sync_reset_date.month:
            user.sync_count = 0
            user.sync_reset_date = today
