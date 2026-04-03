"""
Test SC003 — Voice Note Parsing.

## Traceability
Feature: F002 — Multimodal Input Processing
Scenario: SC003 — Voice Note Parsing

## BDD
Given: A user sends a voice note saying "Meeting with Bob tomorrow at 2 PM".
When:  The AI service transcribes it via Groq Whisper and extracts events via Claude Haiku.
Then:  A ParsedEventSchema is returned with title containing "Bob" or "Meeting"
       and a valid start_time datetime.

## Note
Voice path uses two separate clients:
  - self._groq.audio.transcriptions (Groq Whisper STT)
  - self._anthropic.messages (Claude Haiku entity extraction)
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
            "start_time": "2026-04-04T14:00:00+03:00",
            "end_time": "2026-04-04T15:00:00+03:00",
            "recurrence": None,
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
    """Voice pipeline must call Groq Whisper first, then Claude Haiku for extraction."""
    service = AIService()

    mock_anthropic_response = MagicMock()
    mock_anthropic_response.content = [MagicMock(text=json.dumps(VOICE_AI_RESULT))]

    with (
        patch.object(service._groq.audio.transcriptions, "create", new_callable=AsyncMock) as mock_whisper,
        patch.object(service._anthropic.messages, "create", new_callable=AsyncMock) as mock_claude,
    ):
        mock_whisper.return_value = "Meeting with Bob tomorrow at 2 PM"
        mock_claude.return_value = mock_anthropic_response

        events = await service.process(input_type="voice", content=sample_base64_audio)

    mock_whisper.assert_called_once()
    mock_claude.assert_called_once()
    assert len(events) == 1
    assert isinstance(events[0], ParsedEventSchema)


@pytest.mark.asyncio
async def test_SC003_event_title_reflects_transcript(sample_base64_audio):
    """Extracted event title should contain recognisable content from the voice note."""
    service = AIService()

    mock_anthropic_response = MagicMock()
    mock_anthropic_response.content = [MagicMock(text=json.dumps(VOICE_AI_RESULT))]

    with (
        patch.object(service._groq.audio.transcriptions, "create", new_callable=AsyncMock) as mock_whisper,
        patch.object(service._anthropic.messages, "create", new_callable=AsyncMock) as mock_claude,
    ):
        mock_whisper.return_value = "Meeting with Bob tomorrow at 2 PM"
        mock_claude.return_value = mock_anthropic_response

        events = await service.process(input_type="voice", content=sample_base64_audio)

    assert "Bob" in events[0].title or "Meeting" in events[0].title


@pytest.mark.asyncio
async def test_SC003_start_time_is_datetime(sample_base64_audio):
    """start_time field must be a proper datetime, not a string."""
    from datetime import datetime

    service = AIService()

    mock_anthropic_response = MagicMock()
    mock_anthropic_response.content = [MagicMock(text=json.dumps(VOICE_AI_RESULT))]

    with (
        patch.object(service._groq.audio.transcriptions, "create", new_callable=AsyncMock) as mock_whisper,
        patch.object(service._anthropic.messages, "create", new_callable=AsyncMock) as mock_claude,
    ):
        mock_whisper.return_value = "Meeting with Bob tomorrow at 2 PM"
        mock_claude.return_value = mock_anthropic_response

        events = await service.process(input_type="voice", content=sample_base64_audio)

    assert isinstance(events[0].start_time, datetime)
