"""A filter's rule: a list of conditions and groups, with its own AND / OR between each item and the
one before it (`join`; the first item has none). AND binds tighter than OR, like SQL:
`A OR B AND C` means `A OR (B AND C)`. Groups are brackets: `(A OR B) AND (C OR D)`. Inside a group
the same joins apply; groups hold conditions only, so a rule is at most two levels deep.
Negation lives in the operators (not_contains, ...)."""

import re
from collections.abc import Iterator
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.filters.fields import FIELDS, FieldType
from app.models.inbox import InboxProvider

MAX_ITEMS = 25  # per group
MAX_CONDITIONS = 50  # per rule
MAX_VALUE_LENGTH = 500
MAX_PROMPT_LENGTH = 1000  # an AI condition's description
MAX_AI_CONDITIONS = 5  # per rule: each one is a question to Jev for every email that reaches it

Join = Literal["and", "or"]


def _check_joins(items: list) -> None:
    """Every item after the first is joined to the one before it; the first has nothing to join to."""
    if items and items[0].join is not None:
        raise ValueError("The first item can't have an AND/OR join")
    if any(item.join is None for item in items[1:]):
        raise ValueError("Every item after the first needs an AND/OR join")


class Condition(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["condition"] = "condition"
    # How this item joins the one before it in its list; None for the first item.
    join: Join | None = None
    field: str
    op: str
    # Text: a string (a regex for the regex operators). Number: a number. Enum: an option, or a list
    # of options for "in". Operators that take no value (is_empty, is_true, ...): omitted.
    value: str | float | list[str] | None = None
    # Extra input some fields need, e.g. the header name for "header".
    argument: Annotated[str, Field(max_length=100)] | None = None
    case_sensitive: bool = False

    @model_validator(mode="after")
    def check(self) -> "Condition":
        spec = FIELDS.get(self.field)
        if spec is None:
            raise ValueError(f"Unknown field: {self.field}")
        operator = spec.operator(self.op)
        if operator is None:
            raise ValueError(f'"{self.op}" is not an operator for {spec.label}')
        if spec.argument_label and not (self.argument or "").strip():
            raise ValueError(f"{spec.label}: {spec.argument_label} is required")
        if not operator.takes_value:
            if self.value is not None:
                raise ValueError(f'{spec.label} "{operator.label}" takes no value')
            return self
        match spec.type:
            case FieldType.TEXT | FieldType.TEXT_LIST:
                if not isinstance(self.value, str) or not self.value:
                    raise ValueError(f"{spec.label}: a text value is required")
                if len(self.value) > MAX_VALUE_LENGTH:
                    raise ValueError(f"{spec.label}: value must be at most {MAX_VALUE_LENGTH} characters")
                if self.op in ("matches_regex", "not_matches_regex"):
                    try:
                        re.compile(self.value)
                    except re.error as exc:
                        raise ValueError(f"{spec.label}: invalid regex ({exc})") from None
            case FieldType.AI:
                if not isinstance(self.value, str) or not self.value.strip():
                    raise ValueError("AI condition: describe the emails it should match")
                if len(self.value) > MAX_PROMPT_LENGTH:
                    raise ValueError(
                        f"AI condition: description must be at most {MAX_PROMPT_LENGTH} characters"
                    )
            case FieldType.NUMBER:
                if not isinstance(self.value, float):
                    raise ValueError(f"{spec.label}: a number is required")
            case FieldType.ENUM:
                allowed = {value for value, _ in spec.options}
                values = self.value if self.op == "in" else [self.value]
                if not isinstance(values, list) or not values or any(v not in allowed for v in values):
                    raise ValueError(f"{spec.label}: choose from {', '.join(sorted(allowed))}")
        return self


class SubGroup(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["group"] = "group"
    join: Join | None = None
    items: Annotated[list[Condition], Field(min_length=1, max_length=MAX_ITEMS)]

    @model_validator(mode="after")
    def check_joins(self) -> "SubGroup":
        _check_joins(self.items)
        return self


class Rule(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["group"] = "group"
    items: Annotated[
        list[Annotated[Condition | SubGroup, Field(discriminator="type")]],
        Field(min_length=1, max_length=MAX_ITEMS),
    ]

    @model_validator(mode="after")
    def check_size(self) -> "Rule":
        _check_joins(self.items)
        if sum(1 for _ in self.conditions()) > MAX_CONDITIONS:
            raise ValueError(f"A rule can have at most {MAX_CONDITIONS} conditions")
        if sum(1 for _ in self.ai_conditions()) > MAX_AI_CONDITIONS:
            raise ValueError(f"A rule can have at most {MAX_AI_CONDITIONS} AI conditions")
        return self

    def conditions(self) -> Iterator[Condition]:
        for item in self.items:
            if isinstance(item, Condition):
                yield item
            else:
                yield from item.items

    def ai_conditions(self) -> Iterator[Condition]:
        return (c for c in self.conditions() if FIELDS[c.field].type == FieldType.AI)


def check_mailbox_types(rule: Rule, mailbox_types: frozenset[InboxProvider]) -> None:
    """Raise ValueError if the rule uses a field that isn't available for every mailbox type in scope
    (e.g. a Gmail-only field on a filter that also covers another provider's inboxes)."""
    for condition in rule.conditions():
        spec = FIELDS[condition.field]
        if not spec.applies_to(mailbox_types):
            raise ValueError(f"{spec.label} isn't available for every selected inbox")
