from app.defaults import FILTERS, LABELS, PROCESSORS
from app.filters.evaluate import compile_rule
from app.filters.rule import Rule, check_mailbox_types
from app.mail.types import Attachment
from app.processors import kinds
from tests.test_filters import email


def test_defaults_are_valid():
    label_keys = {label.key for label in LABELS}
    keys = [d.key for d in (*LABELS, *FILTERS, *PROCESSORS)]
    assert len(keys) == len(set(keys))
    for default in FILTERS:
        assert default.label in label_keys
        check_mailbox_types(Rule.model_validate(default.rule), frozenset(default.mailbox_types))
    for default in PROCESSORS:
        assert set(default.labels) <= label_keys
        assert default.kind in kinds()


def test_credit_card_bills_filter():
    (bills,) = (f for f in FILTERS if f.key == "filter:all_banks_credit_card_bills")
    matches = compile_rule(Rule.model_validate(bills.rule), 0.5)
    pdf = (Attachment("statement.pdf", "application/pdf"),)

    assert matches(email(from_address="YES BANK <estatement@yes.bank.in>", attachments=pdf))
    assert matches(email(from_address="statement@idfcfirst.bank.in", attachments=pdf))
    assert not matches(email(from_address="estatement@yes.bank.in", attachments=()))  # no attachment
    assert not matches(email(from_address="offers@yes.bank.in", attachments=pdf))  # another sender


def test_credit_card_bills_processor():
    (bills,) = (p for p in PROCESSORS if p.key == "processor:credit_card_bills")
    assert bills.labels == ("label:credit_card_bill",)
    assert bills.kind == "credit_card_statements"
