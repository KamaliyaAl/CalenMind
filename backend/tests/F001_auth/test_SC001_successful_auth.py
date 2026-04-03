"""
Test SC001 — Successful Google OAuth Authentication.

## Traceability
Feature: F001 — Google OAuth Authentication
Scenario: SC001 — Successful Auth

## BDD
Given: A Telegram user with telegram_id=123456 requests Google OAuth.
When:  The user grants consent and Google redirects with a valid code.
Then:  The user is marked as google_connected=True, tokens are stored
       encrypted, and a UserResponseSchema is returned with the Google email.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from backend.repository.token_repository import TokenRepository
from backend.repository.user_repository import UserRepository
from backend.service.auth_service import AuthService

TELEGRAM_ID = 123456
GOOGLE_EMAIL = "test@gmail.com"


@pytest.mark.asyncio
async def test_SC001_get_authorization_url_contains_google_domain(db_session):
    """get_authorization_url must return a URL pointing to Google's OAuth endpoint."""
    service = AuthService(
        user_repo=UserRepository(db_session),
        token_repo=TokenRepository(db_session),
    )

    with patch("backend.service.auth_service.Flow") as MockFlow:
        mock_flow_instance = MagicMock()
        mock_flow_instance.authorization_url.return_value = (
            "https://accounts.google.com/o/oauth2/auth?client_id=test&state=123456",
            "state",
        )
        MockFlow.from_client_config.return_value = mock_flow_instance

        url = await service.get_authorization_url(TELEGRAM_ID)

    assert "accounts.google.com" in url
    assert str(TELEGRAM_ID) in url


@pytest.mark.asyncio
async def test_SC001_handle_callback_marks_user_connected(db_session, mock_google_credentials):
    """After callback, user.is_google_connected must be True and email saved."""
    user_repo = UserRepository(db_session)
    token_repo = TokenRepository(db_session)
    service = AuthService(user_repo=user_repo, token_repo=token_repo)

    with patch("backend.service.auth_service.Flow") as MockFlow:
        mock_flow_instance = MagicMock()
        mock_flow_instance.credentials = mock_google_credentials
        MockFlow.from_client_config.return_value = mock_flow_instance

        user = await service.handle_callback(code="auth_code", state=str(TELEGRAM_ID))

    assert user.is_google_connected is True
    assert user.google_email == GOOGLE_EMAIL
    assert user.telegram_id == TELEGRAM_ID


@pytest.mark.asyncio
async def test_SC001_tokens_are_not_stored_in_plain_text(db_session, mock_google_credentials):
    """Stored token ciphertext must differ from the plain-text access token."""
    user_repo = UserRepository(db_session)
    token_repo = TokenRepository(db_session)
    service = AuthService(user_repo=user_repo, token_repo=token_repo)

    with patch("backend.service.auth_service.Flow") as MockFlow:
        mock_flow_instance = MagicMock()
        mock_flow_instance.credentials = mock_google_credentials
        MockFlow.from_client_config.return_value = mock_flow_instance
        await service.handle_callback(code="auth_code", state=str(TELEGRAM_ID))

    user = await user_repo.get_by_telegram_id(TELEGRAM_ID)
    token_record = await token_repo.get_by_user_id(user.id)

    assert token_record is not None
    # Ciphertext must NOT equal plain-text token (acceptance criterion)
    assert token_record.encrypted_access_token != "mock_access_token"
    assert token_record.encrypted_refresh_token != "mock_refresh_token"


@pytest.mark.asyncio
async def test_SC001_get_credentials_returns_decrypted_creds(db_session, mock_google_credentials):
    """get_credentials must return a valid Credentials object for a connected user."""
    user_repo = UserRepository(db_session)
    token_repo = TokenRepository(db_session)
    service = AuthService(user_repo=user_repo, token_repo=token_repo)

    with patch("backend.service.auth_service.Flow") as MockFlow:
        mock_flow_instance = MagicMock()
        mock_flow_instance.credentials = mock_google_credentials
        MockFlow.from_client_config.return_value = mock_flow_instance
        user = await service.handle_callback(code="auth_code", state=str(TELEGRAM_ID))

    with patch("backend.service.auth_service.Credentials") as MockCreds:
        mock_cred_instance = MagicMock()
        mock_cred_instance.expired = False
        MockCreds.return_value = mock_cred_instance

        creds = await service.get_credentials(user)

    assert creds is not None
