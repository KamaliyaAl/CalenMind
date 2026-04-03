"""
Test SC002 — Photo Syllabus Parsing.

## Traceability
Feature: F002 — Multimodal Input Processing
Scenario: SC002 — Photo Syllabus Parsing

## BDD
Given: A user has uploaded a valid photo of a syllabus (base64-encoded JPEG).
When:  The AI service processes the image via Claude 3.5 Sonnet.
Then:  One or more ParsedEventSchema objects are returned with valid
       title, start_time, and all fields pass Pydantic validation.
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.schema.ai_schema import AIExtractionResultSchema, ParsedEventSchema
from backend.service.ai_service import AIService


@pytest.mark.asyncio
async def test_SC002_photo_returns_parsed_events(sample_base64_image, sample_ai_extraction_result):
    """AI service must return a non-empty list of events for a valid photo."""
    service = AIService()

    with patch.object(service._anthropic.messages, "create", new_callable=AsyncMock) as mock_create:
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text=json.dumps(sample_ai_extraction_result))]
        mock_create.return_value = mock_response

        events = await service.process(input_type="photo", content=sample_base64_image)

    assert len(events) == 1
    assert isinstance(events[0], ParsedEventSchema)
    assert events[0].title == "Math Lecture"


@pytest.mark.asyncio
async def test_SC002_parsed_event_has_required_fields(sample_base64_image, sample_ai_extraction_result):
    """Every ParsedEventSchema must have a non-empty title and valid start_time."""
    service = AIService()

    with patch.object(service._anthropic.messages, "create", new_callable=AsyncMock) as mock_create:
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text=json.dumps(sample_ai_extraction_result))]
        mock_create.return_value = mock_response

        events = await service.process(input_type="photo", content=sample_base64_image)

    for event in events:
        assert event.title.strip() != ""
        assert event.start_time is not None


@pytest.mark.asyncio
async def test_SC002_invalid_llm_json_raises_ai_parsing_exception(sample_base64_image):
    """Malformed LLM output must raise AIParsingException, not a raw JSON error."""
    from backend.core.exceptions import AIParsingException

    service = AIService()

    with patch.object(service._anthropic.messages, "create", new_callable=AsyncMock) as mock_create:
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="NOT VALID JSON {{{")]
        mock_create.return_value = mock_response

        with pytest.raises(AIParsingException):
            await service.process(input_type="photo", content=sample_base64_image)


@pytest.mark.asyncio
async def test_SC002_empty_events_list_is_valid_response(sample_base64_image):
    """LLM returning no events should produce an empty list, not an error."""
    service = AIService()
    empty_result = {"events": [], "confidence": 0.0, "raw_text": None, "notes": "No events found."}

    with patch.object(service._anthropic.messages, "create", new_callable=AsyncMock) as mock_create:
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text=json.dumps(empty_result))]
        mock_create.return_value = mock_response

        events = await service.process(input_type="photo", content=sample_base64_image)

    assert events == []
