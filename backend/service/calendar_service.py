"""
CalendarService — Creates and manages Google Calendar events via the
Google Calendar API v3.

## Traceability
Feature: F002 — Multimodal Input Processing
Scenarios: SC002, SC003

## Business context
Takes validated ParsedEventSchema objects and a user's Google Credentials
to create events in the user's primary calendar. Returns the Google event ID
so the EventRepository can mark the local record as synced.
"""

import logging
from datetime import timezone

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from backend.core.exceptions import CalendarSyncException
from backend.schema.ai_schema import ParsedEventSchema

logger = logging.getLogger(__name__)

_CALENDAR_ID = "primary"


class CalendarService:
    async def create_event(
        self,
        credentials: Credentials,
        event: ParsedEventSchema,
    ) -> str:
        """
        Create a single event in the user's primary Google Calendar.
        Returns the Google event ID on success.
        """
        try:
            service = build("calendar", "v3", credentials=credentials, cache_discovery=False)
            body = self._build_event_body(event)
            created = service.events().insert(calendarId=_CALENDAR_ID, body=body).execute()
            google_event_id: str = created["id"]
            logger.info("Created Google Calendar event %s: %s", google_event_id, event.title)
            return google_event_id
        except HttpError as exc:
            raise CalendarSyncException(str(exc)) from exc
        except Exception as exc:
            raise CalendarSyncException(str(exc)) from exc

    async def create_events_batch(
        self,
        credentials: Credentials,
        events: list[ParsedEventSchema],
    ) -> list[str]:
        """Create multiple events; returns list of Google event IDs in order."""
        event_ids: list[str] = []
        for event in events:
            event_id = await self.create_event(credentials, event)
            event_ids.append(event_id)
        return event_ids

    @staticmethod
    def _build_event_body(event: ParsedEventSchema) -> dict:
        def _fmt(dt) -> dict:
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return {"dateTime": dt.isoformat(), "timeZone": "UTC"}

        end = event.end_time or event.start_time
        body: dict = {
            "summary": event.title,
            "start": _fmt(event.start_time),
            "end": _fmt(end),
        }
        if event.description:
            body["description"] = event.description
        if event.location:
            body["location"] = event.location
        if event.recurrence:
            body["recurrence"] = event.recurrence  # e.g. ["RRULE:FREQ=WEEKLY;BYDAY=MO,TH,SA"]
        return body
