"""
BaseTrigger — Abstract base for the first stage of a Widget (input capture).

## Traceability
Feature: F001, F002 — All bot features
Scenarios: SC001, SC002, SC003

## Business context
A Trigger's sole responsibility is to extract the raw input data from the
Telegram Message/CallbackQuery and return a normalised dict for the Code
stage. It must NOT call the backend or modify state beyond FSM data capture.
"""

from abc import ABC, abstractmethod
from typing import Any

from aiogram.fsm.context import FSMContext
from aiogram.types import Message


class BaseTrigger(ABC):
    """
    Captures raw input from a Telegram event and returns structured trigger_data.

    Usage in a widget handler:
        trigger = PhotoTrigger()
        trigger_data = await trigger.run(message, state)
    """

    @abstractmethod
    async def run(self, event: Message, state: FSMContext) -> dict[str, Any]:
        """
        Extract and return trigger data from the incoming event.

        Returns:
            dict with at minimum: {"telegram_id": int, "input_type": str, ...}
        """
