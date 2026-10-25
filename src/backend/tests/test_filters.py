from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from app.filters.evaluate import compile_rule
from app.filters.rule import Rule, check_mailbox_types
from app.mail.types import Attachment, FetchedEmail
from app.models.inbox import InboxProvider


def email(**overrides) -> FetchedEmail:
    values = {
        "provider_message_id": "m1",
        "provider_thread_id": "t1",
        "internet_message_id": "<x@y>",
        "sent_at": datetime(2026, 10, 1, tzinfo=UTC),
        "from_address": "HDFC Bank <alerts@HDFCBank.net>",
        "to_addresses": "Me <me@example.com>, other@example.org",
        "cc_addresses": None,
        "subject": "Your Credit Card Statement",
        "snippet": None,
        "body_text": "Total due: 1,234",
        "attachments": (Attachment("Statement_Oct.pdf", "application/pdf"),),
        "headers": {"list-unsubscribe": "<mailto:u@x>", "x-mailer": "BankMailer 2"},
        "size_bytes": 52_000,
        "provider_fields": {"gmail_category": "updates", "gmail_labels": ["INBOX", "Finance"]},
    }
    return FetchedEmail(**(values | overrides))


def matches(rule: dict, mail: FetchedEmail | None = None) -> bool:
    return compile_rule(Rule.model_validate(rule))(mail or email())


def one(field: str, op: str, value=None, **extra) -> dict:
    condition = {"type": "condition", "field": field, "op": op, **extra}
    if value is not None:
        condition["value"] = value
    return {"items": [condition]}


@pytest.mark.parametrize(
    ("field", "op", "value", "expected"),
    [
        ("from_address", "equals", "alerts@hdfcbank.net", True),  # case-insensitive by default
        ("from_address", "matches_regex", r"@hdfcbank\.(com|net)$", True),
        ("from_address", "not_matches_regex", r"@hdfcbank\.", False),
        ("from_name", "starts_with", "hdfc", True),
        ("from_domain", "equals", "hdfcbank.net", True),
        ("subject", "contains", "statement", True),
        ("subject", "not_contains", "statement", False),
        ("subject", "ends_with", "STATEMENT", True),
        ("body", "contains", "total due", True),
        ("to", "equals", "other@example.org", True),  # any address
        ("to", "not_equals", "other@example.org", False),  # no address
        ("any_recipient", "contains", "example.com", True),
        ("attachment_name", "matches_regex", r"\.pdf$", True),
        ("attachment_type", "equals", "application/pdf", True),
        ("list_id", "contains", "x", False),
    ],
)
def test_text_operators(field, op, value, expected):
    assert matches(one(field, op, value)) is expected


def test_case_sensitive_text_and_regex():
    assert matches(one("subject", "contains", "statement", case_sensitive=True)) is False
    assert matches(one("subject", "matches_regex", "credit", case_sensitive=True)) is False
    assert matches(one("subject", "matches_regex", "Credit", case_sensitive=True)) is True


def test_empty_checks_treat_missing_as_empty():
    assert matches(one("cc", "is_empty")) is True
    assert matches(one("list_id", "is_empty")) is True
    assert matches(one("subject", "is_not_empty")) is True
    assert matches(one("subject", "is_empty"), email(subject=None)) is True


def test_bool_number_and_header_fields():
    assert matches(one("has_attachments", "is_true")) is True
    assert matches(one("has_attachments", "is_true"), email(attachments=())) is False
    assert matches(one("is_mailing_list", "is_true")) is True
    assert matches(one("is_reply", "is_false")) is True
    assert matches(one("attachment_count", "gte", 1)) is True
    assert matches(one("size_bytes", "lt", 50_000)) is False
    assert matches(one("size_bytes", "gt", 1), email(size_bytes=None)) is False
    assert matches(one("header", "starts_with", "bankmailer", argument="X-Mailer")) is True


def test_gmail_fields():
    assert matches(one("gmail_category", "is", "updates")) is True
    assert matches(one("gmail_category", "is_not", "updates")) is False
    assert matches(one("gmail_category", "in", ["promotions", "social"])) is False
    assert matches(one("gmail_label", "equals", "finance")) is True
    assert matches(one("gmail_is_starred", "is_false")) is True


def cond(field: str, op: str, value=None, join: str | None = None) -> dict:
    item = {"type": "condition", "field": field, "op": op}
    if value is not None:
        item["value"] = value
    if join:
        item["join"] = join
    return item


def test_and_binds_tighter_than_or():
    # A OR B AND C  ==  A OR (B AND C)
    a = cond("subject", "contains", "nothing-like-this")  # false
    b = cond("subject", "contains", "statement", join="or")  # true
    c = cond("has_attachments", "is_false", join="and")  # false
    assert matches({"items": [a, b, c]}) is False  # left-to-right would give (A OR B) AND C = False too
    # A AND B OR C  ==  (A AND B) OR C
    a2 = cond("subject", "contains", "nothing-like-this")  # false
    b2 = cond("subject", "contains", "statement", join="and")  # true
    c2 = cond("has_attachments", "is_true", join="or")  # true
    assert matches({"items": [a2, b2, c2]}) is True
    # A OR B AND C with A true: true regardless of B AND C (left-to-right would AND with C)
    a3 = cond("subject", "contains", "statement")  # true
    b3 = cond("subject", "contains", "x", join="or")
    c3 = cond("has_attachments", "is_false", join="and")  # false
    assert matches({"items": [a3, b3, c3]}) is True


def test_groups_are_brackets():
    # (domain is hdfcbank.net OR subject contains invoice) AND attachment name ends with .pdf
    rule = {
        "items": [
            {
                "type": "group",
                "items": [
                    cond("from_domain", "equals", "hdfcbank.net"),
                    cond("subject", "contains", "invoice", join="or"),
                ],
            },
            cond("attachment_name", "ends_with", ".pdf", join="and"),
        ]
    }
    assert matches(rule) is True
    assert matches(rule, email(attachments=())) is False
    assert matches(rule, email(from_address="x@other.com")) is False
    assert matches(rule, email(from_address="x@other.com", subject="Invoice 42")) is True


@pytest.mark.parametrize(
    "items",
    [
        [cond("subject", "contains", "a", join="and")],  # first item can't have a join
        [cond("subject", "contains", "a"), cond("subject", "contains", "b")],  # second needs one
        [cond("subject", "contains", "a"), {"type": "group", "items": [cond("subject", "contains", "b")]}],
    ],
)
def test_joins_are_checked(items):
    with pytest.raises(ValidationError):
        Rule.model_validate({"items": items})


@pytest.mark.parametrize(
    "condition",
    [
        {"field": "nope", "op": "equals", "value": "x"},
        {"field": "subject", "op": "gt", "value": 1},
        {"field": "subject", "op": "contains"},
        {"field": "subject", "op": "contains", "value": ""},
        {"field": "subject", "op": "matches_regex", "value": "(unclosed"},
        {"field": "has_attachments", "op": "is_true", "value": "yes"},
        {"field": "size_bytes", "op": "gt", "value": "big"},
        {"field": "gmail_category", "op": "is", "value": "spam"},
        {"field": "gmail_category", "op": "in", "value": []},
        {"field": "header", "op": "contains", "value": "x"},
    ],
)
def test_invalid_conditions_rejected(condition):
    with pytest.raises(ValidationError):
        Rule.model_validate({"items": [{"type": "condition", **condition}]})


def test_depth_is_capped_at_two_levels():
    nested = {
        "items": [
            {
                "type": "group",
                "items": [{"type": "group", "items": []}],
            }
        ],
    }
    with pytest.raises(ValidationError):
        Rule.model_validate(nested)
    with pytest.raises(ValidationError):
        Rule.model_validate({"items": []})


def test_provider_fields_need_every_covered_type():
    rule = Rule.model_validate(one("gmail_category", "is", "social"))
    check_mailbox_types(rule, frozenset({InboxProvider.GMAIL}))  # fine
    with pytest.raises(ValueError, match="every selected inbox"):
        check_mailbox_types(rule, frozenset())
    common = Rule.model_validate(one("subject", "contains", "x"))
    check_mailbox_types(common, frozenset())  # common fields fit any scope
