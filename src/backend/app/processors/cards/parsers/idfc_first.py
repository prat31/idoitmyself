"""IDFC FIRST Bank credit card statements. pypdf scatters the summary's labels and values, and one
transaction can span several lines (date, description lines, then "amount DR|CR"). The rupee sign
comes out as "r". Opening balance, purchases and payments can't be told apart reliably (several
are often equal), so they're left out; the credit limit isn't on the statement."""

import re

from app.processors.cards.datasets import CardTransaction, Statement
from app.processors.cards.parsers.base import StatementParser, money, parse_date

_AMT = r"[\d,]+\.\d{2}"
_DATE = r"\d{2}/[A-Za-z]{3}/\d{4}"
PERIOD = re.compile(rf"(?P<start>{_DATE}) - (?P<end>{_DATE})")
LONE_DATE = re.compile(rf"^\s*({_DATE})\s*$", re.M)
# The total amount due is the first amount standing alone on its line with DR/CR.
TOTAL = re.compile(rf"^\s*r(?P<total>{_AMT}) (?P<sign>DR|CR)\s*$", re.M)
MINIMUM = re.compile(rf"Minimum Amount Due\s*\n\s*r(?P<minimum>{_AMT}) (?:DR|CR)")
CARD = re.compile(r"Card Number: X+ ?(\d{4})")
TRANSACTION_START = re.compile(r"^(?P<date>\d{1,2} [A-Za-z]{3} \d{2})\b ?(?P<rest>.*)$")
TRANSACTION_END = re.compile(rf"(?P<amount>{_AMT}) (?P<sign>DR|CR)\s*$")


class IdfcFirstParser(StatementParser):
    key = "idfc_first"
    bank = "IDFC FIRST Bank"
    sender_domains = ("idfcfirst.bank.in", "idfcfirstbank.com")

    def parse(self, text: str) -> tuple[Statement, list[CardTransaction]]:
        text = self.normalise(text)
        period = PERIOD.search(text)
        total = TOTAL.search(text)
        if period is None or total is None:
            raise self.not_a_statement()
        start, end = parse_date(period["start"]), parse_date(period["end"])
        assert start and end
        due = min((d for m in LONE_DATE.finditer(text) if (d := parse_date(m[1])) and d > end), default=None)
        if due is None:
            raise self.not_a_statement()
        card_match = CARD.search(text)
        card = self.card(card_match[1] if card_match else None)
        transactions = self.find_transactions(text, card)
        minimum = MINIMUM.search(text)
        amount = money(total["total"])
        return self.statement(
            card=card,
            due_date=due,
            total_due=-amount if total["sign"] == "CR" else amount,
            transactions=transactions,
            statement_date=end,
            period=(start, end),
            minimum_due=money(minimum["minimum"]) if minimum else None,
        ), transactions

    def find_transactions(self, text: str, card: str) -> list[CardTransaction]:
        section = text.split("YOUR TRANSACTIONS", 1)[-1].split("ACTIVE EMI DETAILS", 1)[0]
        transactions: list[CardTransaction] = []
        current: tuple[str, list[str]] | None = None  # date, the lines so far
        for line in section.splitlines():
            if start := TRANSACTION_START.match(line.strip()):
                current = (start["date"], [start["rest"]])
            elif current is not None:
                current[1].append(line)
            else:
                continue
            joined = " ".join(current[1]).strip()
            if end := TRANSACTION_END.search(joined):
                on = parse_date(current[0])
                if on is not None:
                    transactions.append(
                        self.transaction(
                            card=card,
                            on=on,
                            description=joined[: end.start()],
                            amount=money(end["amount"]),
                            credit=end["sign"] == "CR",
                        )
                    )
                current = None
        return transactions
