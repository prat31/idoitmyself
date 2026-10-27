"""ICICI Bank credit card statements. pypdf puts the labels and their values in separate blocks, so
the figures are read from their own patterns: the "`"-prefixed amounts (the rupee sign in this
font) under known header rows, and dates written as "October 12, 2026"."""

import re

from app.processors.cards.datasets import CardTransaction, Statement
from app.processors.cards.parsers.base import StatementParser, money, parse_date

_AMT = r"[\d,]+\.\d{2}"
_LONG_DATE = r"[A-Z][a-z]+ \d{1,2}, \d{4}"
PERIOD = re.compile(rf"Statement period\s*:\s*(?P<start>{_LONG_DATE}) to (?P<end>{_LONG_DATE})")
# Total amount due, then minimum amount due: the first two lines holding only a "`" amount each.
DUES = re.compile(rf"^`(?P<total>{_AMT})\s*\n`(?P<minimum>{_AMT})\s*$", re.M)
# The statement date and the due date stand on lines of their own.
LONE_DATE = re.compile(rf"^({_LONG_DATE})\s*$", re.M)
LIMITS = re.compile(rf"Credit Limit \(Including cash\)[^\n]*\n`(?P<limit>{_AMT}) `(?P<available>{_AMT})")
BALANCES = re.compile(
    r"Previous Balance Purchases / Charges Cash Advances Payments / Credits\s*\n"
    rf"`(?P<previous>{_AMT}) `(?P<purchases>{_AMT}) `(?P<cash>{_AMT}) `(?P<payments>{_AMT})"
)
CARD = re.compile(r"^\d{4}X{8}(\d{4})\s*$", re.M)


class IciciParser(StatementParser):
    key = "icici"
    bank = "ICICI Bank"
    sender_domains = ("icici.bank.in", "icicibank.com")
    # "27/09/2099 11111111111 Interest Amount Amortization - <3/24> 0 400.00": date, serial number,
    # details, reward points, (international amount,) amount, and "CR" for credits.
    transaction_line = re.compile(
        rf"^(?P<date>\d{{2}}/\d{{2}}/\d{{4}}) \d{{6,}} (?P<description>.+?) -?\d+ (?:{_AMT} )?"
        rf"(?P<amount>{_AMT})(?: (?P<sign>CR))?\s*$",
        re.M,
    )

    def parse(self, text: str) -> tuple[Statement, list[CardTransaction]]:
        text = self.normalise(text)
        period = PERIOD.search(text)
        dues = DUES.search(text)
        if period is None or dues is None:
            raise self.not_a_statement()
        start, end = parse_date(period["start"]), parse_date(period["end"])
        assert start and end
        # The due date is the first lone date after the statement's end.
        due = min((d for m in LONE_DATE.finditer(text) if (d := parse_date(m[1])) and d > end), default=None)
        if due is None:
            raise self.not_a_statement()
        card_match = CARD.search(text)
        card = self.card(card_match[1] if card_match else None)
        transactions = self.find_transactions(text, card)
        limits = LIMITS.search(text)
        balances = BALANCES.search(text)
        return self.statement(
            card=card,
            due_date=due,
            total_due=money(dues["total"]),
            transactions=transactions,
            statement_date=end,
            period=(start, end),
            minimum_due=money(dues["minimum"]),
            previous_balance=money(balances["previous"]) if balances else None,
            purchases_and_charges=money(balances["purchases"]) + money(balances["cash"])
            if balances
            else None,
            payments_and_credits=money(balances["payments"]) if balances else None,
            credit_limit=money(limits["limit"]) if limits else None,
            available_credit=money(limits["available"]) if limits else None,
        ), transactions
