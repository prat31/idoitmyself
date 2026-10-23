import uuid
from datetime import UTC, datetime, timedelta
from email.utils import format_datetime

import httpx
import pytest

from app.core.quota import QuotaBudget
from app.core.retry import backoff_seconds, parse_retry_after
from app.mail.gmail import GmailSource
from app.mail.types import MailSourceError, TransientMailSourceError
from tests.fakes import MemoryCounter


def unlimited_quota() -> QuotaBudget:
    return QuotaBudget(
        MemoryCounter(), namespace="test", units_per_minute=10**9, utilisation=1, window_seconds=60
    )


@pytest.mark.parametrize("attempt", range(10))
def test_backoff_is_exponential_jittered_and_capped(attempt):
    delay = backoff_seconds(attempt, base=5, cap=600)
    expected = min(600, 5 * 2**attempt)
    assert expected / 2 <= delay <= expected


def test_backoff_honours_retry_after_but_not_beyond_cap():
    assert backoff_seconds(0, base=5, cap=600, retry_after=42) >= 42
    assert backoff_seconds(0, base=5, cap=600, retry_after=9999) == 600


def test_parse_retry_after():
    assert parse_retry_after("7") == 7
    assert parse_retry_after(None) is None
    assert parse_retry_after("soon") is None
    http_date = format_datetime(datetime.now(UTC) + timedelta(seconds=30), usegmt=True)
    assert 25 <= parse_retry_after(http_date) <= 31


def gmail_with(status: int, body: dict, headers: dict | None = None) -> GmailSource:
    transport = httpx.MockTransport(lambda request: httpx.Response(status, json=body, headers=headers))
    source = GmailSource(
        uuid.uuid4(),
        httpx.AsyncClient(transport=transport),
        session_factory=lambda: None,
        quota=unlimited_quota(),
    )
    source._token, source._expires_at = "token", datetime.now(UTC) + timedelta(hours=1)  # skip the DB lookup
    return source


def google_error(code: int, reason: str) -> dict:
    return {"error": {"code": code, "errors": [{"reason": reason}], "message": reason}}


@pytest.mark.parametrize("reason", ["rateLimitExceeded", "userRateLimitExceeded"])
async def test_gmail_403_rate_limit_is_transient(reason):
    with pytest.raises(TransientMailSourceError, match=reason):
        await gmail_with(403, google_error(403, reason)).fetch("m1")


async def test_gmail_429_is_transient_with_retry_after():
    with pytest.raises(TransientMailSourceError) as caught:
        await gmail_with(429, google_error(429, "rateLimitExceeded"), {"Retry-After": "12"}).fetch("m1")
    assert caught.value.retry_after == 12


async def test_gmail_other_403_is_permanent():
    with pytest.raises(MailSourceError) as caught:
        await gmail_with(403, google_error(403, "insufficientPermissions")).fetch("m1")
    assert not isinstance(caught.value, TransientMailSourceError)


async def test_gmail_calls_are_capped_per_process(monkeypatch):
    import asyncio
    import base64

    from app.core.config import get_settings

    monkeypatch.setattr(get_settings(), "gmail_max_in_flight", 2)
    in_flight = peak = 0

    async def handler(request: httpx.Request) -> httpx.Response:
        nonlocal in_flight, peak
        in_flight += 1
        peak = max(peak, in_flight)
        await asyncio.sleep(0.01)
        in_flight -= 1
        body = base64.urlsafe_b64encode(b"hi").decode()
        message = {
            "id": "m",
            "internalDate": "0",
            "payload": {"mimeType": "text/plain", "body": {"data": body}},
        }
        return httpx.Response(200, json=message)

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    sources = [
        GmailSource(uuid.uuid4(), client, session_factory=lambda: None, quota=unlimited_quota())
        for _ in range(2)
    ]
    for source in sources:
        source._token, source._expires_at = "token", datetime.now(UTC) + timedelta(hours=1)
    await asyncio.gather(*(sources[i % 2].fetch(f"m{i}") for i in range(10)))
    assert peak == 2  # shared across sources (inboxes) in this process


async def test_gmail_does_not_call_api_when_budget_is_spent():
    from app.core.quota import QuotaExhausted

    calls = []
    transport = httpx.MockTransport(lambda request: calls.append(request) or httpx.Response(200, json={}))
    tight = QuotaBudget(MemoryCounter(), namespace="t", units_per_minute=59, utilisation=1, window_seconds=60)
    source = GmailSource(
        uuid.uuid4(), httpx.AsyncClient(transport=transport), session_factory=lambda: None, quota=tight
    )
    source._token, source._expires_at = "token", datetime.now(UTC) + timedelta(hours=1)
    with pytest.raises(QuotaExhausted):
        await source.fetch("m1")  # a full fetch costs 60 units > the 59-unit window
    assert calls == []  # Gmail was never called
