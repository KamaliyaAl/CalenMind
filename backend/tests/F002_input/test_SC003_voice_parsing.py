"""
Test SC003 — Voice Note Parsing.

## Traceability
Feature: F002 — Multimodal Input Processing
Scenario: SC003 — Voice Note Parsing

## BDD
Given: A user sends a voice note saying "Meeting with Bob tomorrow at 2 PM".
When:  The AI service transcribes it via Whisper and extracts events via GPT-4o-mini.
Then:  A ParsedEventSchema is returned with title containing "Bob" or "Meeting"
       and a valid start_time.
"""

import base64
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.schema.ai_schema import ParsedEventSchema
from backend.service.ai_service import AIService


VOICE_AI_RESULT = {
    "events": [
        {
            "title": "Meeting with Bob",
            "description": None,
            "location": None,
            "start_time": "2026-04-03T14:00:00+00:00",
            "end_time": "2026-04-03T15:00:00+00:00",
        }
    ],
    "confidence": 0.9,
    "raw_text": "Meeting with Bob tomorrow at 2 PM",
    "notes": None,
}


@pytest.fixture
def sample_base64_audio() -> str:
    return base64.b64encode(b"fake_ogg_audio_bytes").decode()


@pytest.mark.asyncio
async def test_SC003_voice_transcription_then_extraction(sample_base64_audio):
    """Voice pipeline must call Whisper first, then GPT-4o-mini for extraction."""
    service = AIService()

    with (
        patch.object(service._openai.audio.transcriptions, "create", new_callable=AsyncMock) as mock_whisper,
        patch.object(service._openai.chat.completions, "create", new_callable=AsyncMock) as mock_gpt,
    ):
        mock_whisper.return_value = "Meeting with Bob tomorrow at 2 PM"

        mock_choice = MagicMock()
        mock_choice.message.content = json.dumps(VOICE_AI_RESULT)
        mock_gpt.return_value = MagicMock(choices=[mock_choice])

        events = await service.process(input_type="voice", content=sample_base64_audio)

    mock_whisper.assert_called_once()
    mock_gpt.assert_called_once()
    assert len(events) == 1
    assert isinstance(events[0], ParsedEventSchema)


@pytest.mark.asyncio
async def test_SC003_event_title_reflects_transcript(sample_base64_audio):
    """Extracted event title should contain recognisable content from the voice note."""
    service = AIService()

    with (
        patch.object(service._openai.audio.transcriptions, "create", new_callable=AsyncMock) as mock_whisper,
        patch.object(service._openai.chat.completions, "create", new_callable=AsyncMock) as mock_gpt,
    ):
        mock_whisper.return_value = "Meeting with Bob tomorrow at 2 PM"
        mock_choice = MagicMock()
        mock_choice.message.content = json.dumps(VOICE_AI_RESULT)
        mock_gpt.return_value = MagicMock(choices=[mock_choice])

        events = await service.process(input_type="voice", content=sample_base64_audio)

    assert "Bob" in events[0].title or "Meeting" in events[0].title


@pytest.mark.asyncio
async def test_SC003_start_time_is_datetime(sample_base64_audio):
    """start_time field must be a proper datetime, not a string."""
    from datetime import datetime

    service = AIService()

    with (
        patch.object(service._openai.audio.transcriptions, "create", new_callable=AsyncMock) as mock_whisper,
        patch.object(service._openai.chat.completions, "create", new_callable=AsyncMock) as mock_gpt,
    ):
        mock_whisper.return_value = "Meeting with Bob tomorrow at 2 PM"
        mock_choice = MagicMock()
        mock_choice.message.content = json.dumps(VOICE_AI_RESULT)
        mock_gpt.return_value = MagicMock(choices=[mock_choice])

        events = await service.process(input_type="voice", content=sample_base64_audio)

    assert isinstance(events[0].start_time, datetime)
