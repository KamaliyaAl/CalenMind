"""
Conftest — Shared fixtures for F004 (Freemium Limits) tests.

## Traceability
Feature: F004 — Freemium Limits
Scenarios: SC004
"""

from datetime import date
from unittest.mock import AsyncMock, MagicMock

import pytest

from backend.model.user_model import UserModel


@pytest.fixture
def free_user_at_limit() -> UserModel:
    """A free-tier user who has consumed all 10 monthly syncs."""
    user = MagicMock(spec=UserModel)
    user.is_premium = False
    user.sync_count = 10
    user.sync_reset_date = date.today()
    return user


@pytest.fixture
def free_user_below_limit() -> UserModel:
    """A free-tier user with 3 syncs used (7 remaining)."""
    user = MagicMock(spec=UserModel)
    user.is_premium = False
    user.sync_count = 3
    user.sync_reset_date = date.today()
    return user


@pytest.fixture
def premium_user() -> UserModel:
    """A premium user — must bypass all limit checks."""
    user = MagicMock(spec=UserModel)
    user.is_premium = True
    user.sync_count = 999
    user.sync_reset_date = date.today()
    return user


@pytest.fixture
def mock_user_repo():
    repo = MagicMock()
    repo.increment_sync_count = AsyncMock(side_effect=lambda u: u)
    return repo
