import datetime as dt
from io import BytesIO

import pytest
from pypdf import PdfWriter

from app.processors import DATASETS, Dimension, Measure, Money, NeedsInput, Record, Time, kinds
from app.processors.context import PDF_PASSWORD
from app.processors.document import Address
from app.processors.outcomes import Fail
from app.processors.testing import make_document, run_kind
from app.schemas.dataset import SeriesQuery
from app.services.dashboards import kind_spec
from app.services.datasets import DatasetQueryError, series


class Holding(Record, dataset="test.holdings", kind="snapshot", key="symbol"):
    symbol: str = Dimension(title="Symbol")
    as_of: dt.date = Time(title="As of")
    value: Money = Measure(title="Value")
    units: float | None = Measure(None, title="Units")


def test_dataset_fields_and_roles():
    dataset = DATASETS["test.holdings"]
    assert (dataset.kind, dataset.time_field, dataset.key_field) == ("snapshot", "as_of", "symbol")
    assert [(f.name, f.type, f.role.value) for f in dataset.fields] == [
        ("symbol", "text", "dimension"),
        ("as_of", "date", "time"),
        ("value", "money", "measure"),
        ("units", "number", "measure"),
    ]
    record = Holding(symbol="ABC", as_of=dt.date(2026, 10, 1), value="12.50")
    assert record.occurred_at() == dt.datetime(2026, 10, 1, tzinfo=dt.UTC)
    assert record.record_key() == "ABC"


def test_dataset_needs_its_time_field():
    with pytest.raises(TypeError, match="Time field"):

        class _NoTime(Record, dataset="test.no_time"):
            name: str = Dimension(title="Name")


def test_kinds_are_discovered_and_their_dashboards_are_valid():
    assert "credit_card_statements" in kinds()
    for key, kind in kinds().items():
        if kind.dashboard:
            assert kind_spec(key) is not None


async def test_query_rejects_unknown_or_misused_fields():
    with pytest.raises(DatasetQueryError, match="no field"):
        await series(None, SeriesQuery(dataset="test.holdings", measure="nope"))  # type: ignore[arg-type]
    with pytest.raises(DatasetQueryError, match="can't be used to aggregate"):
        await series(None, SeriesQuery(dataset="test.holdings", measure="symbol"))  # type: ignore[arg-type]
    with pytest.raises(DatasetQueryError, match="Unknown dataset"):
        await series(None, SeriesQuery(dataset="nope"))  # type: ignore[arg-type]


def test_address_parsing():
    (address,) = Address.parse_all('"YES BANK" <EStatement@Yes.Bank.in>')
    assert (address.name, address.address, address.domain) == (
        "YES BANK",
        "estatement@yes.bank.in",
        "yes.bank.in",
    )


def _encrypted_pdf(password: str) -> bytes:
    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)
    writer.encrypt(password, algorithm="AES-256")
    buffer = BytesIO()
    writer.write(buffer)
    return buffer.getvalue()


async def test_protected_pdf_asks_for_its_password():
    data = _encrypted_pdf("31129999")
    doc = make_document(
        sender="estatement@yes.bank.in",
        attachments=[("s.pdf", "application/pdf")],
        labels=["credit_card_bill"],
    )

    async def read(_attachment):
        return data

    doc.bind(read)
    kind = kinds()["credit_card_statements"]
    scope = "estatement@yes.bank.in|credit_card_bill"

    with pytest.raises(NeedsInput) as missing:
        await run_kind(kind, doc)
    assert (missing.value.name, missing.value.scope, missing.value.wrong) == (PDF_PASSWORD, scope, False)
    assert missing.value.prompt == "PDF password for estatement@yes.bank.in (Credit card bill)"

    with pytest.raises(NeedsInput) as wrong:
        await run_kind(kind, doc, secrets={(PDF_PASSWORD, scope): "01011990"})
    assert wrong.value.wrong

    # The right password opens it; this blank page has no text to read.
    with pytest.raises(Fail, match="no text"):
        await run_kind(kind, doc, secrets={(PDF_PASSWORD, scope): "31129999"})
