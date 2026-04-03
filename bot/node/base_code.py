"""
BaseCode — Abstract base for the second stage of a Widget (business logic).

## Traceability
Feature: F001, F002 — All bot features
Scenarios: SC001, SC002, SC003

## Business context
The Code stage calls the backend API client and maps the response to an
answer_name key that the Answer registry resolves. It must NOT send any
Telegram messages — that is strictly the Answer's responsibility.
"""

from abc import ABC, abstractmethod
from typing import Any

from aiogram.fsm.context import FSMContext


class BaseCode(ABC):
    """
    Executes business logic (backend API call) and returns a result dict.

    The result dict MUST contain:
        - "answer_name": str  — key into the widget's ANSWER_REGISTRY
        - "data": dict        — payload forwarded to the Answer
    """

    @abstractmethod
    async def run(self, trigger_data: dict[str, Any], state: FSMContext) -> dict[str, Any]:
        """
        Process trigger_data, call backend, return:
            {"answer_name": "<key>", "data": {...}}
        """
