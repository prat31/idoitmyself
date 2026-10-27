import httpx
import pytest

from app.core.config import get_settings
from app.core.retry import TransientError
from app.services import telegram


@pytest.fixture
def configured(monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "telegram_bot_token", __import__("pydantic").SecretStr("123:abc"))
    monkeypatch.setattr(settings, "telegram_chat_id", "42")


def client(status: int, body: dict) -> httpx.AsyncClient:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/bot123:abc/sendMessage"
        return httpx.Response(status, json=body)

    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


def test_not_configured_without_both_settings():
    assert not telegram.is_configured()


def test_message_is_escaped():
    text = telegram.format_message("Bill <due>", "Total & more", "https://mail.example/?a=1&b=2")
    assert text == (
        "<b>Bill &lt;due&gt;</b>\nTotal &amp; more\n"
        '<a href="https://mail.example/?a=1&amp;b=2">Open the email</a>'
    )


async def test_send(configured):
    await telegram.send_message(client(200, {"ok": True}), "hi")


async def test_rate_limit_is_transient(configured):
    with pytest.raises(TransientError) as exc:
        await telegram.send_message(client(429, {"parameters": {"retry_after": 7}}), "hi")
    assert exc.value.retry_after == 7


async def test_bad_chat_is_not_retried(configured):
    with pytest.raises(telegram.TelegramError, match="chat not found"):
        await telegram.send_message(client(400, {"description": "Bad Request: chat not found"}), "hi")
