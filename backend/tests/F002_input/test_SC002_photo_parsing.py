"""
Test SC002 — Photo Syllabus Parsing.

## Traceability
Feature: F002 — Multimodal Input Processing
Scenario: SC002 — Photo Syllabus Parsing
CR: F002-CR-001 — Robust Photo Parsing for Complex University Syllabi

## BDD
Given: A user has uploaded a valid photo of a syllabus (base64-encoded JPEG/PNG/WEBP).
When:  The AI service processes the image via Claude 3.5 Sonnet.
Then:  One or more ParsedEventSchema objects are returned with valid
       title, start_time, and all fields pass Pydantic validation.

## Test status legend
# [PASSES NOW]  — regression baseline, must stay green before and after CR
# [FAILS NOW]   — red phase; must go green after F002-CR-001 is implemented
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
    """
    Both the initial call AND the retry must fail before AIParsingException is raised.

    MODIFICATION (F002-CR-001 / FR-SC002-04):
    After retry logic is added, one bad response triggers a retry.
    AIParsingException must only fire after BOTH calls return unparseable output.
    side_effect provides two bad responses to exhaust the retry.
    """
    from backend.core.exceptions import AIParsingException

    service = AIService()

    bad_response = MagicMock()
    bad_response.content = [MagicMock(text="NOT VALID JSON {{{")]

    with patch.object(service._anthropic.messages, "create", new_callable=AsyncMock) as mock_create:
        mock_create.side_effect = [bad_response, bad_response]

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


# ── F002-CR-001 NEW TESTS (Red phase — all FAIL on current implementation) ────

# TC-SC002-05 FR-SC002-01
@pytest.mark.asyncio
async def test_SC002_photo_uses_sonnet_model(sample_base64_image, sample_ai_extraction_result):
    """
    FR-SC002-01: Photo path must use claude-sonnet-4-6 for best vision accuracy.
    Updated from claude-3-5-sonnet-20241022 → claude-sonnet-4-6 (CR F002-CR-002).
    """
    service = AIService()

    with patch.object(service._anthropic.messages, "create", new_callable=AsyncMock) as mock_create:
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text=json.dumps(sample_ai_extraction_result))]
        mock_create.return_value = mock_response

        await service.process(input_type="photo", content=sample_base64_image)

    called_model = mock_create.call_args.kwargs.get("model") or mock_create.call_args.args[0]
    assert called_model == "claude-sonnet-4-6", (
        f"Expected claude-sonnet-4-6, got {called_model}"
    )


# TC-SC002-06 [FAILS NOW] NFR-SC002-01
@pytest.mark.asyncio
async def test_SC002_photo_max_tokens_is_8192(sample_base64_image, sample_ai_extraction_result):
    """
    NFR-SC002-01: Photo path must request max_tokens=8192 to handle dense syllabi.

    FAILS NOW: current value is 4096.
    """
    service = AIService()

    with patch.object(service._anthropic.messages, "create", new_callable=AsyncMock) as mock_create:
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text=json.dumps(sample_ai_extraction_result))]
        mock_create.return_value = mock_response

        await service.process(input_type="photo", content=sample_base64_image)

    called_max_tokens = mock_create.call_args.kwargs.get("max_tokens")
    assert called_max_tokens == 8192, (
        f"Expected max_tokens=8192, got {called_max_tokens}"
    )


# TC-SC002-07 [FAILS NOW] FR-SC002-02
@pytest.mark.asyncio
async def test_SC002_photo_detects_png_media_type(
    sample_base64_png_image, sample_ai_extraction_result
):
    """
    FR-SC002-02: PNG bytes (magic \\x89PNG) must be sent to Anthropic as image/png.

    FAILS NOW: media_type is hardcoded as 'image/jpeg' regardless of input.
    """
    service = AIService()

    with patch.object(service._anthropic.messages, "create", new_callable=AsyncMock) as mock_create:
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text=json.dumps(sample_ai_extraction_result))]
        mock_create.return_value = mock_response

        await service.process(input_type="photo", content=sample_base64_png_image)

    messages_sent = mock_create.call_args.kwargs.get("messages") or mock_create.call_args.args[0]
    image_block = messages_sent[0]["content"][0]
    actual_media_type = image_block["source"]["media_type"]
    assert actual_media_type == "image/png", (
        f"Expected image/png for PNG input, got {actual_media_type}"
    )


# TC-SC002-08 [FAILS NOW] FR-SC002-02
@pytest.mark.asyncio
async def test_SC002_photo_detects_webp_media_type(
    sample_base64_webp_image, sample_ai_extraction_result
):
    """
    FR-SC002-02: WEBP bytes (RIFF....WEBP) must be sent to Anthropic as image/webp.

    FAILS NOW: media_type is hardcoded as 'image/jpeg'.
    """
    service = AIService()

    with patch.object(service._anthropic.messages, "create", new_callable=AsyncMock) as mock_create:
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text=json.dumps(sample_ai_extraction_result))]
        mock_create.return_value = mock_response

        await service.process(input_type="photo", content=sample_base64_webp_image)

    messages_sent = mock_create.call_args.kwargs.get("messages") or mock_create.call_args.args[0]
    image_block = messages_sent[0]["content"][0]
    actual_media_type = image_block["source"]["media_type"]
    assert actual_media_type == "image/webp", (
        f"Expected image/webp for WEBP input, got {actual_media_type}"
    )


# TC-SC002-09 [FAILS NOW] FR-SC002-03
def test_SC002_parse_llm_output_strips_markdown_fences(sample_ai_extraction_result):
    """
    FR-SC002-03: _parse_llm_output must handle JSON wrapped in ```json ... ``` fences.

    FAILS NOW: json.loads() on a fenced string raises JSONDecodeError immediately.
    Tests the static method directly — applies to photo, voice, and text paths.
    """
    fenced_json = "```json\n" + json.dumps(sample_ai_extraction_result) + "\n```"

    result = AIService._parse_llm_output(fenced_json)

    assert len(result.events) == 1
    assert result.events[0].title == "Math Lecture"


# TC-SC002-10 [FAILS NOW] FR-SC002-04
@pytest.mark.asyncio
async def test_SC002_photo_retries_once_on_parse_failure(
    sample_base64_image, sample_ai_extraction_result
):
    """
    FR-SC002-04: When first Claude call returns unparseable output, photo path must
    retry once. If the second call succeeds, events must be returned (no exception).

    FAILS NOW: no retry logic; AIParsingException raised on first failure.
    """
    service = AIService()

    bad_response = MagicMock()
    bad_response.content = [MagicMock(text="UNPARSEABLE OUTPUT %%%")]

    good_response = MagicMock()
    good_response.content = [MagicMock(text=json.dumps(sample_ai_extraction_result))]

    with patch.object(service._anthropic.messages, "create", new_callable=AsyncMock) as mock_create:
        mock_create.side_effect = [bad_response, good_response]

        events = await service.process(input_type="photo", content=sample_base64_image)

    assert mock_create.call_count == 2, (
        f"Expected 2 calls (initial + retry), got {mock_create.call_count}"
    )
    assert len(events) == 1
    assert events[0].title == "Math Lecture"


# ── F002-CR-001 REGRESSION GUARDS (must pass before AND after implementation) ─

# TC-SC002-R01 [PASSES NOW] FR-SC002-02 regression
@pytest.mark.asyncio
async def test_SC002_photo_jpeg_media_type_preserved(
    sample_base64_image, sample_ai_extraction_result
):
    """
    FR-SC002-02 regression: JPEG bytes must still produce image/jpeg after
    media-type detection is introduced. Magic bytes \\xff\\xd8\\xff = JPEG.
    """
    service = AIService()

    with patch.object(service._anthropic.messages, "create", new_callable=AsyncMock) as mock_create:
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text=json.dumps(sample_ai_extraction_result))]
        mock_create.return_value = mock_response

        await service.process(input_type="photo", content=sample_base64_image)

    messages_sent = mock_create.call_args.kwargs.get("messages") or mock_create.call_args.args[0]
    image_block = messages_sent[0]["content"][0]
    actual_media_type = image_block["source"]["media_type"]
    assert actual_media_type == "image/jpeg"


# TC-SC002-R02 [PASSES NOW] FR-SC002-03 regression
def test_SC002_parse_llm_output_valid_json_no_fences(sample_ai_extraction_result):
    """
    FR-SC002-03 regression: _parse_llm_output must still parse clean JSON
    (no fences) correctly after fence-stripping logic is added.
    """
    clean_json = json.dumps(sample_ai_extraction_result)

    result = AIService._parse_llm_output(clean_json)

    assert len(result.events) == 1
    assert result.events[0].title == "Math Lecture"
