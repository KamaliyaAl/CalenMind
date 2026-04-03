"""
ProcessClient — Bot-side API client for the multimodal processing endpoint.

## Traceability
Feature: F002 — Multimodal Input Processing
Scenarios: SC002, SC003

## Business context
Downloads Telegram file bytes, base64-encodes them, and POSTs to
POST /api/v1/process. The backend handles all AI and calendar logic.
"""

import base64
from typing import Literal

import httpx

from bot.service.api.base_client import BaseClient


class ProcessClient(BaseClient):
    async def process_photo(self, telegram_id: int, file_bytes: bytes) -> dict:
        """Send a photo to the backend for AI extraction."""
        return await self._post(
            "/api/v1/process",
            json={
                "telegram_id": telegram_id,
                "input_type": "photo",
                "content": base64.b64encode(file_bytes).decode(),
                "filename": "photo.jpg",
            },
        )

    async def process_voice(self, telegram_id: int, file_bytes: bytes) -> dict:
        """Send a voice note to the backend for transcription + extraction."""
        return await self._post(
            "/api/v1/process",
            json={
                "telegram_id": telegram_id,
                "input_type": "voice",
                "content": base64.b64encode(file_bytes).decode(),
                "filename": "voice.ogg",
            },
        )

    async def process_text(self, telegram_id: int, text: str) -> dict:
        """Send a plain text message to the backend for extraction."""
        return await self._post(
            "/api/v1/process",
            json={
                "telegram_id": telegram_id,
                "input_type": "text",
                "content": text,
                "filename": None,
            },
        )

    @staticmethod
    async def download_file(bot, file_id: str) -> bytes:
        """Download a Telegram file by file_id and return raw bytes."""
        file = await bot.get_file(file_id)
        file_path = file.file_path
        url = f"https://api.telegram.org/file/bot{bot.token}/{file_path}"
        async with httpx.AsyncClient() as client:
            response = await client.get(url)
            response.raise_for_status()
            return response.content
