"""
Widget: Process voice note.

## Traceability
Feature: F002 — Multimodal Input Processing
Scenarios: SC003

## Business context
Handles the SC003 flow: user sends a voice note → bot downloads the .ogg
file, POSTs base64-encoded bytes to /process?input_type=voice → backend
runs Whisper STT then GPT-4o-mini entity extraction → events are returned
and rendered. Shares Answer classes with photo_widget for DRY responses.
"""

from typing import Any

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from bot.core.loader import bot
from bot.core.vocab import Vocab
from bot.handler.v1.user.scheduling.F002.photo_widget import (
    ANSWER_REGISTRY,
    AuthNotConnectedAnswer,
    EventsSyncedAnswer,
    FreemiumLimitAnswer,
    ParsingErrorAnswer,
)
from bot.node.base_code import BaseCode
from bot.node.base_trigger import BaseTrigger
from bot.service.api.base_client import AuthNotConnectedError, BackendHTTPError, FreemiumLimitError
from bot.service.api.process_client import ProcessClient

router = Router(name="F002_voice")


# ── Trigger ───────────────────────────────────────────────────────────────────

class VoiceTrigger(BaseTrigger):
    async def run(self, event: Message, state: FSMContext) -> dict[str, Any]:
        return {
            "telegram_id": event.from_user.id,
            "file_id": event.voice.file_id,
        }


# ── Code ──────────────────────────────────────────────────────────────────────

class VoiceProcessCode(BaseCode):
    async def run(self, trigger_data: dict[str, Any], state: FSMContext) -> dict[str, Any]:
        client = ProcessClient()
        try:
            file_bytes = await ProcessClient.download_file(bot, trigger_data["file_id"])
            response = await client.process_voice(
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


# ── Widget ────────────────────────────────────────────────────────────────────

@router.message(F.voice)
async def handle_voice_input(message: Message, state: FSMContext) -> None:
    await message.answer(Vocab.PROCESSING_VOICE)

    trigger = VoiceTrigger()
    trigger_data = await trigger.run(message, state)

    code = VoiceProcessCode()
    code_result = await code.run(trigger_data, state)

    answer = ANSWER_REGISTRY[code_result["answer_name"]]
    await answer.run(event=message, user_lang="en", data=code_result["data"])
