import uuid

import pytest
from pydantic import ValidationError

from app.filters.evaluate import compile_rule, question_key
from app.filters.rule import MAX_AI_CONDITIONS, Rule
from app.services import jev
from app.services.scan_engine import compile_filters, matching_labels, pending_questions
from tests.test_filters import email
from tests.test_scan_engine import stored_filter

STATEMENT = "A credit card statement, not a promotion"
INVOICE = "An invoice for something I bought"
STATEMENT_KEY, INVOICE_KEY = question_key(STATEMENT), question_key(INVOICE)


def ai(prompt: str, join: str | None = None, op: str = "matches") -> dict:
    condition = {"type": "condition", "field": "ai", "op": op, "value": prompt}
    return condition | ({"join": join} if join else {})


def cond(field: str, op: str, value=None, join: str | None = None) -> dict:
    condition = {"type": "condition", "field": field, "op": op}
    if value is not None:
        condition["value"] = value
    return condition | ({"join": join} if join else {})


def compiled(*items: dict):
    return compile_rule(Rule.model_validate({"items": list(items)}))


def test_ai_condition_needs_its_answer():
    rule = compiled(ai(STATEMENT))

    assert rule.pending(email()) == {STATEMENT_KEY}
    assert rule(email()) is False  # unanswered counts as not holding
    assert rule(email(), {STATEMENT_KEY: 0.9}) is True
    assert rule(email(), {STATEMENT_KEY: 0.2}) is False
    assert rule.pending(email(), {STATEMENT_KEY: 0.2}) == frozenset()


def test_does_not_match_negates():
    rule = compiled(ai(STATEMENT, op="not_matches"))

    assert rule(email(), {STATEMENT_KEY: 0.2}) is True
    assert rule(email(), {STATEMENT_KEY: 0.9}) is False


def test_threshold():
    rule = compile_rule(Rule.model_validate({"items": [ai(STATEMENT)]}), threshold=0.8)

    assert rule(email(), {STATEMENT_KEY: 0.7}) is False
    assert rule(email(), {STATEMENT_KEY: 0.8}) is True


def test_false_and_run_skips_the_question():
    rule = compiled(cond("from_domain", "equals", "example.org"), ai(STATEMENT, "and"))

    assert rule.pending(email()) == frozenset()
    assert rule(email()) is False


def test_true_or_skips_the_question():
    rule = compiled(cond("from_domain", "equals", "hdfcbank.net"), ai(STATEMENT, "or"))

    assert rule.pending(email()) == frozenset()
    assert rule(email()) is True


def test_only_runs_still_open_are_asked():
    # A AND ai1 OR ai2: A is false, so only ai2 can still make it match.
    rule = compiled(cond("from_domain", "equals", "example.org"), ai(STATEMENT, "and"), ai(INVOICE, "or"))

    assert rule.pending(email()) == {INVOICE_KEY}
    assert rule(email(), {INVOICE_KEY: 0.9}) is True


def test_ai_inside_a_group():
    # has attachments AND (subject contains "receipt" OR ai)
    group = {
        "type": "group",
        "join": "and",
        "items": [cond("subject", "contains", "receipt"), ai(STATEMENT, "or")],
    }
    rule = compiled(cond("has_attachments", "is_true"), group)

    assert rule.pending(email()) == {STATEMENT_KEY}
    assert rule(email(), {STATEMENT_KEY: 0.6}) is True
    assert compiled(cond("has_attachments", "is_true"), group).pending(email(attachments=())) == frozenset()


def test_rule_validation():
    with pytest.raises(ValidationError, match="describe"):
        Rule.model_validate({"items": [ai("   ")]})
    with pytest.raises(ValidationError, match="at most"):
        too_many = [ai(f"p{i}", "or" if i else None) for i in range(MAX_AI_CONDITIONS + 1)]
        Rule.model_validate({"items": too_many})


def test_same_description_is_asked_once():
    label_a, label_b = uuid.uuid4(), uuid.uuid4()
    filters = compile_filters(
        [
            stored_filter({"items": [ai(STATEMENT)]}, label_a),
            stored_filter({"items": [ai(f"  {STATEMENT} ")]}, label_b),
        ]
    )

    assert pending_questions(filters, email()) == {STATEMENT_KEY: STATEMENT}
    assert matching_labels(filters, email(), {STATEMENT_KEY: 0.9}).keys() == {label_a, label_b}


def test_label_already_added_needs_no_question():
    bills = uuid.uuid4()
    filters = compile_filters(
        [
            stored_filter({"items": [cond("subject", "contains", "statement")]}, bills),
            stored_filter({"items": [ai(STATEMENT)]}, bills),
        ]
    )

    assert pending_questions(filters, email()) == {}


def test_jev_request_and_response():
    request = jev.build_request(email(), {STATEMENT_KEY: STATEMENT}, "typesafe/jev-1.13", body_max_chars=5)

    assert request["model"] == "typesafe/jev-1.13"
    assert request["state"]["attachments"] == "Statement_Oct.pdf (application/pdf)"
    assert request["state"]["body"] == "Total" + jev.TRUNCATION_MARKER
    question = request["questions"][STATEMENT_KEY]
    assert question["type"] == "noul" and question["criteria"]["true"] == STATEMENT

    body = {"answers": {STATEMENT_KEY: {"type": "noul", "noul": 0.93}}}
    answers = jev.parse_response(body, {STATEMENT_KEY: ""})
    assert answers == {STATEMENT_KEY: 0.93}
    with pytest.raises(jev.JevError, match="no answer"):
        jev.parse_response({"answers": {}}, {STATEMENT_KEY: ""})
