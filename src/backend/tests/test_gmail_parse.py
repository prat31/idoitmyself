import base64
from datetime import UTC, datetime

from app.mail.gmail import extract_body_text, parse_message


def b64(text: str) -> str:
    return base64.urlsafe_b64encode(text.encode()).decode().rstrip("=")


def test_prefers_plain_text_and_skips_attachments():
    payload = {
        "mimeType": "multipart/mixed",
        "parts": [
            {
                "mimeType": "multipart/alternative",
                "parts": [
                    {"mimeType": "text/plain", "body": {"data": b64("Hello\r\n\r\n\r\nWorld")}},
                    {"mimeType": "text/html", "body": {"data": b64("<p>Hello</p>")}},
                ],
            },
            {"mimeType": "text/plain", "filename": "notes.txt", "body": {"data": b64("attachment")}},
        ],
    }
    assert extract_body_text(payload) == "Hello\n\nWorld"


def test_falls_back_to_html():
    payload = {
        "mimeType": "text/html",
        "body": {"data": b64("<style>p{}</style><p>Total&nbsp;due</p><br>Pay now")},
    }
    assert extract_body_text(payload) == "Total due\n\nPay now"


def test_parse_message_headers_and_date():
    message = {
        "id": "m1",
        "threadId": "t1",
        "internalDate": "1790000000000",
        "snippet": "It&#39;s ready",
        "payload": {
            "mimeType": "text/plain",
            "headers": [
                {"name": "From", "value": "Bank <a@b.c>"},
                {"name": "Subject", "value": "Statement"},
                {"name": "Message-ID", "value": "<x@y>"},
                {"name": "Date", "value": "Thu, 01 Oct 2026 10:00:00 +0530"},
            ],
            "body": {"data": b64("Body")},
        },
    }
    email = parse_message(message)
    assert email.subject == "Statement"
    assert email.from_address == "Bank <a@b.c>"
    assert email.internet_message_id == "<x@y>"
    assert email.snippet == "It's ready"
    assert email.sent_at == datetime(2026, 10, 1, 4, 30, tzinfo=UTC)
    assert email.body_text == "Body"


def test_attachments_listed_without_inline_images():
    from app.mail.gmail import extract_attachments

    payload = {
        "mimeType": "multipart/mixed",
        "parts": [
            {"mimeType": "text/plain", "body": {"data": b64("Statement attached")}},
            {
                "mimeType": "application/pdf",
                "filename": "Statement_Oct2026.pdf",
                "body": {"attachmentId": "a1"},
            },
            {
                "mimeType": "image/png",
                "filename": "logo.png",
                "headers": [{"name": "Content-Disposition", "value": "inline; filename=logo.png"}],
                "body": {"attachmentId": "a2"},
            },
        ],
    }
    attachments = extract_attachments(payload)
    assert [(a.filename, a.mime_type) for a in attachments] == [("Statement_Oct2026.pdf", "application/pdf")]
    assert extract_body_text(payload) == "Statement attached"
