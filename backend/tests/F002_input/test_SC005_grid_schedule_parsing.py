"""
Test SC005 — Complex Grid Schedule Parsing.

## Traceability
Feature: F002 — Multimodal Input Processing
Scenario: SC005 — Complex Grid Schedule Parsing
CR: F002-CR-002 — Grid/Table Schedule Parsing

## BDD
Given: A user sends a photo of a university timetable grid
       (rows = time slots e.g. "9:00-10:30", columns = days e.g. Пн/Mon).
When:  The AI service (Claude Sonnet 4.6) processes the image with grid instructions.
Then:  Multiple ParsedEventSchema objects are returned — one per non-empty cell.
       Each event has RRULE recurrence for the correct weekday.
       The photo user instruction contains explicit grid traversal keywords.
       The system prompt contains grid/table parsing rules.
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.schema.ai_schema import ParsedEventSchema
from backend.service.ai_service import AIService, _EXTRACTION_SYSTEM_PROMPT


GRID_AI_RESULT = {
    "events": [
        {
            "title": "Математика",
            "description": None,
            "location": None,
            "start_time": "2026-04-06T09:00:00+03:00",
            "end_time": "2026-04-06T10:30:00+03:00",
            "recurrence": ["RRULE:FREQ=WEEKLY;BYDAY=MO"],
        },
        {
            "title": "Физика",
            "description": None,
            "location": "Аудитория 301",
            "start_time": "2026-04-07T10:40:00+03:00",
            "end_time": "2026-04-07T12:10:00+03:00",
            "recurrence": ["RRULE:FREQ=WEEKLY;BYDAY=TU"],
        },
        {
            "title": "Английский язык",
            "description": None,
            "location": None,
            "start_time": "2026-04-08T09:00:00+03:00",
            "end_time": "2026-04-08T10:30:00+03:00",
            "recurrence": ["RRULE:FREQ=WEEKLY;BYDAY=WE"],
        },
    ],
    "confidence": 0.95,
    "raw_text": None,
    "notes": "Grid timetable parsed: 3 weekly events extracted.",
}


@pytest.mark.asyncio
async def test_SC005_grid_photo_returns_multiple_events(sample_base64_image):
    """
    Grid timetable photo must produce multiple events (one per cell).
    FR-SC005-01: System prompt contains grid traversal rules.
    FR-SC005-02: User instruction contains explicit grid keywords.
    """
    service = AIService()

    with patch.object(service._anthropic.messages, "create", new_callable=AsyncMock) as mock_create:
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text=json.dumps(GRID_AI_RESULT))]
        mock_create.return_value = mock_response

        events = await service.process(input_type="photo", content=sample_base64_image)

    assert len(events) == 3
    for event in events:
        assert isinstance(event, ParsedEventSchema)
        assert event.recurrence is not None
        assert any("RRULE:FREQ=WEEKLY" in r for r in event.recurrence)


@pytest.mark.asyncio
async def test_SC005_photo_instruction_contains_grid_keywords(sample_base64_image):
    """
    FR-SC005-02: The user instruction passed to Claude must include
    explicit grid traversal keywords ("grid", "cell", "row", "column").
    """
    service = AIService()

    with patch.object(service._anthropic.messages, "create", new_callable=AsyncMock) as mock_create:
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text=json.dumps(GRID_AI_RESULT))]
        mock_create.return_value = mock_response

        await service.process(input_type="photo", content=sample_base64_image)

    messages_sent = mock_create.call_args.kwargs.get("messages") or mock_create.call_args.args[0]
    # User instruction is the second content item (after the image block)
    user_instruction = messages_sent[0]["content"][1]["text"].lower()

    assert "grid" in user_instruction or "cell" in user_instruction, (
        f"User instruction must reference grid/cell traversal, got: {user_instruction[:200]}"
    )


def test_SC005_system_prompt_contains_grid_rules():
    """
    FR-SC005-01: The system prompt must contain explicit GRID/TABLE schedule parsing rules.
    These rules instruct Claude to identify column headers (days) and row headers (times).
    """
    prompt_lower = _EXTRACTION_SYSTEM_PROMPT.lower()
    assert "grid" in prompt_lower or "table" in prompt_lower, (
        "System prompt must contain grid/table parsing instructions (SC005)"
    )
    assert "column" in prompt_lower, (
        "System prompt must reference 'column' for day identification"
    )
    assert "row" in prompt_lower, (
        "System prompt must reference 'row' for time identification"
    )


@pytest.mark.asyncio
async def test_SC005_grid_events_have_weekly_rrule(sample_base64_image):
    """
    Every event extracted from a grid must have RRULE:FREQ=WEEKLY with a BYDAY code.
    This validates the recurring-event contract for timetable inputs.
    """
    service = AIService()

    with patch.object(service._anthropic.messages, "create", new_callable=AsyncMock) as mock_create:
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text=json.dumps(GRID_AI_RESULT))]
        mock_create.return_value = mock_response

        events = await service.process(input_type="photo", content=sample_base64_image)

    byday_codes = {"MO", "TU", "WE", "TH", "FR", "SA", "SU"}
    for event in events:
        assert event.recurrence, f"Event '{event.title}' must have recurrence"
        rrule = event.recurrence[0]
        assert "FREQ=WEEKLY" in rrule, f"Expected FREQ=WEEKLY in {rrule}"
        assert any(f"BYDAY={code}" in rrule for code in byday_codes), (
            f"Expected a valid BYDAY code in {rrule}"
        )
