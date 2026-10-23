"""Google OAuth 2.0 (authorization code + PKCE) for connecting Gmail inboxes."""

import base64
import hashlib
import json
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from urllib.parse import urlencode

import httpx

from app.core.config import get_settings
from app.core.redis import redis_client
from app.schemas.inbox import InboxDraft

AUTHORIZE_ENDPOINT = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"
USERINFO_ENDPOINT = "https://openidconnect.googleapis.com/v1/userinfo"

GMAIL_READONLY_SCOPE = "https://www.googleapis.com/auth/gmail.readonly"
SCOPES = ["openid", "email", GMAIL_READONLY_SCOPE]

STATE_TTL_SECONDS = 600
_STATE_KEY_PREFIX = "oauth:gmail:state:"


class OAuthError(Exception):
    """Raised for failures in the OAuth round trip. `code` is safe to show to the user."""

    def __init__(self, code: str, detail: str | None = None):
        super().__init__(detail or code)
        self.code = code


@dataclass(frozen=True)
class PendingAuthorization:
    draft: InboxDraft
    code_verifier: str


@dataclass(frozen=True)
class GoogleTokens:
    access_token: str
    refresh_token: str
    expires_at: datetime
    scopes: list[str]


def _code_challenge(verifier: str) -> str:
    digest = hashlib.sha256(verifier.encode()).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode()


async def start_authorization(draft: InboxDraft) -> str:
    """Persist the draft + PKCE verifier under a one-time state and return Google's consent URL."""
    settings = get_settings()
    state = secrets.token_urlsafe(32)
    code_verifier = secrets.token_urlsafe(64)

    payload = {"draft": draft.model_dump(), "code_verifier": code_verifier}
    await redis_client.set(_STATE_KEY_PREFIX + state, json.dumps(payload), ex=STATE_TTL_SECONDS)

    params = {
        "client_id": settings.google_client_id,
        "redirect_uri": settings.google_redirect_uri,
        "response_type": "code",
        "scope": " ".join(SCOPES),
        "access_type": "offline",
        "prompt": "consent",  # always return a refresh token
        "include_granted_scopes": "true",
        "state": state,
        "code_challenge": _code_challenge(code_verifier),
        "code_challenge_method": "S256",
    }
    return f"{AUTHORIZE_ENDPOINT}?{urlencode(params)}"


async def consume_state(state: str) -> PendingAuthorization:
    """Fetch and delete the pending authorization for `state` (single use)."""
    raw = await redis_client.getdel(_STATE_KEY_PREFIX + state)
    if raw is None:
        raise OAuthError("invalid_state", "OAuth state is unknown or expired")
    payload = json.loads(raw)
    return PendingAuthorization(
        draft=InboxDraft.model_validate(payload["draft"]), code_verifier=payload["code_verifier"]
    )


async def exchange_code(code: str, code_verifier: str) -> GoogleTokens:
    settings = get_settings()
    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.post(
            TOKEN_ENDPOINT,
            data={
                "code": code,
                "client_id": settings.google_client_id,
                "client_secret": settings.google_client_secret.get_secret_value(),
                "redirect_uri": settings.google_redirect_uri,
                "grant_type": "authorization_code",
                "code_verifier": code_verifier,
            },
        )
    if response.status_code != 200:
        raise OAuthError("token_exchange_failed", f"Google token endpoint returned {response.status_code}")

    body = response.json()
    scopes = body.get("scope", "").split()
    if GMAIL_READONLY_SCOPE not in scopes:
        raise OAuthError("missing_scope", "Gmail read access was not granted")
    if "refresh_token" not in body:
        raise OAuthError("missing_refresh_token", "Google did not return a refresh token")

    return GoogleTokens(
        access_token=body["access_token"],
        refresh_token=body["refresh_token"],
        expires_at=datetime.now(UTC) + timedelta(seconds=int(body["expires_in"])),
        scopes=scopes,
    )


async def fetch_email_address(access_token: str) -> str:
    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.get(USERINFO_ENDPOINT, headers={"Authorization": f"Bearer {access_token}"})
    if response.status_code != 200:
        raise OAuthError("userinfo_failed", f"Google userinfo returned {response.status_code}")
    body = response.json()
    if not body.get("email") or not body.get("email_verified"):
        raise OAuthError("email_unavailable", "Google account has no verified email")
    return body["email"].lower()


async def refresh_access_token(client: httpx.AsyncClient, refresh_token: str) -> tuple[str, datetime]:
    """Exchange a refresh token for a new access token. Returns (access_token, expires_at)."""
    settings = get_settings()
    response = await client.post(
        TOKEN_ENDPOINT,
        data={
            "client_id": settings.google_client_id,
            "client_secret": settings.google_client_secret.get_secret_value(),
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        },
    )
    if response.status_code != 200:
        # invalid_grant means the user revoked access or the token expired: the inbox must reconnect.
        error = (
            response.json().get("error", "")
            if response.headers.get("content-type", "").startswith("application/json")
            else ""
        )
        raise OAuthError(
            "refresh_failed", f"Google token refresh returned {response.status_code} {error}".strip()
        )
    body = response.json()
    return body["access_token"], datetime.now(UTC) + timedelta(seconds=int(body["expires_in"]))
