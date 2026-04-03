"""
TokenRepository — Encrypted storage and retrieval of Google OAuth tokens.

## Traceability
Feature: F001 — Google OAuth Authentication
Scenarios: SC001

## Business context
This repository is the only place in the codebase that calls encrypt/decrypt.
Service layer always receives and passes plain-text token values; encryption
is an implementation detail of persistence, satisfying the acceptance criterion
of no plain-text OAuth credentials in the database.
"""

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.security import decrypt_token, encrypt_token
from backend.model.token_model import TokenModel
from backend.repository.base_repository import BaseRepository


class TokenRepository(BaseRepository[TokenModel]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(TokenModel, session)

    async def get_by_user_id(self, user_id: str) -> TokenModel | None:
        result = await self._session.execute(
            select(TokenModel).where(TokenModel.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def upsert_tokens(
        self,
        user_id: str,
        access_token: str,
        refresh_token: str,
        expiry: datetime | None,
        scopes: str | None,
    ) -> TokenModel:
        """Create or replace the token record for a user (plain-text input)."""
        token = await self.get_by_user_id(user_id)

        encrypted_access = encrypt_token(access_token)
        encrypted_refresh = encrypt_token(refresh_token)

        if token:
            token.encrypted_access_token = encrypted_access
            token.encrypted_refresh_token = encrypted_refresh
            token.token_expiry = expiry
            token.scopes = scopes
            return await self.update(token)

        token = TokenModel(
            user_id=user_id,
            encrypted_access_token=encrypted_access,
            encrypted_refresh_token=encrypted_refresh,
            token_expiry=expiry,
            scopes=scopes,
        )
        return await self.create(token)

    async def get_plain_tokens(self, user_id: str) -> dict[str, str] | None:
        """Return decrypted access/refresh tokens, or None if not found."""
        token = await self.get_by_user_id(user_id)
        if not token:
            return None
        return {
            "access_token": decrypt_token(token.encrypted_access_token),
            "refresh_token": decrypt_token(token.encrypted_refresh_token),
            "expiry": token.token_expiry.isoformat() if token.token_expiry else None,
            "scopes": token.scopes,
        }
