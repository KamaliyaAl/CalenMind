"""
AIService — Multimodal AI orchestration: routes photo/voice/text inputs
to the appropriate LLM and returns validated ParsedEventSchema objects.

## Traceability
Feature: F002 — Multimodal Input Processing
Scenarios: SC002, SC003

## Business context
Routing strategy from tech_research.md:
  - Photo  → Claude 3.5 Sonnet (best table/syllabus parsing)
  - Voice  → OpenAI Whisper (STT) → GPT-4o-mini (entity extraction)
  - Text   → GPT-4o-mini (fast, cost-efficient for simple text)

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

CRITICAL RULES FOR WEEKLY SCHEDULES (photos/tables with days of week):
- If the input is a timetable/schedule organized by days of the week (Mon, Tue, Wed... or Пн, Вт, Ср...) — treat EVERY class/event as a WEEKLY recurring event.
- Each unique class on a given day = one event with RRULE for that weekday.
- Use the NEXT occurrence of that weekday from today as start_time.
- BYDAY codes: MO=Monday, TU=Tuesday, WE=Wednesday, TH=Thursday, FR=Friday, SA=Saturday, SU=Sunday
- Example: "Math on Monday 9:00" → start_time = next Monday at 09:00+03:00, recurrence = ["RRULE:FREQ=WEEKLY;BYDAY=MO"]
- If same subject appears on multiple days → create ONE event per day (separate entries).

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

    # ── Photo (Claude 3.5 Sonnet) ─────────────────────────────────────────────

    async def _process_photo(self, base64_image: str) -> AIExtractionResultSchema:
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
            response = await self._anthropic.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=4096,
                system=system,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": "image/jpeg",
                                    "data": base64_image,
                                },
                            },
                            {"type": "text", "text": "Extract all calendar events from this image."},
                        ],
                    }
                ],
            )
            raw_json = response.content[0].text
            return self._parse_llm_output(raw_json)
        except Exception as exc:
            logger.exception("Claude photo parsing failed")
            raise AIParsingException(str(exc)) from exc

    # ── Voice (Whisper → GPT-4o-mini) ─────────────────────────────────────────

    async def _process_voice(self, base64_audio: str) -> AIExtractionResultSchema:
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

    # ── Text (Claude 3.5 Sonnet) ──────────────────────────────────────────────

    async def _process_text(self, text: str) -> AIExtractionResultSchema:
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
            model="claude-3-haiku-20240307",
            max_tokens=4096,
            system=system,
            messages=[{"role": "user", "content": text}],
        )
        raw_json = response.content[0].text
        return self._parse_llm_output(raw_json)

    # ── Shared parser ─────────────────────────────────────────────────────────

    @staticmethod
    def _parse_llm_output(raw_json: str) -> AIExtractionResultSchema:
        try:
            data = json.loads(raw_json)
            return AIExtractionResultSchema.model_validate(data)
        except Exception as exc:
            raise AIParsingException(f"LLM returned invalid JSON: {exc}") from exc
