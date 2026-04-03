"""
Conftest — Shared fixtures for F001 bot widget tests.

## Traceability
Feature: F001 — Google OAuth Authentication
Scenarios: SC001
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from aiogram.fsm.context import FSMContext
from aiogram.types import Chat, Message, User


@pytest.fixture
def mock_message() -> Message:
    msg = MagicMock(spec=Message)
    msg.from_user = MagicMock(spec=User)
    msg.from_user.id = 123456
    msg.from_user.username = "testuser"
    msg.answer = AsyncMock()
    return msg


@pytest.fixture
def mock_state() -> FSMContext:
    state = MagicMock(spec=FSMContext)
    state.get_data = AsyncMock(return_value={})
    state.update_data = AsyncMock()
    return state
