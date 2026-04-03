"""
AIService — Multimodal AI orchestration: routes photo/voice/text inputs
to the appropriate LLM and returns validated ParsedEventSchema objects.

## Traceability
Feature: F002 — Multimodal Input Processing
Scenarios: SC002, SC003, SC005
CR: F002-CR-001 — Robust Photo Parsing for Complex University Syllabi
CR: F002-CR-002 — Grid/Table Schedule Parsing (SC005)

## Business context
Routing strategy (live, supersedes tech_research.md):
  - Photo  → claude-sonnet-4-6 (best table/syllabus vision accuracy)
  - Voice  → Groq whisper-large-v3 (STT) → claude-haiku-4-5-20251001 (entity extraction)
  - Text   → claude-haiku-4-5-20251001 (cost-efficient for simple strings)

## CR F002-CR-001 changes (photo path only):
  - FR-SC002-01: upgraded model to claude-sonnet-4-6
  - FR-SC002-02: media type auto-detected from magic bytes (JPEG / PNG / WEBP)
  - FR-SC002-03: _parse_llm_output strips markdown fences before json.loads
  - FR-SC002-04: one automatic retry on parse failure with corrective instruction
  - NFR-SC002-01: max_tokens raised to 8192 for photo path

## CR F002-CR-002 changes (SC005 grid parsing):
  - FR-SC005-01: added GRID/TABLE SCHEDULE section to system prompt
  - FR-SC005-02: photo user instruction now explicitly requests grid traversal

All outputs are validated through AIExtractionResultSchema ensuring
a data contract before any DB write occurs.
"""

import base64
import json
import logging
from typing import Literal

import anthropic
import groq

from backend.core.config import settings
from backend.core.exceptions import AIParsingException
from backend.schema.ai_schema import AIExtractionResultSchema, ParsedEventSchema

logger = logging.getLogger(__name__)

_EXTRACTION_SYSTEM_PROMPT = """You are a calendar assistant.
Current date and time: {now} (UTC+3, Moscow time).
Today is {weekday}, {today}.

CRITICAL: All dates MUST be in year {year}. Never use past years.

RELATIVE DATE RESOLUTION (calculate from today's date above):
- "tomorrow" → {today} + 1 day
- "on Friday" / "this Friday" → the nearest upcoming Friday from today (if today IS Friday, use next week's Friday)
- "next Monday" → the Monday of next week
- "in 3 days" → today + 3 days
- If only a time is given with no date → use today's date
- ALWAYS compute the exact calendar date. Do not guess or use approximate years.

Extract ALL events from the input. Supports Russian and English.

CRITICAL RULES FOR GRID/TABLE SCHEDULES (SC005):
If the image is a 2D grid/table timetable (rows = time slots, columns = days of week):
STEP 1 — Read column headers: identify each column header as a day of the week (Пн/Mon, Вт/Tue, Ср/Wed, Чт/Thu, Пт/Fri, Сб/Sat, Вс/Sun).
STEP 2 — Read row headers: identify each row header as a time slot (e.g. "9:00–10:30", "10:40–12:10").
STEP 3 — For EVERY non-empty cell: combine its ROW time + COLUMN day → create one event.
         Cell content = event title (subject name / class name).
         Do NOT skip any cell that contains text.
STEP 4 — Each grid event is a WEEKLY recurring event (RRULE).
         Use the NEXT occurrence of that weekday from today as start_time.
STEP 5 — If a cell contains multiple lines (e.g. subject + room/teacher), use the subject as title, room as location.
- BYDAY codes: MO=Monday, TU=Tuesday, WE=Wednesday, TH=Thursday, FR=Friday, SA=Saturday, SU=Sunday
- Example: cell at row "9:00–10:30" / column "Пн" containing "Математика" →
    title="Математика", start_time=next Monday 09:00+03:00, end_time=next Monday 10:30+03:00,
    recurrence=["RRULE:FREQ=WEEKLY;BYDAY=MO"]
- If same subject appears in multiple cells (different days/times) → create ONE event PER cell (separate entries).

CRITICAL RULES FOR WEEKLY SCHEDULES (text-list format):
- If the input is a text list organized by days of the week (Mon, Tue... or Пн, Вт...) — treat EVERY class/event as a WEEKLY recurring event.
- Each unique class on a given day = one event with RRULE for that weekday.
- Use the NEXT occurrence of that weekday from today as start_time.

RECURRING EVENTS from text:
- "every Monday, Thursday, Saturday" → ["RRULE:FREQ=WEEKLY;BYDAY=MO,TH,SA"]
- "every day" → ["RRULE:FREQ=DAILY"]
- One-time events → recurrence: null

Return ONLY valid JSON (no markdown, no prose):
{{
  "events": [
    {{
      "title": "string",
      "description": "string or null",
      "location": "room/location or null",
      "start_time": "ISO-8601 with +03:00 offset",
      "end_time": "ISO-8601 with +03:00 offset or null",
      "recurrence": ["RRULE:FREQ=WEEKLY;BYDAY=MO"] or null
    }}
  ],
  "confidence": 0.0-1.0,
  "raw_text": "string or null",
  "notes": "string or null"
}}
If no events found: {{"events": [], "confidence": 0.0, "raw_text": null, "notes": "No events detected."}}.
"""

# ── Model constants (CR F002-CR-001, CR F002-CR-002) ─────────────────────────
_PHOTO_MODEL = "claude-sonnet-4-6"            # FR-SC002-01: Sonnet 4.6 for vision accuracy
_TEXT_MODEL = "claude-haiku-4-5-20251001"     # cost-efficient for text/voice extraction
_PHOTO_MAX_TOKENS = 8192                        # NFR-SC002-01: dense syllabi need headroom
_TEXT_MAX_TOKENS = 4096                         # unchanged


class AIService:
    def __init__(self) -> None:
        self._anthropic = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
        self._groq = groq.AsyncGroq(api_key=settings.groq_api_key)

    async def process(
        self,
        input_type: Literal["photo", "voice", "text"],
        content: str,
    ) -> list[ParsedEventSchema]:
        """
        Entry point. content is base64-encoded bytes for photo/voice,
        or a plain string for text.
        Returns a validated list of ParsedEventSchema.
        """
        if input_type == "photo":
            result = await self._process_photo(content)
        elif input_type == "voice":
            result = await self._process_voice(content)
        else:
            result = await self._process_text(content)

        return result.events

    # ── Photo (claude-3-5-sonnet-20241022) ────────────────────────────────────

    async def _process_photo(self, base64_image: str) -> AIExtractionResultSchema:
        """
        SC002 photo path.

        CR F002-CR-001 changes applied here:
          - FR-SC002-01: model = _PHOTO_MODEL (Sonnet)
          - FR-SC002-02: media_type auto-detected via _detect_media_type()
          - FR-SC002-04: one retry on AIParsingException with corrective instruction
          - NFR-SC002-01: max_tokens = _PHOTO_MAX_TOKENS (8192)
        """
        try:
            from datetime import datetime, timezone, timedelta
            tz_moscow = timezone(timedelta(hours=3))
            now = datetime.now(tz_moscow)
            system = _EXTRACTION_SYSTEM_PROMPT.format(
                now=now.strftime("%Y-%m-%d %H:%M"),
                today=now.strftime("%Y-%m-%d"),
                weekday=now.strftime("%A"),
                year=now.year,
            )

            # FR-SC002-02: detect actual image format from magic bytes
            image_bytes = base64.b64decode(base64_image)
            media_type = self._detect_media_type(image_bytes)

            def _build_messages(instruction: str) -> list:
                return [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": media_type,
                                    "data": base64_image,
                                },
                            },
                            {"type": "text", "text": instruction},
                        ],
                    }
                ]

            _PHOTO_USER_INSTRUCTION = (
                "Extract ALL calendar events from this image.\n\n"
                "If this image is a grid/table timetable (rows = times, columns = days of week): "
                "scan EVERY cell. For each non-empty cell, combine its row time and column day "
                "to create a separate weekly recurring event. Do not skip any cell."
            )
            response = await self._anthropic.messages.create(
                model=_PHOTO_MODEL,
                max_tokens=_PHOTO_MAX_TOKENS,
                system=system,
                messages=_build_messages(_PHOTO_USER_INSTRUCTION),
            )
            raw_json = response.content[0].text

            try:
                return self._parse_llm_output(raw_json)
            except AIParsingException:
                # FR-SC002-04: one retry with explicit JSON-only instruction
                logger.warning("Photo parse failed on first attempt — retrying with corrective instruction")
                retry_response = await self._anthropic.messages.create(
                    model=_PHOTO_MODEL,
                    max_tokens=_PHOTO_MAX_TOKENS,
                    system=system,
                    messages=_build_messages(
                        "Extract ALL calendar events from this image. "
                        "If this is a grid/table timetable, scan every cell and combine row time + column day.\n\n"
                        "IMPORTANT: Return ONLY the raw JSON object. No markdown. No code blocks."
                    ),
                )
                raw_json_retry = retry_response.content[0].text
                return self._parse_llm_output(raw_json_retry)

        except AIParsingException:
            raise
        except Exception as exc:
            logger.exception("Claude photo parsing failed")
            raise AIParsingException(str(exc)) from exc

    # ── Voice (Groq whisper-large-v3 → claude-3-haiku) ────────────────────────

    async def _process_voice(self, base64_audio: str) -> AIExtractionResultSchema:
        """SC003 voice path. Unchanged by CR F002-CR-001."""
        try:
            audio_bytes = base64.b64decode(base64_audio)
            transcript = await self._transcribe_audio(audio_bytes)
            return await self._extract_from_text(transcript)
        except AIParsingException:
            raise
        except Exception as exc:
            logger.exception("Voice processing failed")
            raise AIParsingException(str(exc)) from exc

    async def _transcribe_audio(self, audio_bytes: bytes) -> str:
        import io
        audio_file = io.BytesIO(audio_bytes)
        audio_file.name = "voice.ogg"
        response = await self._groq.audio.transcriptions.create(
            model="whisper-large-v3",
            file=audio_file,
            response_format="text",
        )
        return str(response)

    # ── Text (claude-3-haiku-20240307) ────────────────────────────────────────

    async def _process_text(self, text: str) -> AIExtractionResultSchema:
        """Text path. Unchanged by CR F002-CR-001."""
        try:
            return await self._extract_from_text(text)
        except AIParsingException:
            raise
        except Exception as exc:
            logger.exception("Text processing failed")
            raise AIParsingException(str(exc)) from exc

    async def _extract_from_text(self, text: str) -> AIExtractionResultSchema:
        from datetime import datetime, timezone, timedelta
        tz_moscow = timezone(timedelta(hours=3))
        now = datetime.now(tz_moscow)
        system = _EXTRACTION_SYSTEM_PROMPT.format(
            now=now.strftime("%Y-%m-%d %H:%M"),
            today=now.strftime("%Y-%m-%d"),
            weekday=now.strftime("%A"),
            year=now.year,
        )
        response = await self._anthropic.messages.create(
            model=_TEXT_MODEL,
            max_tokens=_TEXT_MAX_TOKENS,
            system=system,
            messages=[{"role": "user", "content": text}],
        )
        raw_json = response.content[0].text
        return self._parse_llm_output(raw_json)

    # ── Shared helpers ────────────────────────────────────────────────────────

    @staticmethod
    def _detect_media_type(image_bytes: bytes) -> str:
        """
        FR-SC002-02: Detect image MIME type from magic bytes.

        Supported signatures:
          JPEG  — FF D8 FF
          PNG   — 89 50 4E 47 0D 0A 1A 0A  (\\x89PNG\\r\\n\\x1a\\n)
          WEBP  — 52 49 46 46 ?? ?? ?? ?? 57 45 42 50  (RIFF....WEBP)
        Falls back to image/jpeg for unrecognised formats.
        """
        if image_bytes[:3] == b"\xff\xd8\xff":
            return "image/jpeg"
        if image_bytes[:8] == b"\x89PNG\r\n\x1a\n":
            return "image/png"
        if image_bytes[:4] == b"RIFF" and image_bytes[8:12] == b"WEBP":
            return "image/webp"
        return "image/jpeg"

    @staticmethod
    def _parse_llm_output(raw_json: str) -> AIExtractionResultSchema:
        """
        Parse and validate LLM JSON output.

        FR-SC002-03: Strips markdown code fences (```json ... ```) before
        parsing, so that more capable models wrapping their output in fences
        do not cause a JSONDecodeError.
        Only strips when fences are actually present — clean JSON is unaffected.
        """
        try:
            stripped = raw_json.strip()
            if stripped.startswith("```"):
                lines = stripped.split("\n")
                # Drop opening fence line (```json or ```) and closing fence line (```)
                inner = lines[1:-1] if lines[-1].strip() == "```" else lines[1:]
                stripped = "\n".join(inner)
            data = json.loads(stripped)
            return AIExtractionResultSchema.model_validate(data)
        except Exception as exc:
            raise AIParsingException(f"LLM returned invalid JSON: {exc}") from exc
