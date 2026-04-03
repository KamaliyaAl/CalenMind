"""
TokenModel — Encrypted Google OAuth 2.0 refresh and access tokens.

## Traceability
Feature: F001 — Google OAuth Authentication
Scenarios: SC001

## Business context
Acceptance criteria forbid plain-text storage of OAuth credentials.
All token fields are stored as Fernet-encrypted ciphertext via
backend.core.security. The repository layer handles encrypt/decrypt
transparently so upper layers always work with plain-text values.
"""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.core.database import Base
from backend.model.base_model import TimestampMixin, UUIDPrimaryKeyMixin


class TokenModel(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "oauth_tokens"

    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False, index=True
    )

    # Encrypted fields (Fernet ciphertext — never plain text)
    encrypted_access_token: Mapped[str] = mapped_column(Text, nullable=False)
    encrypted_refresh_token: Mapped[str] = mapped_column(Text, nullable=False)

    token_expiry: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    scopes: Mapped[str | None] = mapped_column(Text, nullable=True)  # space-separated

    # Relationship back to user
    user: Mapped["UserModel"] = relationship("UserModel", back_populates="oauth_token")  # noqa: F821

    def __repr__(self) -> str:
        return f"<TokenModel user_id={self.user_id} expiry={self.token_expiry}>"
