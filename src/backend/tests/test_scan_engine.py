import uuid
from types import SimpleNamespace

from app.services.scan_engine import compile_filters, matching_labels
from tests.test_filters import email, one


def stored_filter(rule: dict, label_id: uuid.UUID) -> SimpleNamespace:
    return SimpleNamespace(id=uuid.uuid4(), name="f", label_id=label_id, rule=rule)


def test_first_matching_filter_per_label_wins():
    bills, newsletters = uuid.uuid4(), uuid.uuid4()
    first = stored_filter(one("subject", "contains", "statement"), bills)
    second = stored_filter(one("has_attachments", "is_true"), bills)
    unrelated = stored_filter(one("is_mailing_list", "is_true"), newsletters)
    miss = stored_filter(one("from_domain", "equals", "example.org"), uuid.uuid4())

    labels = matching_labels(compile_filters([first, second, unrelated, miss]), email())

    assert labels == {bills: first.id, newsletters: unrelated.id}


def test_invalid_stored_rule_is_skipped():
    good = stored_filter(one("subject", "contains", "statement"), uuid.uuid4())
    broken = stored_filter({"items": [{"type": "condition", "field": "gone", "op": "x"}]}, uuid.uuid4())

    compiled = compile_filters([broken, good])

    assert [f.filter_id for f in compiled] == [good.id]
