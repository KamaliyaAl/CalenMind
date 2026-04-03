"""
Widget: Process schedule photo.

## Traceability
Feature: F002 — Multimodal Input Processing
Scenarios: SC002

## Business context
Handles the SC002 flow: user sends a photo → bot downloads it, POSTs
base64-encoded bytes to the backend, receives a list of events, and renders
a formatted confirmation message. Freemium errors (SC004) trigger a payment
prompt via the FreemiumLimitAnswer.
"""

from datetime import datetime
from typing import Any

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from bot.core.loader import bot
from bot.core.vocab import Vocab
from bot.node.base_answer import BaseAnswer
from bot.node.base_code import BaseCode
from bot.node.base_trigger import BaseTrigger
from bot.service.api.base_client import AuthNotConnectedError, FreemiumLimitError, BackendHTTPError
from bot.service.api.process_client import ProcessClient

router = Router(name="F002_photo")


# ── Trigger ───────────────────────────────────────────────────────────────────

class PhotoTrigger(BaseTrigger):
    async def run(self, event: Message, state: FSMContext) -> dict[str, Any]:
        photo = event.photo[-1]  # highest resolution
        return {
            "telegram_id": event.from_user.id,
            "file_id": photo.file_id,
        }


# ── Code ──────────────────────────────────────────────────────────────────────

class PhotoProcessCode(BaseCode):
    async def run(self, trigger_data: dict[str, Any], state: FSMContext) -> dict[str, Any]:
        client = ProcessClient()
        try:
            file_bytes = await ProcessClient.download_file(bot, trigger_data["file_id"])
            response = await client.process_photo(
                telegram_id=trigger_data["telegram_id"],
                file_bytes=file_bytes,
            )
            return {"answer_name": "events_synced", "data": {"response": response}}
        except FreemiumLimitError as exc:
            return {"answer_name": "freemium_limit", "data": {"message": exc.message}}
        except AuthNotConnectedError:
            return {"answer_name": "auth_not_connected", "data": {}}
        except BackendHTTPError:
            return {"answer_name": "parsing_error", "data": {}}
        finally:
            await client.close()


# ── Answers ───────────────────────────────────────────────────────────────────

def _to_local(start_time_str: str) -> str:
    """Display time in the timezone it arrived with (preserving the original offset)."""
    try:
        parsed = datetime.fromisoformat(start_time_str)
        return parsed.strftime("%Y-%m-%d %H:%M")
    except Exception:
        return start_time_str[:16].replace("T", " ")


class EventsSyncedAnswer(BaseAnswer):
    async def run(self, event: Message, user_lang: str, data: dict[str, Any]) -> None:
        response = data["response"]
        events = response.get("events", [])
        event_lines = "\n".join(
            Vocab.EVENT_LINE.format(
                title=e["title"],
                start_time=_to_local(e["start_time"]),
            )
            for e in events
        )
        await event.answer(
            Vocab.EVENTS_CREATED.format(count=len(events), event_list=event_lines or "—")
        )


class FreemiumLimitAnswer(BaseAnswer):
    async def run(self, event: Message, user_lang: str, data: dict[str, Any]) -> None:
        from bot.core.config import bot_settings
        await event.answer(Vocab.FREEMIUM_LIMIT.format(limit=bot_settings.free_monthly_limit))


class AuthNotConnectedAnswer(BaseAnswer):
    async def run(self, event: Message, user_lang: str, data: dict[str, Any]) -> None:
        await event.answer(Vocab.AUTH_NOT_CONNECTED)


class ParsingErrorAnswer(BaseAnswer):
    async def run(self, event: Message, user_lang: str, data: dict[str, Any]) -> None:
        await event.answer(Vocab.PARSING_ERROR)


# ── Registry & Widget ─────────────────────────────────────────────────────────

ANSWER_REGISTRY: dict[str, BaseAnswer] = {
    "events_synced": EventsSyncedAnswer(),
    "freemium_limit": FreemiumLimitAnswer(),
    "auth_not_connected": AuthNotConnectedAnswer(),
    "parsing_error": ParsingErrorAnswer(),
}


@router.message(F.photo)
async def handle_photo_input(message: Message, state: FSMContext) -> None:
    await message.answer(Vocab.PROCESSING_PHOTO)
    await bot.send_chat_action(message.chat.id, "typing")

    trigger = PhotoTrigger()
    trigger_data = await trigger.run(message, state)

    code = PhotoProcessCode()
    code_result = await code.run(trigger_data, state)

    answer = ANSWER_REGISTRY[code_result["answer_name"]]
    await answer.run(event=message, user_lang="en", data=code_result["data"])
