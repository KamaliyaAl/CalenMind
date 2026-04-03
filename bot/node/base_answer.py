"""
BaseAnswer — Abstract base for the third stage of a Widget (response rendering).

## Traceability
Feature: F001, F002 — All bot features
Scenarios: SC001, SC002, SC003

## Business context
The Answer stage is the only place that sends a Telegram message. It
receives the code_result data and formats it using strings from Vocab.
Keeping rendering isolated makes the Code and Trigger stages unit-testable
without a real Telegram connection.
"""

from abc import ABC, abstractmethod
from typing import Any

from aiogram.types import Message


class BaseAnswer(ABC):
    """
    Renders a Telegram reply from code_result data.

    Usage in a widget handler:
        answer = ANSWER_REGISTRY[code_result["answer_name"]]
        await answer.run(event=message, user_lang="en", data=code_result["data"])
    """

    @abstractmethod
    async def run(self, event: Message, user_lang: str, data: dict[str, Any]) -> None:
        """Send the appropriate Telegram message(s) based on data."""
