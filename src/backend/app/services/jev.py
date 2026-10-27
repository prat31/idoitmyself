"""Jev (TypeSafe's System One model) via OpenRouter's Decisions API, for AI conditions in filters.

One request per email: the email is the `state`, and each AI condition still open for it is a `noul`
(yes/no) question, keyed by `question_key(prompt)`. Jev answers with P(yes) per question.
Docs: https://openrouter.ai/docs/guides/community/jev-tutorial.md
"""

from collections.abc import Awaitable, Callable, Mapping
from typing import Any

import httpx

from app.core.config import get_settings
from app.core.retry import TransientError, parse_retry_after
from app.mail.types import FetchedEmail

TRUNCATION_MARKER = "\n…[truncated]"

# question key -> the condition's natural-language description
Questions = Mapping[str, str]
# question key -> P(yes)
Answers = Mapping[str, float]
AskFn = Callable[[httpx.AsyncClient, FetchedEmail, Questions], Awaitable[Answers]]


class JevError(Exception):
    """A failed Jev call. `fatal` errors (auth, billing, missing key) would fail every email, so the
    scan stops at the first one instead of failing each email."""

    def __init__(self, message: str, *, fatal: bool = False):
        super().__init__(message)
        self.fatal = fatal


class JevTransientError(JevError, TransientError):
    """A Jev failure worth retrying later (rate limit, 5xx, network)."""

    def __init__(self, message: str, retry_after: float | None = None):
        JevError.__init__(self, message)
        self.retry_after = retry_after


FATAL_STATUSES = {401: "authentication failed", 402: "insufficient OpenRouter credits", 403: "access denied"}


def is_configured() -> bool:
    return get_settings().openrouter_api_key is not None


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
    email: FetchedEmail, questions: Questions, model: str, body_max_chars: int
) -> dict[str, Any]:
    return {
        "model": model,
        "state": email_state(email, body_max_chars),
        "questions": {
            key: {
                "type": "noul",
                "instructions": "Does this email meet the following condition?",
                "criteria": {"true": prompt, "false": "The email does not meet that condition."},
            }
            for key, prompt in questions.items()
        },
    }


def parse_response(body: dict[str, Any], questions: Questions) -> dict[str, float]:
    answers = body.get("answers") or {}
    probabilities: dict[str, float] = {}
    for key in questions:
        answer = answers.get(key)
        if not isinstance(answer, dict) or not isinstance(answer.get("noul"), int | float):
            raise JevError(f"Jev returned no answer for question {key!r}")
        probabilities[key] = float(answer["noul"])
    return probabilities


async def ask(client: httpx.AsyncClient, email: FetchedEmail, questions: Questions) -> Answers:
    settings = get_settings()
    if settings.openrouter_api_key is None:
        raise JevError("OPENROUTER_API_KEY is not set, so AI conditions can't be evaluated", fatal=True)
    payload = build_request(email, questions, settings.jev_model, settings.jev_body_max_chars)
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
    return parse_response(response.json(), questions)
