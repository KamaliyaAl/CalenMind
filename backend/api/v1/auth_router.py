"""
AuthRouter — FastAPI endpoints for Google OAuth 2.0 flow.

## Traceability
Feature: F001 — Google OAuth Authentication
Scenarios: SC001

## Business context
Two endpoints handle the full OAuth dance:
  GET /auth/login?telegram_id=…  → returns the Google consent URL
  GET /auth/callback              → Google redirects here with code & state
After callback, the user is marked as connected and the bot sends a welcome message.
"""

import logging

import httpx
from fastapi import APIRouter, Depends, Query
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.config import settings
from backend.core.database import get_db
from backend.repository.token_repository import TokenRepository
from backend.repository.user_repository import UserRepository
from backend.schema.user_schema import UserResponseSchema
from backend.service.auth_service import AuthService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])

_SUCCESS_MESSAGE = (
    "🎉 <b>Great! You're all set!</b>\n\n"
    "Your Google Calendar is now connected.\n\n"
    "Just write me your plans and I'll add them to your calendar. For example:\n"
    "• <i>Meeting with Anna tomorrow at 3 PM</i>\n"
    "• <i>Gym every Monday and Wednesday at 7 AM</i>\n"
    "• <i>Doctor appointment on Friday at 11:00</i>\n\n"
    "You can also send a <b>photo</b> of a schedule or a <b>voice note</b> 📸🎙️"
)


def _get_auth_service(db: AsyncSession = Depends(get_db)) -> AuthService:
    return AuthService(
        user_repo=UserRepository(db),
        token_repo=TokenRepository(db),
    )


async def _notify_telegram(telegram_id: int, text: str) -> None:
    """Send a message to the user via Telegram Bot API."""
    url = f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage"
    keyboard = {
        "inline_keyboard": [[
            {"text": "🚪 Exit", "callback_data": f"exit_account_{telegram_id}"},
            {"text": "🔄 Switch account", "callback_data": f"disconnect_{telegram_id}"},
        ]]
    }
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            await client.post(url, json={
                "chat_id": telegram_id,
                "text": text,
                "parse_mode": "HTML",
                "reply_markup": keyboard,
            })
    except Exception:
        logger.exception("Failed to send Telegram notification to %s", telegram_id)


@router.get("/login")
async def login(
    telegram_id: int = Query(..., description="Telegram user ID"),
    service: AuthService = Depends(_get_auth_service),
) -> JSONResponse:
    """Returns a Google OAuth consent URL for the given Telegram user."""
    url = await service.get_authorization_url(telegram_id)
    return JSONResponse({"auth_url": url})


@router.get("/callback")
async def callback(
    code: str = Query(...),
    state: str = Query(..., description="Encodes telegram_id"),
    service: AuthService = Depends(_get_auth_service),
) -> HTMLResponse:
    """
    Google redirects here after consent. Exchanges code for tokens,
    stores encrypted, marks user connected, and notifies user in Telegram.
    """
    user = await service.handle_callback(code=code, state=state)
    await _notify_telegram(user.telegram_id, _SUCCESS_MESSAGE)

    html = """
    <html><body style="font-family:sans-serif;text-align:center;padding:60px">
      <h2>✅ Google Calendar Connected!</h2>
      <p>You can close this tab and return to Telegram.</p>
    </body></html>
    """
    return HTMLResponse(content=html)


@router.post("/disconnect")
async def disconnect(
    telegram_id: int = Query(...),
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """Remove stored OAuth tokens and mark user as disconnected."""
    user_repo = UserRepository(db)
    token_repo = TokenRepository(db)

    user = await user_repo.get_by_telegram_id(telegram_id)
    if user:
        token = await token_repo.get_by_user_id(user.id)
        if token:
            await token_repo.delete(token)
        user.is_google_connected = False
        user.google_email = None
        await user_repo.update(user)

    return JSONResponse({"status": "disconnected"})


@router.get("/success", response_model=UserResponseSchema)
async def auth_success(
    telegram_id: int = Query(...),
    db: AsyncSession = Depends(get_db),
) -> UserResponseSchema:
    """Confirmation endpoint — returns the connected user profile."""
    user_repo = UserRepository(db)
    user = await user_repo.get_by_telegram_id(telegram_id)
    return UserResponseSchema.model_validate(user)
