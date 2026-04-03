"""
EventSchema — Pydantic models for event creation, response, and calendar sync.

## Traceability
Feature: F002 — Multimodal Input Processing
Scenarios: SC002, SC003

## Business context
EventCreateSchema is what the API receives from the bot after a user submits
input. EventResponseSchema is what the API returns. The optional google_event_id
signals whether a Calendar sync has occurred.
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class EventCreateSchema(BaseModel):
    """Payload for persisting a parsed event."""

    title: str = Field(..., max_length=255)
    description: str | None = None
    location: str | None = None
    start_time: datetime
    end_time: datetime | None = None
    input_type: Literal["photo", "voice", "text"]
    raw_ai_output: dict | None = None


class EventResponseSchema(BaseModel):
    """API response for a single calendar event."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    description: str | None
    location: str | None
    start_time: datetime
    end_time: datetime | None
    input_type: str
    google_event_id: str | None
    is_synced: bool
    created_at: datetime


class ProcessInputRequestSchema(BaseModel):
    """
    Inbound request to POST /api/v1/process.

    The bot sends:
    - telegram_id to identify the user
    - input_type to route AI logic
    - content: base64-encoded file bytes (photo/voice) or raw text string
    """

    telegram_id: int
    input_type: Literal["photo", "voice", "text"]
    content: str = Field(..., description="Base64-encoded bytes for photo/voice, raw string for text")
    filename: str | None = Field(None, description="Original filename hint (for MIME detection)")


class ProcessInputResponseSchema(BaseModel):
    """Response from POST /api/v1/process."""

    events: list[EventResponseSchema]
    message: str = "Events processed successfully."
