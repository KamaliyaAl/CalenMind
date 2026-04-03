"""
AuthService — Google OAuth 2.0 flow: authorization URL, callback handling,
token storage, and refresh logic.

## Traceability
Feature: F001 — Google OAuth Authentication
Scenarios: SC001

## Business context
Manages the full OAuth lifecycle. Generates the Google consent URL,
exchanges the authorization code for tokens, persists them encrypted,
and refreshes expired access tokens transparently so Calendar API calls
never fail due to expiry.
"""

from datetime import datetime, timezone

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow

from backend.core.config import settings
from backend.core.exceptions import AuthNotConnectedException, TokenDecryptionException
from backend.model.user_model import UserModel
from backend.repository.token_repository import TokenRepository
from backend.repository.user_repository import UserRepository

SCOPES = [
    "https://www.googleapis.com/auth/calendar.events",
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
]

_CLIENT_CONFIG = {
    "web": {
        "client_id": settings.google_client_id,
        "client_secret": settings.google_client_secret,
        "redirect_uris": [settings.google_redirect_uri],
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
    }
}


class AuthService:
    def __init__(self, user_repo: UserRepository, token_repo: TokenRepository) -> None:
        self._user_repo = user_repo
        self._token_repo = token_repo

    def _build_flow(self) -> Flow:
        return Flow.from_client_config(
            _CLIENT_CONFIG,
            scopes=SCOPES,
            redirect_uri=settings.google_redirect_uri,
        )

    async def get_authorization_url(self, telegram_id: int) -> str:
        """
        Return a Google consent URL. The state parameter encodes telegram_id
        so the callback handler can associate the token with the correct user.
        """
        flow = self._build_flow()
        auth_url, _ = flow.authorization_url(
            access_type="offline",
            include_granted_scopes="true",
            prompt="consent",
            state=str(telegram_id),
        )
        return auth_url

    async def handle_callback(self, code: str, state: str) -> UserModel:
        """
        Exchange authorization code for tokens, store encrypted, mark user connected.
        Returns the updated UserModel.
        """
        telegram_id = int(state)
        flow = self._build_flow()
        import os
        os.environ["OAUTHLIB_RELAX_TOKEN_SCOPE"] = "1"  # allow Google to return subset of scopes
        flow.fetch_token(code=code)

        creds: Credentials = flow.credentials
        user, _ = await self._user_repo.get_or_create(telegram_id)

        expiry: datetime | None = creds.expiry
        if expiry and expiry.tzinfo is None:
            expiry = expiry.replace(tzinfo=timezone.utc)

        await self._token_repo.upsert_tokens(
            user_id=user.id,
            access_token=creds.token,
            refresh_token=creds.refresh_token,
            expiry=expiry,
            scopes=" ".join(creds.scopes or []),
        )

        # Fetch Google email from id_token (may be a JWT string or a dict)
        email = ""
        if hasattr(creds, "id_token") and creds.id_token:
            id_token = creds.id_token
            if isinstance(id_token, dict):
                email = id_token.get("email", "")
            elif isinstance(id_token, str):
                import base64, json
                try:
                    payload = id_token.split(".")[1]
                    payload += "=" * (4 - len(payload) % 4)
                    email = json.loads(base64.urlsafe_b64decode(payload)).get("email", "")
                except Exception:
                    email = ""

        user = await self._user_repo.mark_google_connected(user, email)
        return user

    async def get_credentials(self, user: UserModel) -> Credentials:
        """
        Return a valid Credentials object, refreshing if expired.
        Raises AuthNotConnectedException if user has no stored tokens.
        """
        if not user.is_google_connected:
            raise AuthNotConnectedException()

        try:
            tokens = await self._token_repo.get_plain_tokens(user.id)
        except ValueError as exc:
            raise TokenDecryptionException() from exc

        if not tokens:
            raise AuthNotConnectedException()

        creds = Credentials(
            token=tokens["access_token"],
            refresh_token=tokens["refresh_token"],
            token_uri="https://oauth2.googleapis.com/token",
            client_id=settings.google_client_id,
            client_secret=settings.google_client_secret,
            scopes=(tokens["scopes"] or "").split(),
        )

        if creds.expired and creds.refresh_token:
            import google.auth.transport.requests as google_requests
            request = google_requests.Request()
            creds.refresh(request)
            expiry = creds.expiry
            if expiry and expiry.tzinfo is None:
                expiry = expiry.replace(tzinfo=timezone.utc)
            await self._token_repo.upsert_tokens(
                user_id=user.id,
                access_token=creds.token,
                refresh_token=creds.refresh_token,
                expiry=expiry,
                scopes=" ".join(creds.scopes or []),
            )

        return creds
