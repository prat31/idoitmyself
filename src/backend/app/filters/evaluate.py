"""Evaluates a filter's rule against an email. Pure: no I/O. Compile once (regexes included), then
call the result for every email.

Text tests are case-insensitive unless the condition says otherwise. For list fields (recipients,
attachments, ...) a positive operator holds if any value matches; its negation ("not_contains", ...)
holds if no value matches. A missing value counts as empty text, and fails every number test.

AI conditions aren't read from the email: their answer is a probability from Jev, passed in. Until it
is, an AI condition is *unknown*, and the rule is evaluated with three-valued logic (an AND run with a
false item is false whatever else it holds; one true run makes the OR true). `CompiledRule.pending`
names the AI questions whose answers could still change the result, so Jev is only asked about
emails where they matter."""

import hashlib
import operator
import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any

from app.filters.fields import FIELDS, FieldType
from app.filters.rule import Condition, Rule, SubGroup
from app.mail.types import FetchedEmail

Predicate = Callable[[FetchedEmail], bool]
# question key -> P(yes), from Jev
Answers = Mapping[str, float]
# (value, AI question keys it still depends on): the value is None while unknown, and the keys are
# empty once it's known.
Outcome = tuple[bool | None, frozenset[str]]
Node = Callable[[FetchedEmail, Answers], Outcome]

_KNOWN: frozenset[str] = frozenset()
DEFAULT_THRESHOLD = 0.5

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


def question_key(prompt: str) -> str:
    """The Jev question for an AI condition's description. Same description, same question, so a
    description shared by several conditions or filters is asked once per email."""
    return "q_" + hashlib.sha256(prompt.strip().encode()).hexdigest()[:16]


def _ai_node(condition: Condition, threshold: float) -> Node:
    key = question_key(str(condition.value))
    negate = condition.op == "not_matches"

    def node(email: FetchedEmail, answers: Answers) -> Outcome:
        if key not in answers:
            return None, frozenset({key})
        return (answers[key] >= threshold) != negate, _KNOWN

    return node


def _known(predicate: Predicate) -> Node:
    return lambda email, _: (predicate(email), _KNOWN)


def _chain(items: list[tuple[str | None, Node]]) -> Node:
    """Items joined by AND / OR, AND binding tighter: split at every OR into runs of ANDs; the chain
    holds if any run holds entirely. `A OR B AND C` → any([A], [B, C]). Unknown items make a run
    unknown unless another of its items is false, and the chain unknown unless another run is true."""
    runs: list[list[Node]] = [[]]
    for join, node in items:
        if join == "or":
            runs.append([])
        runs[-1].append(node)

    def run_outcome(run: list[Node], email: FetchedEmail, answers: Answers) -> Outcome:
        outcomes = [node(email, answers) for node in run]
        if any(value is False for value, _ in outcomes):
            return False, _KNOWN
        if all(value for value, _ in outcomes):
            return True, _KNOWN
        return None, frozenset().union(*(needs for value, needs in outcomes if value is None))

    def chain(email: FetchedEmail, answers: Answers) -> Outcome:
        outcomes = [run_outcome(run, email, answers) for run in runs]
        if any(value for value, _ in outcomes):
            return True, _KNOWN
        if all(value is False for value, _ in outcomes):
            return False, _KNOWN
        return None, frozenset().union(*(needs for value, needs in outcomes if value is None))

    return chain


@dataclass(frozen=True)
class CompiledRule:
    root: Node
    # question key -> description, for every AI condition in the rule
    questions: Mapping[str, str]

    def pending(self, email: FetchedEmail, answers: Answers | None = None) -> frozenset[str]:
        """The AI questions whose answers could still change whether the email matches; empty once
        it's decided (always, for a rule without AI conditions)."""
        return self.root(email, answers or {})[1]

    def __call__(self, email: FetchedEmail, answers: Answers | None = None) -> bool:
        """Whether the email matches. An AI condition left unanswered counts as not holding."""
        return self.root(email, answers or {})[0] is True


def compile_rule(rule: Rule, threshold: float = DEFAULT_THRESHOLD) -> CompiledRule:
    def condition(c: Condition) -> Node:
        if FIELDS[c.field].type == FieldType.AI:
            return _ai_node(c, threshold)
        return _known(compile_condition(c))

    def item(node: Condition | SubGroup) -> Node:
        if isinstance(node, Condition):
            return condition(node)
        return _chain([(c.join, condition(c)) for c in node.items])

    questions = {question_key(str(c.value)): str(c.value).strip() for c in rule.ai_conditions()}
    return CompiledRule(_chain([(node.join, item(node)) for node in rule.items]), questions)
