"""Gmail implementation of MailSource (Gmail API v1, read-only)."""

import asyncio
import base64
import uuid
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from email.utils import parsedate_to_datetime
from typing import Any
from urllib.parse import quote

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.crypto import decrypt, encrypt
from app.core.quota import QuotaBudget
from app.core.redis import loop_redis
from app.core.retry import parse_retry_after
from app.mail.text import html_to_text, normalize_whitespace
from app.mail.types import (
    Attachment,
    FetchedEmail,
    MailSourceError,
    TransientMailSourceError,
)
from app.models.inbox import InboxCredential
from app.services.gmail_oauth import OAuthError, refresh_access_token

API_BASE = "https://gmail.googleapis.com/gmail/v1/users/me"
TOKEN_REFRESH_MARGIN = timedelta(minutes=2)
# Quota units per call (developers.google.com/workspace/gmail/api/reference/quota).
UNITS_LIST = 5
UNITS_GET_FULL = 60
UNITS_LABELS = 1
UNITS_ATTACHMENT = 20

# Gmail's inbox tabs, as label ids.
CATEGORY_LABELS = {
    "CATEGORY_PERSONAL": "primary",
    "CATEGORY_SOCIAL": "social",
    "CATEGORY_PROMOTIONS": "promotions",
    "CATEGORY_UPDATES": "updates",
    "CATEGORY_FORUMS": "forums",
}

# Gmail reports per-user throttling as 403 with these reasons (as well as 429).
RATE_LIMIT_REASONS = frozenset({"rateLimitExceeded", "userRateLimitExceeded", "quotaExceeded"})


class GmailSource:
    def __init__(
        self,
        inbox_id: uuid.UUID,
        client: httpx.AsyncClient,
        session_factory: Callable[[], AsyncSession],
        quota: QuotaBudget | None = None,
    ):
        self._inbox_id = inbox_id
        self._client = client
        self._session_factory = session_factory
        self._token: str | None = None
        self._expires_at = datetime.min.replace(tzinfo=UTC)
        self._token_lock = asyncio.Lock()
        # Caps concurrent Gmail calls from this process, whatever the batch's own concurrency.
        self._in_flight = _process_gmail_limiter()
        # Shared across processes: every Gmail call reserves its quota units first.
        self._quota = quota if quota is not None else gmail_quota_budget()
        # Gmail label id -> name, read once per source (user labels have opaque ids like "Label_12").
        self._label_names: dict[str, str] | None = None
        self._labels_lock = asyncio.Lock()

    # --- auth -------------------------------------------------------------------------------------

    async def _access_token(self, force_refresh: bool = False) -> str:
        async with self._token_lock:
            if (
                not force_refresh
                and self._token
                and datetime.now(UTC) < self._expires_at - TOKEN_REFRESH_MARGIN
            ):
                return self._token
            async with self._session_factory() as session:
                credential = await session.get(InboxCredential, self._inbox_id)
                if credential is None:
                    raise MailSourceError("Inbox has no stored credentials; reconnect it")
                fresh = datetime.now(UTC) < credential.access_token_expires_at - TOKEN_REFRESH_MARGIN
                if fresh and not force_refresh:
                    self._token = decrypt(credential.encrypted_access_token)
                    self._expires_at = credential.access_token_expires_at
                    return self._token
                try:
                    token, expires_at = await refresh_access_token(
                        self._client, decrypt(credential.encrypted_refresh_token)
                    )
                except OAuthError as exc:
                    raise MailSourceError(
                        f"Gmail access was revoked or expired; reconnect the inbox ({exc})"
                    ) from exc
                credential.encrypted_access_token = encrypt(token)
                credential.access_token_expires_at = expires_at
                await session.commit()
            self._token, self._expires_at = token, expires_at
            return token

    async def _get(
        self,
        path: str,
        params: dict[str, Any] | list[tuple[str, Any]],
        *,
        units: int,
    ) -> dict[str, Any]:
        """One Gmail API call. Never sleeps: throttling and server errors raise
        TransientMailSourceError so the caller can re-queue the work with a delay."""
        token = await self._access_token()
        for refreshed in (False, True):
            # Raises QuotaExhausted (no call made) when this mailbox's budget for the window is spent.
            await self._quota.reserve(str(self._inbox_id), units)
            try:
                async with self._in_flight:
                    response = await self._client.get(
                        f"{API_BASE}{path}", params=params, headers={"Authorization": f"Bearer {token}"}
                    )
            except httpx.TransportError as exc:
                raise TransientMailSourceError(f"Gmail request failed: {exc!r}") from exc
            if response.status_code == 401 and not refreshed:
                token = await self._access_token(force_refresh=True)  # expired token: refresh, retry once
                continue
            break

        if response.status_code == 200:
            return response.json()
        reasons = _error_reasons(response)
        detail = f"Gmail API returned {response.status_code} for {path}" + (
            f" ({', '.join(reasons)})" if reasons else ""
        )
        if response.status_code in (429, 500, 502, 503, 504) or (
            response.status_code == 403 and RATE_LIMIT_REASONS.intersection(reasons)
        ):
            raise TransientMailSourceError(
                detail, retry_after=parse_retry_after(response.headers.get("retry-after"))
            )
        raise MailSourceError(detail)

    # --- MailSource -------------------------------------------------------------------------------

    async def list_message_ids(self, start: datetime, end: datetime) -> list[str]:
        # after:/before: accept epoch seconds (the received time); after is exclusive (hence the -1),
        # before is exclusive. Drafts aren't scanned; spam and trash are left out by default.
        query = f"after:{int(start.timestamp()) - 1} before:{int(end.timestamp())} -in:drafts"
        ids: list[str] = []
        page_token: str | None = None
        while True:
            params: dict[str, Any] = {"q": query, "maxResults": 500}
            if page_token:
                params["pageToken"] = page_token
            body = await self._get("/messages", params, units=UNITS_LIST)
            ids.extend(m["id"] for m in body.get("messages", []))
            page_token = body.get("nextPageToken")
            if not page_token:
                return ids

    async def fetch(self, message_id: str) -> FetchedEmail:
        message = await self._get(f"/messages/{message_id}", {"format": "full"}, units=UNITS_GET_FULL)
        return parse_message(message, await self._labels())

    async def fetch_attachment(self, message_id: str, ref: str) -> bytes:
        body = await self._get(
            f"/messages/{message_id}/attachments/{quote(ref, safe='')}", {}, units=UNITS_ATTACHMENT
        )
        data = body.get("data", "")
        return base64.urlsafe_b64decode(data + "=" * (-len(data) % 4))

    async def _labels(self) -> dict[str, str]:
        async with self._labels_lock:
            if self._label_names is None:
                body = await self._get("/labels", {}, units=UNITS_LABELS)
                self._label_names = {label["id"]: label["name"] for label in body.get("labels", [])}
            return self._label_names


def web_url(email_address: str, message_id: str) -> str:
    """Opens the message in Gmail's web UI, in the right signed-in account (authuser)."""
    return f"https://mail.google.com/mail/?authuser={quote(email_address)}#all/{quote(message_id)}"


def gmail_quota_budget() -> QuotaBudget:
    settings = get_settings()
    return QuotaBudget(
        loop_redis(),
        namespace="gmail",
        units_per_minute=settings.gmail_quota_units_per_minute,
        utilisation=settings.gmail_quota_utilisation,
        window_seconds=settings.gmail_quota_window_seconds,
    )


_limiters: dict[int, asyncio.Semaphore] = {}


def _process_gmail_limiter() -> asyncio.Semaphore:
    """One semaphore per event loop (each Celery task runs its own loop), shared by every GmailSource
    in it, so all of this process's Gmail calls count against GMAIL_MAX_IN_FLIGHT together."""
    loop_id = id(asyncio.get_running_loop())
    if loop_id not in _limiters:
        _limiters.clear()  # previous tasks' loops are gone
        _limiters[loop_id] = asyncio.Semaphore(get_settings().gmail_max_in_flight)
    return _limiters[loop_id]


def _error_reasons(response: httpx.Response) -> list[str]:
    """Google API error reasons, e.g. ['rateLimitExceeded']."""
    try:
        error = response.json().get("error", {})
    except ValueError:
        return []
    reasons = [e.get("reason") for e in error.get("errors", []) if e.get("reason")]
    for detail in error.get("details", []):
        if detail.get("reason"):
            reasons.append(detail["reason"])
    return reasons


def _header_map(payload: dict[str, Any]) -> dict[str, str]:
    """Headers by lowercase name; repeated headers are joined with ", "."""
    headers: dict[str, str] = {}
    for header in payload.get("headers", []):
        name = header["name"].lower()
        headers[name] = f"{headers[name]}, {header['value']}" if name in headers else header["value"]
    return headers


def _decode(data: str) -> str:
    return base64.urlsafe_b64decode(data + "=" * (-len(data) % 4)).decode("utf-8", errors="replace")


def extract_body_text(payload: dict[str, Any]) -> str:
    """Plain-text body of a Gmail message payload: prefers text/plain parts, falls back to HTML."""
    plain: list[str] = []
    markup: list[str] = []

    def walk(part: dict[str, Any]) -> None:
        mime = part.get("mimeType", "")
        data = part.get("body", {}).get("data")
        if part.get("filename"):  # attachment
            return
        if data and mime == "text/plain":
            plain.append(_decode(data))
        elif data and mime == "text/html":
            markup.append(_decode(data))
        for child in part.get("parts", []) or []:
            walk(child)

    walk(payload)
    if plain:
        return normalize_whitespace("\n\n".join(plain))
    return html_to_text("\n".join(markup))


def extract_body_html(payload: dict[str, Any]) -> str | None:
    """The HTML body of a Gmail message payload, if it has one."""
    found: list[str] = []

    def walk(part: dict[str, Any]) -> None:
        data = part.get("body", {}).get("data")
        if not part.get("filename") and data and part.get("mimeType") == "text/html":
            found.append(_decode(data))
        for child in part.get("parts", []) or []:
            walk(child)

    walk(payload)
    return "\n".join(found) or None


def extract_attachments(payload: dict[str, Any]) -> tuple[Attachment, ...]:
    """Named file parts of a Gmail payload, skipping inline images (logos, signatures)."""
    found: list[Attachment] = []

    def walk(part: dict[str, Any]) -> None:
        filename = (part.get("filename") or "").strip()
        mime = part.get("mimeType", "application/octet-stream")
        if filename:
            disposition = _header_map(part).get("content-disposition", "").lower()
            if not (mime.startswith("image/") and disposition.startswith("inline")):
                body = part.get("body", {})
                found.append(
                    Attachment(
                        filename=filename, mime_type=mime, ref=body.get("attachmentId"), size=body.get("size")
                    )
                )
        for child in part.get("parts", []) or []:
            walk(child)

    walk(payload)
    return tuple(found)


def gmail_fields(label_ids: list[str], label_names: dict[str, str]) -> dict[str, Any]:
    """Values for the Gmail-only filter fields (see app.filters.fields)."""
    category = next((CATEGORY_LABELS[i] for i in label_ids if i in CATEGORY_LABELS), None)
    return {
        "gmail_category": category,
        "gmail_labels": [label_names.get(i, i) for i in label_ids],
        "gmail_is_important": "IMPORTANT" in label_ids,
        "gmail_is_starred": "STARRED" in label_ids,
    }


def parse_message(message: dict[str, Any], label_names: dict[str, str] | None = None) -> FetchedEmail:
    payload = message.get("payload", {})
    headers = _header_map(payload)
    sent_at = datetime.fromtimestamp(int(message["internalDate"]) / 1000, tz=UTC)
    if "date" in headers:
        try:
            sent_at = parsedate_to_datetime(headers["date"]).astimezone(UTC)
        except (TypeError, ValueError):
            pass  # keep internalDate
    return FetchedEmail(
        provider_message_id=message["id"],
        provider_thread_id=message.get("threadId"),
        internet_message_id=headers.get("message-id"),
        sent_at=sent_at,
        from_address=headers.get("from"),
        to_addresses=headers.get("to"),
        cc_addresses=headers.get("cc"),
        subject=headers.get("subject"),
        snippet=html_to_text(message["snippet"]) if message.get("snippet") else None,
        body_text=extract_body_text(payload),
        body_html=extract_body_html(payload),
        attachments=extract_attachments(payload),
        headers=headers,
        size_bytes=message.get("sizeEstimate"),
        provider_fields=gmail_fields(message.get("labelIds", []), label_names or {}),
    )
