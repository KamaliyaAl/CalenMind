"""
Security — AES-128-CBC (Fernet) encryption for OAuth refresh tokens.

## Traceability
Feature: F001 — Google OAuth Authentication
Scenarios: SC001

## Business context
Acceptance criteria mandate that no plain-text OAuth credentials are stored
in the database. This module wraps cryptography.fernet so every repository
that touches token data calls encrypt/decrypt through a single, auditable
path. The Fernet key is derived from the application SECRET_KEY.
"""

import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken

from backend.core.config import settings


def _build_fernet() -> Fernet:
    """Derive a valid 32-byte URL-safe base64 key from SECRET_KEY."""
    raw = hashlib.sha256(settings.secret_key.encode()).digest()
    key = base64.urlsafe_b64encode(raw)
    return Fernet(key)


_fernet = _build_fernet()


def encrypt_token(plain_text: str) -> str:
    """Return Fernet-encrypted ciphertext as a UTF-8 string."""
    return _fernet.encrypt(plain_text.encode()).decode()


def decrypt_token(cipher_text: str) -> str:
    """Decrypt a Fernet token. Raises ValueError on tampering."""
    try:
        return _fernet.decrypt(cipher_text.encode()).decode()
    except InvalidToken as exc:
        raise ValueError("Token decryption failed — possible tampering.") from exc
