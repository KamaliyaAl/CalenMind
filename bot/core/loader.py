"""
Loader — Initialises the aiogram Bot and Dispatcher singletons.

## Traceability
Feature: F001, F002 — All bot features
Scenarios: SC001, SC002, SC003

## Business context
Single source of truth for the Bot and Dispatcher instances.
All handler modules import from here to avoid circular dependency
and multiple Bot object creation.
"""

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from bot.core.config import bot_settings

bot = Bot(
    token=bot_settings.telegram_bot_token,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML),
)

dp = Dispatcher(storage=MemoryStorage())
