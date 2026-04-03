"""
Conftest — Shared fixtures for F002 bot widget tests.

## Traceability
Feature: F002 — Multimodal Input Processing
Scenarios: SC002, SC003
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from aiogram.fsm.context import FSMContext
from aiogram.types import Message, PhotoSize, Voice, User


@pytest.fixture
def mock_photo_message() -> Message:
    photo = MagicMock(spec=PhotoSize)
    photo.file_id = "photo_file_id_abc"

    msg = MagicMock(spec=Message)
    msg.from_user = MagicMock(spec=User)
    msg.from_user.id = 789012
    msg.photo = [photo]
    msg.answer = AsyncMock()
    return msg


@pytest.fixture
def mock_voice_message() -> Message:
    voice = MagicMock(spec=Voice)
    voice.file_id = "voice_file_id_xyz"

    msg = MagicMock(spec=Message)
    msg.from_user = MagicMock(spec=User)
    msg.from_user.id = 789012
    msg.voice = voice
    msg.answer = AsyncMock()
    return msg


@pytest.fixture
def mock_state() -> FSMContext:
    state = MagicMock(spec=FSMContext)
    state.get_data = AsyncMock(return_value={})
    state.update_data = AsyncMock()
    return state


@pytest.fixture
def sample_events_response() -> dict:
    return {
        "events": [
            {
                "id": "uuid-1",
                "title": "Math Lecture",
                "description": None,
                "location": "Room 201",
                "start_time": "2026-04-10T09:00:00+00:00",
                "end_time": "2026-04-10T11:00:00+00:00",
                "input_type": "photo",
                "google_event_id": None,
                "is_synced": False,
                "created_at": "2026-04-02T10:00:00+00:00",
            }
        ],
        "message": "1 event(s) processed and queued for sync.",
    }
