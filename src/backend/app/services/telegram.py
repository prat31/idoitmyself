"""Sending notifications to a Telegram chat (Bot API sendMessage). Only used when TELEGRAM_BOT_TOKEN and
TELEGRAM_CHAT_ID are both set."""

import html

import httpx

from app.core.config import get_settings
from app.core.retry import TransientError, parse_retry_after


class TelegramError(Exception):
    """Telegram refused the message (bad token, unknown chat, ...): retrying won't help. Safe to show."""


def is_configured() -> bool:
    settings = get_settings()
    return settings.telegram_bot_token is not None and bool(settings.telegram_chat_id)


def format_message(title: str, body: str | None, link: str | None) -> str:
    parts = [f"<b>{html.escape(title)}</b>"]
    if body:
        parts.append(html.escape(body))
    if link:
        parts.append(f'<a href="{html.escape(link, quote=True)}">Open the email</a>')
    return "\n".join(parts)


async def send_message(client: httpx.AsyncClient, text: str) -> None:
    """Raises TransientError (rate limit, 5xx, network) or TelegramError."""
    settings = get_settings()
    assert settings.telegram_bot_token is not None
    url = f"{settings.telegram_api_url}/bot{settings.telegram_bot_token.get_secret_value()}/sendMessage"
    try:
        response = await client.post(
            url,
            json={
                "chat_id": settings.telegram_chat_id,
                "text": text,
                "parse_mode": "HTML",
                "disable_web_page_preview": True,
            },
        )
    except httpx.TransportError as exc:
        raise TransientError(f"Telegram request failed: {exc!r}") from exc
    if response.status_code == 200:
        return
    try:
        body = response.json()
    except ValueError:
        body = {}
    detail = f"Telegram returned {response.status_code}: {body.get('description', response.text[:200])}"
    if response.status_code == 429 or response.status_code >= 500:
        retry_after = body.get("parameters", {}).get("retry_after") or parse_retry_after(
            response.headers.get("retry-after")
        )
        raise TransientError(detail, retry_after=float(retry_after) if retry_after else None)
    raise TelegramError(detail)
