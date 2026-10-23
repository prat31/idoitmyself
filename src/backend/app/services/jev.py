"""Jev (TypeSafe's System One model) via OpenRouter's Decisions API.

One request per email: the email is the `state`, and each label in the run is a `noul` (yes/no)
question keyed by label name. Jev answers with P(yes) per question.
Docs: https://openrouter.ai/docs/guides/community/jev-tutorial.md
"""

from dataclasses import dataclass
from decimal import Decimal
from typing import Any

import httpx

from app.core.config import get_settings
from app.core.retry import TransientError, parse_retry_after
from app.mail.types import FetchedEmail

TRUNCATION_MARKER = "\n…[truncated]"


class JevError(Exception):
    """A failed Jev call. `fatal` errors (auth, billing, missing key) would fail every email,
    so a run stops at the first one instead of retrying each message."""

    def __init__(self, message: str, *, fatal: bool = False):
        super().__init__(message)
        self.fatal = fatal


class JevTransientError(JevError, TransientError):
    """A Jev failure worth retrying later (rate limit, 5xx, network)."""

    def __init__(self, message: str, retry_after: float | None = None):
        JevError.__init__(self, message)
        self.retry_after = retry_after


FATAL_STATUSES = {401: "authentication failed", 402: "insufficient OpenRouter credits", 403: "access denied"}


@dataclass(frozen=True)
class LabelQuestion:
    name: str  # normalized label name, used as the question key
    filter_condition: str


@dataclass(frozen=True)
class JevAnswer:
    probabilities: dict[str, float]  # label name -> P(yes)
    cost_usd: Decimal


def email_state(email: FetchedEmail, body_max_chars: int) -> dict[str, str]:
    body = email.body_text
    if len(body) > body_max_chars:
        body = body[:body_max_chars] + TRUNCATION_MARKER
    state = {
        "from": email.from_address,
        "to": email.to_addresses,
        "cc": email.cc_addresses,
        "subject": email.subject,
        "date": email.sent_at.isoformat(),
        # Always present (even "none") so conditions can rely on attachments, e.g. "a PDF is attached".
        "attachments": "; ".join(f"{a.filename} ({a.mime_type})" for a in email.attachments) or "none",
        "body": body or email.snippet,
    }
    return {key: value for key, value in state.items() if value}


def build_request(
    email: FetchedEmail, labels: list[LabelQuestion], model: str, body_max_chars: int
) -> dict[str, Any]:
    return {
        "model": model,
        "state": email_state(email, body_max_chars),
        "questions": {
            label.name: {
                "type": "noul",
                "instructions": "Does this email meet the following condition?",
                "criteria": {
                    "true": label.filter_condition,
                    "false": "The email does not meet that condition.",
                },
            }
            for label in labels
        },
    }


def parse_response(body: dict[str, Any], labels: list[LabelQuestion]) -> JevAnswer:
    answers = body.get("answers") or {}
    probabilities: dict[str, float] = {}
    for label in labels:
        answer = answers.get(label.name)
        if not isinstance(answer, dict) or not isinstance(answer.get("noul"), int | float):
            raise JevError(f"Jev returned no answer for label {label.name!r}")
        probabilities[label.name] = float(answer["noul"])
    cost = (body.get("usage") or {}).get("cost") or 0
    return JevAnswer(probabilities=probabilities, cost_usd=Decimal(str(cost)))


async def classify(client: httpx.AsyncClient, email: FetchedEmail, labels: list[LabelQuestion]) -> JevAnswer:
    settings = get_settings()
    if settings.openrouter_api_key is None:
        raise JevError("OPENROUTER_API_KEY is not set", fatal=True)
    payload = build_request(email, labels, settings.jev_model, settings.jev_body_max_chars)
    headers = {"Authorization": f"Bearer {settings.openrouter_api_key.get_secret_value()}"}

    # Never sleeps: transient failures raise JevTransientError and the task re-queues the email.
    try:
        response = await client.post(settings.jev_decisions_url, json=payload, headers=headers, timeout=60)
    except httpx.TransportError as exc:
        raise JevTransientError(f"Jev request failed: {exc!r}") from exc
    if response.status_code in FATAL_STATUSES:
        reason = FATAL_STATUSES[response.status_code]
        raise JevError(
            f"Jev {reason} ({response.status_code}): {response.text[:300]}. "
            "Check OPENROUTER_API_KEY and your OpenRouter account.",
            fatal=True,
        )
    if response.status_code in (429, 500, 502, 503, 504):
        raise JevTransientError(
            f"Jev returned {response.status_code}",
            retry_after=parse_retry_after(response.headers.get("retry-after")),
        )
    if response.status_code != 200:
        raise JevError(f"Jev returned {response.status_code}: {response.text[:300]}")
    return parse_response(response.json(), labels)
