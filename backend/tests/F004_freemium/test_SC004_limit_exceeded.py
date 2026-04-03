"""
Test SC004 — Freemium Limit Exceeded.

## Traceability
Feature: F004 — Freemium Limits
Scenario: SC004 — Limit Exceeded
Test Case: TC-F004-01

## BDD
Given: A free-tier user has already performed 10 syncs in the current month.
When:  They attempt to sync an 11th event via FreemiumService.check_and_increment().
Then:  FreemiumLimitExceededException (HTTP 402) is raised.
       No event is created. No sync_count increment occurs.

Given: A premium user has performed any number of syncs.
When:  They attempt another sync.
Then:  The check passes and sync_count is incremented.

Given: A free-tier user has performed 3 syncs.
When:  They attempt another sync.
Then:  The check passes and sync_count is incremented.
"""

import pytest

from backend.core.exceptions import FreemiumLimitExceededException
from backend.service.freemium_service import FreemiumService


@pytest.mark.asyncio
async def test_SC004_free_user_at_limit_raises_exception(free_user_at_limit, mock_user_repo):
    """
    TC-F004-01: FreemiumService must raise FreemiumLimitExceededException (HTTP 402)
    when a free user has reached their monthly limit.
    """
    service = FreemiumService(user_repo=mock_user_repo)

    with pytest.raises(FreemiumLimitExceededException) as exc_info:
        await service.check_and_increment(free_user_at_limit)

    assert exc_info.value.status_code == 402
    detail = exc_info.value.detail
    assert detail["code"] == "FREEMIUM_LIMIT_EXCEEDED"
    # Counter must NOT be incremented after a limit violation
    mock_user_repo.increment_sync_count.assert_not_called()


@pytest.mark.asyncio
async def test_SC004_free_user_below_limit_increments(free_user_below_limit, mock_user_repo):
    """Free user with remaining syncs must succeed and trigger counter increment."""
    service = FreemiumService(user_repo=mock_user_repo)

    await service.check_and_increment(free_user_below_limit)

    mock_user_repo.increment_sync_count.assert_called_once_with(free_user_below_limit)


@pytest.mark.asyncio
async def test_SC004_premium_user_bypasses_limit(premium_user, mock_user_repo):
    """Premium users must bypass the freemium gate entirely (no exception, no increment)."""
    service = FreemiumService(user_repo=mock_user_repo)

    result = await service.check_and_increment(premium_user)

    assert result is premium_user
    mock_user_repo.increment_sync_count.assert_not_called()


def test_SC004_get_status_reports_limit_reached(free_user_at_limit, mock_user_repo):
    """get_status must report is_limit_reached=True and remaining=0 for an exhausted user."""
    service = FreemiumService(user_repo=mock_user_repo)

    status = service.get_status(free_user_at_limit)

    assert status.is_limit_reached is True
    assert status.remaining == 0
    assert status.sync_count == 10


def test_SC004_get_status_reports_remaining_syncs(free_user_below_limit, mock_user_repo):
    """get_status must return correct remaining count (10 - 3 = 7)."""
    service = FreemiumService(user_repo=mock_user_repo)

    status = service.get_status(free_user_below_limit)

    assert status.remaining == 7
    assert status.is_limit_reached is False
