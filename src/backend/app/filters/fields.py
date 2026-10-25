"""The fields a filter condition can test, and the operators each field type supports.

Common fields work for every mailbox type. A provider's own fields (e.g. Gmail's category) name the
mailbox types they apply to and read their values from `FetchedEmail.provider_fields`, which that
provider's MailSource fills in."""

import enum
from collections.abc import Callable
from dataclasses import dataclass
from email.utils import getaddresses
from typing import Any

from app.mail.types import FetchedEmail
from app.models.inbox import InboxProvider


class FieldType(enum.StrEnum):
    TEXT = "text"
    TEXT_LIST = "text_list"  # several values (e.g. recipients); a condition holds if any value does
    BOOL = "bool"
    NUMBER = "number"
    ENUM = "enum"


@dataclass(frozen=True)
class Operator:
    key: str
    label: str
    takes_value: bool = True


_TEXT_OPERATORS = (
    Operator("equals", "is"),
    Operator("not_equals", "is not"),
    Operator("contains", "contains"),
    Operator("not_contains", "does not contain"),
    Operator("starts_with", "starts with"),
    Operator("ends_with", "ends with"),
    Operator("matches_regex", "matches regex"),
    Operator("not_matches_regex", "does not match regex"),
    Operator("is_empty", "is empty", takes_value=False),
    Operator("is_not_empty", "is not empty", takes_value=False),
)

OPERATORS: dict[FieldType, tuple[Operator, ...]] = {
    FieldType.TEXT: _TEXT_OPERATORS,
    FieldType.TEXT_LIST: _TEXT_OPERATORS,
    FieldType.BOOL: (
        Operator("is_true", "is true", takes_value=False),
        Operator("is_false", "is false", False),
    ),
    FieldType.NUMBER: (
        Operator("eq", "="),
        Operator("ne", "≠"),
        Operator("gt", ">"),
        Operator("gte", "≥"),
        Operator("lt", "<"),
        Operator("lte", "≤"),
    ),
    FieldType.ENUM: (Operator("is", "is"), Operator("is_not", "is not"), Operator("in", "is any of")),
}

Reader = Callable[[FetchedEmail, str | None], Any]


@dataclass(frozen=True)
class FieldSpec:
    key: str
    label: str
    type: FieldType
    description: str
    read: Reader
    # None: every mailbox type.
    mailbox_types: frozenset[InboxProvider] | None = None
    options: tuple[tuple[str, str], ...] = ()  # (value, label) for ENUM fields
    # Set when the condition needs an extra input, e.g. which header to read.
    argument_label: str | None = None

    def operator(self, key: str) -> Operator | None:
        return next((op for op in OPERATORS[self.type] if op.key == key), None)

    def applies_to(self, mailbox_types: frozenset[InboxProvider]) -> bool:
        """Usable on a filter covering these mailbox types: common fields always; a provider's own
        fields only when every covered type has them."""
        return self.mailbox_types is None or (bool(mailbox_types) and mailbox_types <= self.mailbox_types)


def _addresses(*values: str | None) -> list[tuple[str, str]]:
    return [(name, addr) for name, addr in getaddresses([v for v in values if v]) if addr or name]


def _sender(email: FetchedEmail) -> tuple[str, str] | None:
    found = _addresses(email.from_address)
    return found[0] if found else None


def _from_address(email: FetchedEmail, _: str | None) -> str | None:
    sender = _sender(email)
    return sender[1] if sender else None


def _from_name(email: FetchedEmail, _: str | None) -> str | None:
    sender = _sender(email)
    return sender[0] if sender else None


def _from_domain(email: FetchedEmail, _: str | None) -> str | None:
    address = _from_address(email, None)
    return address.rsplit("@", 1)[1] if address and "@" in address else None


def _address_list(*headers: str) -> Reader:
    """Addresses (no display names) from the given headers, in order."""

    def raw(email: FetchedEmail, header: str) -> str | None:
        if header == "to":
            return email.to_addresses
        if header == "cc":
            return email.cc_addresses
        return email.headers.get(header)

    return lambda email, _: [addr for _, addr in _addresses(*(raw(email, h) for h in headers)) if addr]


def _header(name: str) -> Reader:
    return lambda email, _: email.headers.get(name)


def _provider_field(key: str) -> Reader:
    return lambda email, _: email.provider_fields.get(key)


_GMAIL = frozenset({InboxProvider.GMAIL})

FIELDS: dict[str, FieldSpec] = {
    spec.key: spec
    for spec in (
        FieldSpec("from_address", "Sender address", FieldType.TEXT, "Email address in From", _from_address),
        FieldSpec("from_name", "Sender name", FieldType.TEXT, "Display name in From", _from_name),
        FieldSpec("from_domain", "Sender domain", FieldType.TEXT, "Domain of the From address", _from_domain),
        FieldSpec("to", "To", FieldType.TEXT_LIST, "Any address in To", _address_list("to")),
        FieldSpec("cc", "Cc", FieldType.TEXT_LIST, "Any address in Cc", _address_list("cc")),
        FieldSpec(
            "any_recipient",
            "Any recipient",
            FieldType.TEXT_LIST,
            "Any address in To, Cc, Bcc or Delivered-To",
            _address_list("to", "cc", "bcc", "delivered-to"),
        ),
        FieldSpec(
            "reply_to", "Reply-To", FieldType.TEXT_LIST, "Any address in Reply-To", _address_list("reply-to")
        ),
        FieldSpec("subject", "Subject", FieldType.TEXT, "Subject line", lambda e, _: e.subject),
        FieldSpec("body", "Body", FieldType.TEXT, "Plain-text body (never stored)", lambda e, _: e.body_text),
        FieldSpec(
            "has_attachments",
            "Has attachments",
            FieldType.BOOL,
            "At least one attached file (inline images don't count)",
            lambda e, _: bool(e.attachments),
        ),
        FieldSpec(
            "attachment_name",
            "Attachment name",
            FieldType.TEXT_LIST,
            "File name of any attachment",
            lambda e, _: [a.filename for a in e.attachments],
        ),
        FieldSpec(
            "attachment_type",
            "Attachment type",
            FieldType.TEXT_LIST,
            "MIME type of any attachment, e.g. application/pdf",
            lambda e, _: [a.mime_type for a in e.attachments],
        ),
        FieldSpec(
            "attachment_count",
            "Attachment count",
            FieldType.NUMBER,
            "Number of attachments",
            lambda e, _: len(e.attachments),
        ),
        FieldSpec(
            "size_bytes",
            "Size (bytes)",
            FieldType.NUMBER,
            "Size of the whole message",
            lambda e, _: e.size_bytes,
        ),
        FieldSpec(
            "is_reply",
            "Is a reply",
            FieldType.BOOL,
            "Has In-Reply-To or References headers",
            lambda e, _: "in-reply-to" in e.headers or "references" in e.headers,
        ),
        FieldSpec(
            "is_mailing_list",
            "Is from a mailing list",
            FieldType.BOOL,
            "Has List-Id or List-Unsubscribe headers (newsletters, notifications)",
            lambda e, _: "list-id" in e.headers or "list-unsubscribe" in e.headers,
        ),
        FieldSpec("list_id", "Mailing list id", FieldType.TEXT, "The List-Id header", _header("list-id")),
        FieldSpec(
            "header",
            "Header",
            FieldType.TEXT,
            "Any header, by name",
            lambda e, name: e.headers.get((name or "").lower()),
            argument_label="Header name",
        ),
        # --- Gmail only ----------------------------------------------------------------------------
        FieldSpec(
            "gmail_category",
            "Gmail category",
            FieldType.ENUM,
            "The Gmail inbox tab",
            _provider_field("gmail_category"),
            mailbox_types=_GMAIL,
            options=(
                ("primary", "Primary"),
                ("social", "Social"),
                ("promotions", "Promotions"),
                ("updates", "Updates"),
                ("forums", "Forums"),
            ),
        ),
        FieldSpec(
            "gmail_label",
            "Gmail label",
            FieldType.TEXT_LIST,
            "Any of the message's Gmail labels, as they were when it was scanned",
            _provider_field("gmail_labels"),
            mailbox_types=_GMAIL,
        ),
        FieldSpec(
            "gmail_is_important",
            "Marked important",
            FieldType.BOOL,
            "Gmail's importance marker, as it was when scanned",
            _provider_field("gmail_is_important"),
            mailbox_types=_GMAIL,
        ),
        FieldSpec(
            "gmail_is_starred",
            "Starred",
            FieldType.BOOL,
            "Starred in Gmail, as it was when scanned",
            _provider_field("gmail_is_starred"),
            mailbox_types=_GMAIL,
        ),
    )
}
