"""
ProcessRouter — FastAPI endpoint for multimodal input processing.

## Traceability
Feature: F002 — Multimodal Input Processing, F004 — Freemium Limits
Scenarios: SC002, SC003, SC004

## Business context
POST /process is the single entry point for all user input (photo/voice/text).
Pipeline:
  1. Identify (or create) the user via telegram_id.
  2. FreemiumService checks + increments the monthly counter (F004).
  3. AIService extracts events from the input.
  4. Events are persisted to DB.
  5. CalendarService syncs each event to Google Calendar (F001 creds required).
  6. Returns the created EventResponseSchema list.
"""

import logging

from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.database import get_db
from backend.model.event_model import EventModel
from backend.repository.event_repository import EventRepository
from backend.repository.token_repository import TokenRepository
from backend.repository.user_repository import UserRepository
from backend.schema.event_schema import (
    EventResponseSchema,
    ProcessInputRequestSchema,
    ProcessInputResponseSchema,
)
from backend.service.ai_service import AIService
from backend.service.auth_service import AuthService
from backend.service.calendar_service import CalendarService
from backend.service.freemium_service import FreemiumService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/process", tags=["process"])


@router.post("", response_model=ProcessInputResponseSchema)
async def process_input(
    payload: ProcessInputRequestSchema,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
) -> ProcessInputResponseSchema:
    """
    Accepts multimodal input, runs AI extraction, persists and syncs events.
    Returns the list of created events.
    """
    user_repo = UserRepository(db)
    token_repo = TokenRepository(db)
    event_repo = EventRepository(db)
    ai_service = AIService()
    auth_service = AuthService(user_repo=user_repo, token_repo=token_repo)
    calendar_service = CalendarService()
    freemium_service = FreemiumService(user_repo=user_repo)

    # 1. Resolve user
    user, _ = await user_repo.get_or_create(
        telegram_id=payload.telegram_id,
    )

    # 2. Freemium gate — raises HTTP 402 if limit reached (SC004)
    user = await freemium_service.check_and_increment(user)

    # 3. AI extraction
    parsed_events = await ai_service.process(
        input_type=payload.input_type,
        content=payload.content,
    )

    # 4. Persist events to DB
    db_events: list[EventModel] = []
    for parsed in parsed_events:
        event = EventModel(
            user_id=user.id,
            title=parsed.title,
            description=parsed.description,
            location=parsed.location,
            start_time=parsed.start_time,
            end_time=parsed.end_time,
            input_type=payload.input_type,
            raw_ai_output=parsed.model_dump(mode="json"),
        )
        event = await event_repo.create(event)
        db_events.append(event)

    # 5. Sync to Google Calendar (non-blocking background task)
    background_tasks.add_task(
        _sync_to_calendar,
        user_id=user.id,
        db_events=db_events,
        parsed_events=parsed_events,
        auth_service=auth_service,
        calendar_service=calendar_service,
        event_repo=event_repo,
        user=user,
    )

    return ProcessInputResponseSchema(
        events=[
            EventResponseSchema.model_validate(e).model_copy(
                update={"start_time": parsed.start_time}
            )
            for e, parsed in zip(db_events, parsed_events)
        ],
        message=f"{len(db_events)} event(s) processed and queued for sync.",
    )


async def _sync_to_calendar(
    user_id,
    db_events,
    parsed_events,
    auth_service,
    calendar_service,
    event_repo,
    user,
) -> None:
    """Background task: sync each persisted event to Google Calendar."""
    try:
        credentials = await auth_service.get_credentials(user)
        for db_event, parsed in zip(db_events, parsed_events):
            google_id = await calendar_service.create_event(credentials, parsed)
            await event_repo.mark_synced(db_event, google_id)
    except Exception:
        logger.exception("Background calendar sync failed for user %s", user_id)
