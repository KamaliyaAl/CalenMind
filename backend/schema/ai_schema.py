"""
AISchema — Pydantic models for structured AI output validation.

## Traceability
Feature: F002 — Multimodal Input Processing
Scenarios: SC002, SC003

## Business context
The AI service instructs LLMs to return JSON matching ParsedEventSchema.
Using Pydantic validation here ensures that any malformed LLM output is
caught before it reaches the repository layer, providing the >90% accuracy
acceptance criterion with a hard data contract.
"""

from datetime import datetime

from pydantic import BaseModel, Field, field_validator


class ParsedEventSchema(BaseModel):
    """A single event as extracted by the AI from any input modality."""

    title: str = Field(..., max_length=255, description="Short event title")
    description: str | None = Field(None, description="Optional event details")
    location: str | None = Field(None, description="Physical or virtual location")
    start_time: datetime = Field(..., description="Event start in ISO-8601 with timezone")
    end_time: datetime | None = Field(None, description="Event end in ISO-8601 (optional)")
    recurrence: list[str] | None = Field(
        None,
        description="Google Calendar RRULE strings, e.g. ['RRULE:FREQ=WEEKLY;BYDAY=MO,TH,SA']"
    )

    @field_validator("title")
    @classmethod
    def title_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Event title must not be empty.")
        return v.strip()


class AIExtractionResultSchema(BaseModel):
    """
    Complete AI response containing one or more parsed events.

    The LLM is instructed to always return this wrapper so we can
    distinguish 'no events found' from a parsing failure.
    """

    events: list[ParsedEventSchema] = Field(default_factory=list)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    raw_text: str | None = Field(None, description="Transcript or OCR text before structuring")
    notes: str | None = Field(None, description="LLM's own notes on ambiguities")
