"""
Test SC002 — Photo Widget (Bot side).

## Traceability
Feature: F002 — Multimodal Input Processing
Scenario: SC002 — Photo Syllabus Parsing

## BDD
Given: A user sends a photo to the bot.
When:  The PhotoProcessCode calls the backend /process endpoint.
Then:  The bot replies with a formatted list of extracted events.
       If the freemium limit is reached, the bot replies with a payment prompt.
"""

import pytest
from unittest.mock import AsyncMock, patch

from bot.handler.v1.user.scheduling.F002.photo_widget import (
    EventsSyncedAnswer,
    PhotoProcessCode,
    PhotoTrigger,
)
from bot.core.vocab import Vocab
from bot.service.api.base_client import FreemiumLimitError


@pytest.mark.asyncio
async def test_SC002_trigger_extracts_file_id(mock_photo_message, mock_state):
    """PhotoTrigger must extract the last (highest-res) photo file_id."""
    trigger = PhotoTrigger()
    result = await trigger.run(mock_photo_message, mock_state)
    assert result["telegram_id"] == 789012
    assert result["file_id"] == "photo_file_id_abc"


@pytest.mark.asyncio
async def test_SC002_code_returns_events_synced(mock_photo_message, mock_state, sample_events_response):
    """PhotoProcessCode must return 'events_synced' on a successful backend call."""
    with (
        patch("bot.handler.v1.user.scheduling.F002.photo_widget.ProcessClient.download_file", new_callable=AsyncMock) as mock_dl,
        patch("bot.handler.v1.user.scheduling.F002.photo_widget.ProcessClient") as MockClient,
    ):
        mock_dl.return_value = b"fake_bytes"
        instance = MockClient.return_value
        instance.process_photo = AsyncMock(return_value=sample_events_response)
        instance.close = AsyncMock()

        code = PhotoProcessCode()
        result = await code.run({"telegram_id": 789012, "file_id": "photo_file_id_abc"}, mock_state)

    assert result["answer_name"] == "events_synced"
    assert result["data"]["response"] == sample_events_response


@pytest.mark.asyncio
async def test_SC002_code_routes_freemium_limit(mock_photo_message, mock_state):
    """PhotoProcessCode must return 'freemium_limit' when HTTP 402 is raised (SC004)."""
    with (
        patch("bot.handler.v1.user.scheduling.F002.photo_widget.ProcessClient.download_file", new_callable=AsyncMock) as mock_dl,
        patch("bot.handler.v1.user.scheduling.F002.photo_widget.ProcessClient") as MockClient,
    ):
        mock_dl.return_value = b"fake_bytes"
        instance = MockClient.return_value
        instance.process_photo = AsyncMock(
            side_effect=FreemiumLimitError(402, "FREEMIUM_LIMIT_EXCEEDED", "Limit reached")
        )
        instance.close = AsyncMock()

        code = PhotoProcessCode()
        result = await code.run({"telegram_id": 789012, "file_id": "photo_file_id_abc"}, mock_state)

    assert result["answer_name"] == "freemium_limit"


@pytest.mark.asyncio
async def test_SC002_events_synced_answer_formats_event_list(mock_photo_message, mock_state, sample_events_response):
    """EventsSyncedAnswer must mention the event count and title."""
    answer = EventsSyncedAnswer()
    await answer.run(event=mock_photo_message, user_lang="en", data={"response": sample_events_response})

    mock_photo_message.answer.assert_called_once()
    call_args = mock_photo_message.answer.call_args[0][0]
    assert "1" in call_args
    assert "Math Lecture" in call_args
