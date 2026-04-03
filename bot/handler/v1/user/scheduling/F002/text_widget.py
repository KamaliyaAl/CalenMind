"""
Widget: Process plain text input.

## Traceability
Feature: F002 — Multimodal Input Processing
Scenarios: SC002, SC003

## Business context
Handles free-text event descriptions (e.g. "Dentist appointment on Friday at 3pm").
Routes to the same ANSWER_REGISTRY as photo/voice widgets.
Filters out command messages to avoid intercepting /start etc.
"""

from typing import Any

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from bot.core.vocab import Vocab
from bot.handler.v1.user.scheduling.F002.photo_widget import ANSWER_REGISTRY
from bot.node.base_code import BaseCode
from bot.node.base_trigger import BaseTrigger
from bot.service.api.base_client import AuthNotConnectedError, BackendHTTPError, FreemiumLimitError
from bot.service.api.process_client import ProcessClient

router = Router(name="F002_text")


# ── Trigger ───────────────────────────────────────────────────────────────────

class TextTrigger(BaseTrigger):
    async def run(self, event: Message, state: FSMContext) -> dict[str, Any]:
        return {
            "telegram_id": event.from_user.id,
            "text": event.text,
        }


# ── Code ──────────────────────────────────────────────────────────────────────

class TextProcessCode(BaseCode):
    async def run(self, trigger_data: dict[str, Any], state: FSMContext) -> dict[str, Any]:
        client = ProcessClient()
        try:
            response = await client.process_text(
                telegram_id=trigger_data["telegram_id"],
                text=trigger_data["text"],
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


# ── Widget ────────────────────────────────────────────────────────────────────

@router.message(F.text & ~F.text.startswith("/"))
async def handle_text_input(message: Message, state: FSMContext) -> None:
    await message.answer(Vocab.PROCESSING_TEXT)

    trigger = TextTrigger()
    trigger_data = await trigger.run(message, state)

    code = TextProcessCode()
    code_result = await code.run(trigger_data, state)

    answer = ANSWER_REGISTRY[code_result["answer_name"]]
    await answer.run(event=message, user_lang="en", data=code_result["data"])
