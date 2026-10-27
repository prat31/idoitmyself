"""AU Bank credit card statements. Each transaction is three lines: the day and description, then
"Mon yy Dr/Cr" (with optional reward points), then the amount. The bill summary holds the balances."""

import re
from datetime import date

from app.processors.cards.datasets import CardTransaction, Statement, TransactionKind
from app.processors.cards.parsers.base import StatementParser, money, parse_date

# "Statement for your credit card ending with 1234 (24 Mar - 23 Apr 2026)"
HEADER = re.compile(
    r"ending with (?P<last4>\d{4}) \((?P<start_day>\d{1,2}) (?P<start_month>[A-Z][a-z]{2}) - "
    r"(?P<end_day>\d{1,2}) (?P<end_month>[A-Z][a-z]{2}) (?P<end_year>\d{4})\)"
)
# "Total bill amount Minimum amount due" then "₹12,345.67 ₹620.00".
BILL = re.compile(
    r"Total bill amount\s+Minimum amount due\s*\n\s*₹(?P<total>[\d,]+\.\d{2})"
    r"\s+₹(?P<minimum>[\d,]+\.\d{2})"
)
DUE = re.compile(r"Payment due date (?P<date>\d{1,2} [A-Z][a-z]{2} \d{4})")
CREDIT_LIMIT = re.compile(r"Total Credit Limit:\s*₹(?P<limit>[\d,]+\.\d{2})")
# "Opening balance ₹1,000.00", "Total spends ₹12,345.67", "Payments & Refunds ₹1,000.00".
SUMMARY = re.compile(
    r"^(?P<label>Opening balance|Total spends|Payments & Refunds) ₹(?P<amount>[\d,]+\.\d{2})$", re.M
)
# AU writes "PYMNT" rather than "payment" in its transaction descriptions.
PYMNT = re.compile(r"\bpymnt\b", re.I)


class AuParser(StatementParser):
    key = "au"
    bank = "AU Bank"
    sender_domains = ("aubank.in",)
    transaction_line = re.compile(
        r"^\s*(?P<day>\d{1,2}) (?P<description>.+?)\n"
        r"\s*(?P<month>[A-Z][a-z]{2}) (?P<year>\d{2}) (?P<sign>Dr|Cr)(?: +\d+ RP)?\n"
        r"\s*[+-]?₹(?P<amount>[\d,]+\.\d{2})\s*$",
        re.M,
    )

    def parse(self, text: str) -> tuple[Statement, list[CardTransaction]]:
        text = self.normalise(text)
        header = HEADER.search(text)
        bill = BILL.search(text)
        due = DUE.search(text)
        if bill is None or due is None:
            raise self.not_a_statement()
        card = self.card(header["last4"] if header else None)
        transactions = self.find_transactions(text, card)
        summary = {match["label"]: money(match["amount"]) for match in SUMMARY.finditer(text)}
        credit_limit = CREDIT_LIMIT.search(text)
        return self.statement(
            card=card,
            due_date=parse_date(due["date"]),  # type: ignore[arg-type]
            total_due=money(bill["total"]),
            transactions=transactions,
            period=self._period(header) if header else None,
            minimum_due=money(bill["minimum"]),
            previous_balance=summary.get("Opening balance"),
            purchases_and_charges=summary.get("Total spends"),
            payments_and_credits=summary.get("Payments & Refunds"),
            credit_limit=money(credit_limit["limit"]) if credit_limit else None,
        ), transactions

    def _period(self, header: re.Match[str]) -> tuple[date, date] | None:
        end = parse_date(f"{header['end_day']} {header['end_month']} {header['end_year']}")
        start = parse_date(f"{header['start_day']} {header['start_month']} {header['end_year']}")
        if start and end and start > end:  # a period that crosses the new year
            start = start.replace(year=start.year - 1)
        return (start, end) if start and end else None

    def find_transactions(self, text: str, card: str) -> list[CardTransaction]:
        if self.transaction_line is None:
            return []
        transactions: list[CardTransaction] = []
        for match in self.transaction_line.finditer(text):
            on = parse_date(f"{match['day']} {match['month']} {match['year']}")
            if on is None:
                continue
            transactions.append(
                self.transaction(
                    card=card,
                    on=on,
                    description=match["description"],
                    amount=money(match["amount"]),
                    credit=match["sign"] == "Cr",
                )
            )
        return transactions

    def classify(self, description: str, direction: str) -> TransactionKind:
        kind = super().classify(description, direction)
        return "payment" if kind == "refund" and PYMNT.search(description) else kind
