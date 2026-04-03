"""
Conftest — Shared fixtures for F001 (Google OAuth Authentication) tests.

## Traceability
Feature: F001 — Google OAuth Authentication
Scenarios: SC001
"""

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from backend.core.database import Base
from backend.model.token_model import TokenModel  # noqa: F401 — ensure table is registered
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
def mock_google_credentials(mocker):
    """Returns a mock Credentials object for Google OAuth."""
    creds = mocker.MagicMock()
    creds.token = "mock_access_token"
    creds.refresh_token = "mock_refresh_token"
    creds.expiry = None
    creds.scopes = ["https://www.googleapis.com/auth/calendar.events"]
    creds.id_token = {"email": "test@gmail.com"}
    creds.expired = False
    return creds
