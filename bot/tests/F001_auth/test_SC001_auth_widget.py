"""
Test SC001 — Auth Widget (Bot side).

## Traceability
Feature: F001 — Google OAuth Authentication
Scenario: SC001 — Successful Auth

## BDD
Given: A Telegram user with telegram_id=123456 sends /start.
When:  The AuthCode calls the backend AuthClient.
Then:  If not connected → bot replies with an inline keyboard containing the auth URL.
       If already connected → bot replies with AUTH_ALREADY_CONNECTED message.
"""

import pytest
from unittest.mock import AsyncMock, patch

from bot.handler.v1.user.auth.F001.auth_widget import (
    AlreadyConnectedAnswer,
    AuthCode,
    AuthTrigger,
    SendAuthUrlAnswer,
)
from bot.core.vocab import Vocab


@pytest.mark.asyncio
async def test_SC001_trigger_extracts_telegram_id(mock_message, mock_state):
    """AuthTrigger must extract the telegram_id from the message."""
    trigger = AuthTrigger()
    result = await trigger.run(mock_message, mock_state)
    assert result["telegram_id"] == 123456


@pytest.mark.asyncio
async def test_SC001_code_returns_auth_url_for_new_user(mock_message, mock_state):
    """AuthCode must return 'send_auth_url' for a user not yet connected."""
    with patch("bot.handler.v1.user.auth.F001.auth_widget.AuthClient") as MockClient:
        instance = MockClient.return_value
        instance.get_user_status = AsyncMock(return_value={"is_google_connected": False})
        instance.get_auth_url = AsyncMock(return_value="https://accounts.google.com/auth?state=123456")
        instance.close = AsyncMock()

        code = AuthCode()
        result = await code.run({"telegram_id": 123456}, mock_state)

    assert result["answer_name"] == "send_auth_url"
    assert "auth_url" in result["data"]
    assert "accounts.google.com" in result["data"]["auth_url"]


@pytest.mark.asyncio
async def test_SC001_code_returns_already_connected(mock_message, mock_state):
    """AuthCode must return 'already_connected' if user is connected."""
    with patch("bot.handler.v1.user.auth.F001.auth_widget.AuthClient") as MockClient:
        instance = MockClient.return_value
        instance.get_user_status = AsyncMock(return_value={"is_google_connected": True})
        instance.close = AsyncMock()

        code = AuthCode()
        result = await code.run({"telegram_id": 123456}, mock_state)

    assert result["answer_name"] == "already_connected"


@pytest.mark.asyncio
async def test_SC001_send_auth_url_answer_sends_keyboard(mock_message, mock_state):
    """SendAuthUrlAnswer must call message.answer with an inline keyboard."""
    answer = SendAuthUrlAnswer()
    await answer.run(
        event=mock_message,
        user_lang="en",
        data={"auth_url": "https://accounts.google.com/auth"},
    )
    mock_message.answer.assert_called_once()
    call_kwargs = mock_message.answer.call_args
    assert Vocab.AUTH_CONNECT_BUTTON in str(call_kwargs)


@pytest.mark.asyncio
async def test_SC001_already_connected_answer_sends_correct_text(mock_message, mock_state):
    """AlreadyConnectedAnswer must send AUTH_ALREADY_CONNECTED text with inline keyboard."""
    answer = AlreadyConnectedAnswer()
    await answer.run(event=mock_message, user_lang="en", data={})
    mock_message.answer.assert_called_once()
    # Text is passed as the first positional argument; reply_markup is a kwarg
    text_arg = mock_message.answer.call_args[0][0]
    assert text_arg == Vocab.AUTH_ALREADY_CONNECTED
    # Keyboard must also be present (Stay / Switch buttons)
    call_kwargs = mock_message.answer.call_args[1]
    assert "reply_markup" in call_kwargs
