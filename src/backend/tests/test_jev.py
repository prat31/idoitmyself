from datetime import UTC, datetime
from decimal import Decimal

import pytest

from app.mail.types import Attachment, FetchedEmail
from app.services.jev import TRUNCATION_MARKER, JevError, LabelQuestion, build_request, parse_response

EMAIL = FetchedEmail(
    provider_message_id="m1",
    provider_thread_id="t1",
    internet_message_id="<id@x>",
    sent_at=datetime(2026, 10, 1, 9, 30, tzinfo=UTC),
    from_address="Bank <alerts@bank.example>",
    to_addresses="me@example.com",
    cc_addresses=None,
    subject="Your statement",
    snippet="Statement ready",
    body_text="Amount due: 100",
)
LABELS = [
    LabelQuestion("credit_card_bill", "Credit card statements"),
    LabelQuestion("travel", "Trip bookings"),
]


def test_request_has_one_noul_question_per_label_keyed_by_name():
    request = build_request(EMAIL, LABELS, "typesafe/jev-1.13", 8000)
    assert request["model"] == "typesafe/jev-1.13"
    assert set(request["questions"]) == {"credit_card_bill", "travel"}
    question = request["questions"]["credit_card_bill"]
    assert question["type"] == "noul"
    assert question["criteria"]["true"] == "Credit card statements"
    assert request["state"]["subject"] == "Your statement"
    assert "cc" not in request["state"]  # empty fields are omitted


def test_body_is_truncated():
    long_email = FetchedEmail(**{**EMAIL.__dict__, "body_text": "x" * 50})
    body = build_request(long_email, LABELS, "m", 10)["state"]["body"]
    assert body == "x" * 10 + TRUNCATION_MARKER


def test_parse_response_reads_noul_probabilities_and_cost():
    answer = parse_response(
        {
            "answers": {
                "credit_card_bill": {"type": "noul", "noul": 0.96},
                "travel": {"type": "noul", "noul": 0},
            },
            "usage": {"cost": 0.000019992},
        },
        LABELS,
    )
    assert answer.probabilities == {"credit_card_bill": 0.96, "travel": 0.0}
    assert answer.cost_usd == Decimal("0.000019992")


def test_parse_response_rejects_missing_answer():
    with pytest.raises(JevError):
        parse_response({"answers": {"credit_card_bill": {"type": "noul", "noul": 0.5}}}, LABELS)


def test_state_lists_attachments_or_none():
    assert build_request(EMAIL, LABELS, "m", 8000)["state"]["attachments"] == "none"
    with_pdf = FetchedEmail(**{**EMAIL.__dict__, "attachments": (Attachment("Stmt.pdf", "application/pdf"),)})
    assert build_request(with_pdf, LABELS, "m", 8000)["state"]["attachments"] == "Stmt.pdf (application/pdf)"
