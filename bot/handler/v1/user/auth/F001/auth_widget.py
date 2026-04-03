"""
Widget: Google OAuth Authentication — /start and /status commands.

## Traceability
Feature: F001 — Google OAuth Authentication
Scenarios: SC001

## Business context
Implements the Trigger → Code → Answer pattern for the auth flow.
The Trigger captures the telegram_id, the Code fetches the consent URL
from the backend, and the Answer renders an inline keyboard with the URL.
No DB access occurs in the bot; all state is managed by the backend.
"""

from typing import Any

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from bot.core.vocab import Vocab
from bot.node.base_answer import BaseAnswer
from bot.node.base_code import BaseCode
from bot.node.base_trigger import BaseTrigger
from bot.service.api.auth_client import AuthClient
from bot.service.api.base_client import AuthNotConnectedError, BackendHTTPError

router = Router(name="F001_auth")


# ── Trigger ───────────────────────────────────────────────────────────────────

class AuthTrigger(BaseTrigger):
    async def run(self, event: Message, state: FSMContext) -> dict[str, Any]:
        return {"telegram_id": event.from_user.id}


# ── Code ──────────────────────────────────────────────────────────────────────

class AuthCode(BaseCode):
    async def run(self, trigger_data: dict[str, Any], state: FSMContext) -> dict[str, Any]:
        client = AuthClient()
        try:
            user = await client.get_user_status(trigger_data["telegram_id"])
            if user.get("is_google_connected"):
                return {"answer_name": "already_connected", "data": {}}

            auth_url = await client.get_auth_url(trigger_data["telegram_id"])
            return {"answer_name": "send_auth_url", "data": {"auth_url": auth_url}}
        except BackendHTTPError:
            # User doesn't exist yet — generate URL for first-time registration
            auth_url = await client.get_auth_url(trigger_data["telegram_id"])
            return {"answer_name": "send_auth_url", "data": {"auth_url": auth_url}}
        finally:
            await client.close()


class StatusCode(BaseCode):
    async def run(self, trigger_data: dict[str, Any], state: FSMContext) -> dict[str, Any]:
        client = AuthClient()
        try:
            user = await client.get_user_status(trigger_data["telegram_id"])
            freemium = await client.get_freemium_status(trigger_data["telegram_id"])
            return {
                "answer_name": "status_connected" if user.get("is_google_connected") else "status_not_connected",
                "data": {"freemium": freemium, "user": user},
            }
        except AuthNotConnectedError:
            return {"answer_name": "status_not_connected", "data": {}}
        finally:
            await client.close()


# ── Answers ───────────────────────────────────────────────────────────────────

class SendAuthUrlAnswer(BaseAnswer):
    async def run(self, event: Message, user_lang: str, data: dict[str, Any]) -> None:
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[[
                InlineKeyboardButton(text=Vocab.AUTH_CONNECT_BUTTON, url=data["auth_url"])
            ]]
        )
        await event.answer(Vocab.AUTH_WELCOME, reply_markup=keyboard)


class AlreadyConnectedAnswer(BaseAnswer):
    async def run(self, event: Message, user_lang: str, data: dict[str, Any]) -> None:
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[[
                InlineKeyboardButton(
                    text=Vocab.AUTH_KEEP_BUTTON,
                    callback_data=f"keep_account_{event.from_user.id}",
                ),
                InlineKeyboardButton(
                    text=Vocab.AUTH_SWITCH_BUTTON,
                    callback_data=f"disconnect_{event.from_user.id}",
                ),
            ]]
        )
        await event.answer(Vocab.AUTH_ALREADY_CONNECTED, reply_markup=keyboard)


class StatusConnectedAnswer(BaseAnswer):
    async def run(self, event: Message, user_lang: str, data: dict[str, Any]) -> None:
        freemium = data.get("freemium", {})
        remaining = freemium.get("remaining", "?")
        text = (
            f"✅ Google Calendar connected: <b>{data['user'].get('google_email', 'unknown')}</b>\n"
            + Vocab.FREEMIUM_REMAINING.format(remaining=remaining)
        )
        await event.answer(text)


class StatusNotConnectedAnswer(BaseAnswer):
    async def run(self, event: Message, user_lang: str, data: dict[str, Any]) -> None:
        await event.answer(Vocab.AUTH_NOT_CONNECTED)


# ── Registry & Widget ─────────────────────────────────────────────────────────

ANSWER_REGISTRY: dict[str, BaseAnswer] = {
    "send_auth_url": SendAuthUrlAnswer(),
    "already_connected": AlreadyConnectedAnswer(),
    "status_connected": StatusConnectedAnswer(),
    "status_not_connected": StatusNotConnectedAnswer(),
}


@router.message(Command("start"))
async def handle_start(message: Message, state: FSMContext) -> None:
    trigger = AuthTrigger()
    trigger_data = await trigger.run(message, state)

    code = AuthCode()
    code_result = await code.run(trigger_data, state)

    answer = ANSWER_REGISTRY[code_result["answer_name"]]
    await answer.run(event=message, user_lang="en", data=code_result["data"])


@router.message(Command("status"))
async def handle_status(message: Message, state: FSMContext) -> None:
    trigger = AuthTrigger()
    trigger_data = await trigger.run(message, state)

    code = StatusCode()
    code_result = await code.run(trigger_data, state)

    answer = ANSWER_REGISTRY[code_result["answer_name"]]
    await answer.run(event=message, user_lang="en", data=code_result["data"])


@router.message(Command("disconnect"))
async def handle_disconnect(message: Message, state: FSMContext) -> None:
    client = AuthClient()
    try:
        await client.disconnect(message.from_user.id)
    finally:
        await client.close()

    auth_url = await AuthClient().get_auth_url(message.from_user.id)
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[[
            InlineKeyboardButton(text=Vocab.AUTH_CONNECT_BUTTON, url=auth_url)
        ]]
    )
    await message.answer(
        "🔌 Google Calendar disconnected.\n\nConnect a new account:",
        reply_markup=keyboard,
    )


@router.callback_query(F.data.startswith("disconnect_"))
async def handle_disconnect_callback(callback: CallbackQuery, state: FSMContext) -> None:
    telegram_id = callback.from_user.id
    client = AuthClient()
    try:
        await client.disconnect(telegram_id)
        auth_url = await client.get_auth_url(telegram_id)
    finally:
        await client.close()

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[[
            InlineKeyboardButton(text=Vocab.AUTH_CONNECT_BUTTON, url=auth_url)
        ]]
    )
    await callback.message.edit_text(
        "🔌 Disconnected. Connect a different Google account:",
        reply_markup=keyboard,
    )
    await callback.answer()


def _all_set_keyboard(telegram_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[
            InlineKeyboardButton(
                text=Vocab.AUTH_EXIT_BUTTON,
                callback_data=f"exit_account_{telegram_id}",
            ),
            InlineKeyboardButton(
                text=Vocab.AUTH_SWITCH_ACCOUNT_BUTTON,
                callback_data=f"disconnect_{telegram_id}",
            ),
        ]]
    )


@router.callback_query(F.data.startswith("keep_account_"))
async def handle_keep_account_callback(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.message.edit_text(
        Vocab.AUTH_KEEP_ACCOUNT,
        reply_markup=_all_set_keyboard(callback.from_user.id),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("exit_account_"))
async def handle_exit_account_callback(callback: CallbackQuery, state: FSMContext) -> None:
    client = AuthClient()
    try:
        await client.disconnect(callback.from_user.id)
    finally:
        await client.close()
    await callback.message.edit_text(
        "👋 You've been logged out.\n\n"
        "Your Google Calendar has been disconnected.\n"
        "Use /start to connect again."
    )
    await callback.answer()


@router.message(Command("exit"))
async def handle_exit(message: Message, state: FSMContext) -> None:
    """Disconnect Google account and confirm."""
    client = AuthClient()
    try:
        await client.disconnect(message.from_user.id)
    finally:
        await client.close()
    await message.answer(
        "👋 You've been logged out.\n\n"
        "Your Google Calendar has been disconnected.\n"
        "Use /start to connect again."
    )


@router.message(Command("switch"))
async def handle_switch(message: Message, state: FSMContext) -> None:
    """Disconnect current account and immediately offer to connect a new one."""
    client = AuthClient()
    try:
        await client.disconnect(message.from_user.id)
        auth_url = await client.get_auth_url(message.from_user.id)
    finally:
        await client.close()

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[[
            InlineKeyboardButton(text=Vocab.AUTH_CONNECT_BUTTON, url=auth_url)
        ]]
    )
    await message.answer(
        "🔄 Previous account disconnected.\n\nConnect a new Google account:",
        reply_markup=keyboard,
    )


@router.message(Command("help"))
async def handle_help(message: Message, state: FSMContext) -> None:
    await message.answer(Vocab.HELP_TEXT)
