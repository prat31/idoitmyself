"""Evaluates a filter's rule against an email. Pure: no I/O. Compile once (regexes included), then
call the result for every email.

Text tests are case-insensitive unless the condition says otherwise. For list fields (recipients,
attachments, ...) a positive operator holds if any value matches; its negation ("not_contains", ...)
holds if no value matches. A missing value counts as empty text, and fails every number test."""

import operator
import re
from collections.abc import Callable
from typing import Any

from app.filters.fields import FIELDS, FieldType
from app.filters.rule import Condition, Rule, SubGroup
from app.mail.types import FetchedEmail

Predicate = Callable[[FetchedEmail], bool]

_NEGATED = {"not_equals": "equals", "not_contains": "contains", "not_matches_regex": "matches_regex"}
_NUMBER_OPS = {
    "eq": operator.eq,
    "ne": operator.ne,
    "gt": operator.gt,
    "gte": operator.ge,
    "lt": operator.lt,
    "lte": operator.le,
}


def _text_test(op: str, value: str, case_sensitive: bool) -> Callable[[str], bool]:
    if op == "matches_regex":
        pattern = re.compile(value, 0 if case_sensitive else re.IGNORECASE)
        return lambda text: pattern.search(text) is not None
    fold = (lambda s: s) if case_sensitive else str.casefold
    needle = fold(value)
    match op:
        case "equals":
            return lambda text: fold(text.strip()) == needle.strip()
        case "contains":
            return lambda text: needle in fold(text)
        case "starts_with":
            return lambda text: fold(text).startswith(needle)
        case "ends_with":
            return lambda text: fold(text).endswith(needle)
    raise ValueError(f"Unknown text operator: {op}")


def _as_texts(raw: Any) -> list[str]:
    if raw is None:
        return []
    if isinstance(raw, list | tuple):
        return [str(v) for v in raw if v is not None]
    return [str(raw)]


def compile_condition(condition: Condition) -> Predicate:
    spec = FIELDS[condition.field]

    def read(email: FetchedEmail) -> Any:
        return spec.read(email, condition.argument)

    op = condition.op
    match spec.type:
        case FieldType.TEXT | FieldType.TEXT_LIST:
            if op in ("is_empty", "is_not_empty"):
                empty = op == "is_empty"
                return lambda e: (not any(t.strip() for t in _as_texts(read(e)))) == empty
            base = _NEGATED.get(op, op)
            test = _text_test(base, str(condition.value), condition.case_sensitive)

            def any_matches(email: FetchedEmail) -> bool:
                return any(test(text) for text in _as_texts(read(email)))

            return (lambda e: not any_matches(e)) if op in _NEGATED else any_matches
        case FieldType.BOOL:
            expected = op == "is_true"
            return lambda e: bool(read(e)) == expected
        case FieldType.NUMBER:
            compare = _NUMBER_OPS[op]
            target = float(condition.value)  # type: ignore[arg-type]

            def number_test(email: FetchedEmail) -> bool:
                value = read(email)
                return value is not None and compare(float(value), target)

            return number_test
        case FieldType.ENUM:
            if op == "in":
                options = set(condition.value)  # type: ignore[arg-type]
                return lambda e: read(e) in options
            if op == "is_not":
                return lambda e: read(e) != condition.value
            return lambda e: read(e) == condition.value
    raise ValueError(f"Unsupported field type: {spec.type}")


def _chain(items: list[tuple[str | None, Predicate]]) -> Predicate:
    """Items joined by AND / OR, AND binding tighter: split at every OR into runs of ANDs; the chain
    holds if any run holds entirely. `A OR B AND C` → any([A], [B, C])."""
    runs: list[list[Predicate]] = [[]]
    for join, predicate in items:
        if join == "or":
            runs.append([])
        runs[-1].append(predicate)
    return lambda e: any(all(p(e) for p in run) for run in runs)


def compile_rule(rule: Rule) -> Predicate:
    def item(node: Condition | SubGroup) -> Predicate:
        if isinstance(node, Condition):
            return compile_condition(node)
        return _chain([(c.join, compile_condition(c)) for c in node.items])

    return _chain([(node.join, item(node)) for node in rule.items])
