"""
app.py — CalenMind AI Telegram Bot entry point.

## Traceability
Feature: F001, F002, F004 — All bot features
Scenarios: SC001, SC002, SC003, SC004

## Business context
Registers all feature routers onto the Dispatcher and starts the aiogram
polling loop. Router order matters: more specific filters (photo, voice)
are registered before the generic text router to avoid accidental routing.
"""

import asyncio
import logging

from bot.core.loader import bot, dp
from bot.handler.v1.user.auth.F001.auth_widget import router as auth_router
from bot.handler.v1.user.scheduling.F002.photo_widget import router as photo_router
from bot.handler.v1.user.scheduling.F002.voice_widget import router as voice_router
from bot.handler.v1.user.scheduling.F002.text_widget import router as text_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)

# Register routers — order: auth first, then modality-specific, text last
dp.include_router(auth_router)
dp.include_router(photo_router)
dp.include_router(voice_router)
dp.include_router(text_router)


async def main() -> None:
    logging.getLogger(__name__).info("CalenMind AI bot starting…")
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())


if __name__ == "__main__":
    asyncio.run(main())
