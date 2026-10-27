"""The parent of every bank's statement parser, and the helpers they share.

Banks lay their statements out very differently, and pypdf's text keeps that layout's quirks (labels
far from their values, rows run together). So a bank's parser reads its own layout, building on:
- `parse_amount`, `parse_dates`: amounts with Indian or international grouping and Dr/Cr; dates as
  dd/mm/yyyy, dd/Mon/yyyy, "18 Oct 26" or "October 12, 2026";
- `statement(...)`: the Statement record, with the card's name and the fees summed from transactions;
- `transaction(...)`: a CardTransaction, classified as purchase, payment, refund, cashback, fee or EMI.

Banks whose statements label each figure on its own line can instead set `phrases` (regexes for each
figure's label) and `transaction_line`, and use the default `parse` (Yes Bank does)."""

import re
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import ClassVar

from app.processors.cards.datasets import CardTransaction, Statement, TransactionKind
from app.processors.outcomes import Fail

# How far after a phrase its value may be (PDF text often puts a line break or other words between).
VALUE_WINDOW = 80

_AMOUNT = re.compile(
    r"(?:₹|rs\.?|inr)?\s*(\d{1,3}(?:,\d{2,3})+(?:\.\d{1,2})?|\d+(?:\.\d{1,2})?)\s*(cr|dr)?\b", re.I
)
_MONTHS = {m: i for i, m in enumerate("jan feb mar apr may jun jul aug sep oct nov dec".split(), start=1)}
_DATE = re.compile(
    r"\b(?:(?P<d1>\d{1,2})[/.-](?P<m1>\d{1,2})[/.-](?P<y1>\d{4})"  # 20/10/2026
    r"|(?P<d2>\d{1,2})[/ -](?P<mon2>[A-Za-z]{3,9})[/ -](?P<y2>\d{4}|\d{2})"  # 20/Oct/2026, 18 Oct 26
    r"|(?P<mon3>[A-Za-z]{3,9}) (?P<d3>\d{1,2}), (?P<y3>\d{4}))\b"  # October 12, 2026
)
_MASKED_CARD = re.compile(r"[\dX*]{4,}[X*]{4,}[\dX*]*?(\d{4})\b", re.I)

FEE_PATTERN = re.compile(
    r"\b(fee|fees|charges?|interest|finance|gst|goods\s*&\s*services\s*tax|igst|cgst|sgst|"
    r"emi\s*int|late\s*payment|over\s*limit|annual|joining|surcharge)\b",
    re.I,
)
EMI_PATTERN = re.compile(r"\bemi\s*prin|principal\s+amount\s+amortization", re.I)
CASHBACK_PATTERN = re.compile(r"\bcash\s*back\b", re.I)
PAYMENT_PATTERN = re.compile(r"\bpayment\b", re.I)


def parse_amount(raw: str) -> Decimal | None:
    """The first amount in `raw` (Indian or international digit grouping); "Cr" makes it negative."""
    match = _AMOUNT.search(raw)
    if not match:
        return None
    try:
        value = Decimal(match.group(1).replace(",", ""))
    except InvalidOperation:
        return None
    return -value if (match.group(2) or "").lower() == "cr" else value


def money(raw: str) -> Decimal:
    """A plain amount like "1,20,000.00" (no sign, no currency)."""
    return Decimal(raw.replace(",", ""))


def parse_dates(raw: str) -> list[date]:
    """Every date in `raw`, in order (see the module docstring for the formats)."""
    found: list[date] = []
    for m in _DATE.finditer(raw):
        try:
            if m["d1"]:
                found.append(date(int(m["y1"]), int(m["m1"]), int(m["d1"])))
                continue
            name, day, year = (m["mon2"], m["d2"], m["y2"]) if m["d2"] else (m["mon3"], m["d3"], m["y3"])
            month = _MONTHS.get(name[:3].lower())
            if month is None:
                continue
            found.append(date(int(year) + (2000 if len(year) == 2 else 0), month, int(day)))
        except ValueError:
            continue
    return found


def parse_date(raw: str) -> date | None:
    dates = parse_dates(raw)
    return dates[0] if dates else None


class StatementParser:
    """A child sets `key`, `bank` and `sender_domains`, and either overrides `parse` or sets:
    - `phrases`: field -> regexes for the statement's labels (multiline; tried in order). Fields:
      card_number, statement_date, statement_period, due_date, total_due, minimum_due,
      previous_balance, purchases_and_charges, payments_and_credits, credit_limit, available_credit;
    - `transaction_line`: a regex with named groups date, description and amount, and optionally
      sign (Dr/Cr; none means a debit) and category."""

    key: ClassVar[str]
    bank: ClassVar[str]
    sender_domains: ClassVar[tuple[str, ...]]
    phrases: ClassVar[dict[str, tuple[str, ...]]] = {}
    transaction_line: ClassVar[re.Pattern[str] | None] = None
    fee_pattern: ClassVar[re.Pattern[str]] = FEE_PATTERN
    emi_pattern: ClassVar[re.Pattern[str]] = EMI_PATTERN

    def handles(self, domain: str) -> bool:
        return any(domain == d or domain.endswith(f".{d}") for d in self.sender_domains)

    def normalise(self, text: str) -> str:
        """Collapse runs of spaces (a bank whose columns are told apart by them overrides this)."""
        return re.sub(r"[ \t ]+", " ", text)

    def card(self, last4: str | None) -> str:
        return f"{self.bank} ••{last4}" if last4 else self.bank

    def not_a_statement(self) -> Fail:
        return Fail(f"Doesn't look like a credit card statement from {self.bank} (no due date or total due)")

    # --- building records ------------------------------------------------------------------------

    def statement(
        self,
        *,
        card: str,
        due_date: date,
        total_due: Decimal,
        transactions: list[CardTransaction],
        statement_date: date | None = None,
        period: tuple[date, date] | None = None,
        minimum_due: Decimal | None = None,
        previous_balance: Decimal | None = None,
        purchases_and_charges: Decimal | None = None,
        payments_and_credits: Decimal | None = None,
        credit_limit: Decimal | None = None,
        available_credit: Decimal | None = None,
    ) -> Statement:
        return Statement(
            bank=self.bank,
            card=card,
            statement_date=statement_date or (period[1] if period else due_date),
            period_start=period[0] if period else None,
            period_end=period[1] if period else None,
            due_date=due_date,
            total_due=total_due,
            minimum_due=minimum_due,
            previous_balance=previous_balance,
            purchases_and_charges=purchases_and_charges,
            payments_and_credits=abs(payments_and_credits) if payments_and_credits is not None else None,
            credit_limit=credit_limit,
            available_credit=available_credit,
            fees=sum(
                (t.amount if t.direction == "debit" else -t.amount for t in transactions if t.kind == "fee"),
                Decimal("0"),
            ),
        )

    def classify(self, description: str, direction: str) -> TransactionKind:
        if self.fee_pattern.search(description):
            return "fee"  # including a fee's reversal (a credit)
        if direction == "credit":
            if CASHBACK_PATTERN.search(description):
                return "cashback"
            return "payment" if PAYMENT_PATTERN.search(description) else "refund"
        return "emi" if self.emi_pattern.search(description) else "purchase"

    def transaction(
        self,
        *,
        card: str,
        on: date,
        description: str,
        amount: Decimal,
        credit: bool,
        category: str | None = None,
    ) -> CardTransaction:
        description = re.sub(r"\s+", " ", description).strip(" -")
        direction = "credit" if credit else "debit"
        return CardTransaction(
            bank=self.bank,
            card=card,
            date=on,
            description=description,
            category=(category or "").strip() or None,
            kind=self.classify(description, direction),
            direction=direction,
            amount=abs(amount),
        )

    # --- the default, phrase-based layout --------------------------------------------------------

    def parse(self, text: str) -> tuple[Statement, list[CardTransaction]]:
        text = self.normalise(text)
        due = self.find_date(text, "due_date")
        total = self.find_amount(text, "total_due")
        if due is None or total is None:
            raise self.not_a_statement()
        card = self.card(self.find_card_last4(text))
        period = self.find_dates(text, "statement_period")
        transactions = self.find_transactions(text, card)
        return self.statement(
            card=card,
            due_date=due,
            total_due=total,
            transactions=transactions,
            statement_date=self.find_date(text, "statement_date"),
            period=(period[0], period[1]) if len(period) > 1 else None,
            minimum_due=self.find_amount(text, "minimum_due"),
            previous_balance=self.find_amount(text, "previous_balance"),
            purchases_and_charges=self.find_amount(text, "purchases_and_charges"),
            payments_and_credits=self.find_amount(text, "payments_and_credits"),
            credit_limit=self.find_amount(text, "credit_limit"),
            available_credit=self.find_amount(text, "available_credit"),
        ), transactions

    def _after(self, text: str, field: str) -> list[str]:
        """The text right after each match of the field's phrases, in phrase order."""
        return [
            text[match.end() : match.end() + VALUE_WINDOW]
            for phrase in self.phrases.get(field, ())
            for match in re.finditer(phrase, text, re.I | re.M)
        ]

    def find_amount(self, text: str, field: str) -> Decimal | None:
        for window in self._after(text, field):
            if (value := parse_amount(window)) is not None:
                return value
        return None

    def find_dates(self, text: str, field: str) -> list[date]:
        for window in self._after(text, field):
            if dates := parse_dates(window):
                return dates
        return []

    def find_date(self, text: str, field: str) -> date | None:
        dates = self.find_dates(text, field)
        return dates[0] if dates else None

    def find_card_last4(self, text: str) -> str | None:
        for window in self._after(text, "card_number"):
            if match := _MASKED_CARD.search(window):
                return match.group(1)
        return None

    def find_transactions(self, text: str, card: str) -> list[CardTransaction]:
        if self.transaction_line is None:
            return []
        transactions: list[CardTransaction] = []
        for match in self.transaction_line.finditer(text):
            on = parse_date(match["date"])
            amount = parse_amount(match["amount"])
            if on is None or amount is None:
                continue
            groups = match.groupdict()
            transactions.append(
                self.transaction(
                    card=card,
                    on=on,
                    description=match["description"],
                    amount=amount,
                    credit=(groups.get("sign") or "").lower() == "cr",
                    category=groups.get("category"),
                )
            )
        return transactions
