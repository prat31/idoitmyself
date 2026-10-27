"""Credit card datasets. Any kind may write them (e.g. a future card-alert email reader)."""

import datetime as dt
from typing import Literal

from app.processors.records import Dimension, Measure, Money, Record, Text, Time


class Statement(Record, dataset="cards.statements", label="Card statements", time="statement_date"):
    bank: str = Dimension(title="Bank")
    card: str = Dimension(title="Card", description="Bank and last four digits, e.g. Acme Bank ••1234")
    statement_date: dt.date = Time(title="Statement date")
    period_start: dt.date | None = Time(None, title="Period from")
    period_end: dt.date | None = Time(None, title="Period to")
    due_date: dt.date = Time(title="Due date")
    total_due: Money = Measure(title="Total due")
    minimum_due: Money | None = Measure(None, title="Minimum due")
    previous_balance: Money | None = Measure(None, title="Previous balance")
    purchases_and_charges: Money | None = Measure(None, title="Purchases & charges")
    payments_and_credits: Money | None = Measure(None, title="Payments & credits")
    credit_limit: Money | None = Measure(None, title="Credit limit")
    available_credit: Money | None = Measure(None, title="Available credit")
    # Interest, fees, charges and taxes on them, net of reversals.
    fees: Money = Measure(title="Fees & charges")
    currency: str = Dimension("INR", title="Currency")


TransactionKind = Literal["purchase", "payment", "refund", "cashback", "fee", "emi"]


class CardTransaction(Record, dataset="cards.transactions", label="Card transactions", time="date"):
    bank: str = Dimension(title="Bank")
    card: str = Dimension(title="Card")
    date: dt.date = Time(title="Date")
    description: str = Text(title="Description")
    category: str | None = Dimension(None, title="Category", description="The bank's merchant category")
    kind: TransactionKind = Dimension(title="Kind")
    direction: Literal["debit", "credit"] = Dimension(title="Debit / credit")
    amount: Money = Measure(title="Amount")  # always positive; see direction
    currency: str = Dimension("INR", title="Currency")
