"""
Conftest — Shared fixtures for F002 (Multimodal Input Processing) tests.

## Traceability
Feature: F002 — Multimodal Input Processing
Scenarios: SC002, SC003
"""

import base64

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from backend.core.database import Base
from backend.model.event_model import EventModel  # noqa: F401
from backend.model.token_model import TokenModel  # noqa: F401
from backend.model.user_model import UserModel  # noqa: F401

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture(scope="function")
async def db_session() -> AsyncSession:
    engine = create_async_engine(TEST_DB_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        yield session
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture
def sample_base64_image() -> str:
    """1x1 white JPEG as base64 — minimal valid image for AI mock tests."""
    tiny_jpeg = (
        b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00"
        b"\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t"
        b"\x08\n\x0c\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a"
        b"\x1f\x1e\x1d\x1a\x1c\x1c $.' \",#\x1c\x1c(7),\x01\x01\x01\x01"
        b"\xff\xc0\x00\x0b\x08\x00\x01\x00\x01\x01\x01\x11\x00\xff\xc4"
        b"\x00\x1f\x00\x00\x01\x05\x01\x01\x01\x01\x01\x01\x00\x00\x00"
        b"\x00\x00\x00\x00\x00\x01\x02\x03\x04\x05\x06\x07\x08\t\n\x0b"
        b"\xff\xda\x00\x08\x01\x01\x00\x00?\x00\xfb\xff\xd9"
    )
    return base64.b64encode(tiny_jpeg).decode()


@pytest.fixture
def sample_ai_extraction_result() -> dict:
    return {
        "events": [
            {
                "title": "Math Lecture",
                "description": "Chapter 3 — Calculus",
                "location": "Room 201",
                "start_time": "2026-04-10T09:00:00+00:00",
                "end_time": "2026-04-10T11:00:00+00:00",
            }
        ],
        "confidence": 0.95,
        "raw_text": "Math Lecture, Room 201, April 10 9:00-11:00",
        "notes": None,
    }
