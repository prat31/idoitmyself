"""Axis Bank credit card statements. The figures sit in rows of columns under one header row each, and
transaction descriptions are told apart from merchant categories only by runs of spaces."""

import re

from app.processors.cards.datasets import CardTransaction, Statement
from app.processors.cards.parsers.base import StatementParser, money, parse_date

_AMT = r"[\d,]+\.\d{2}"
# "17/09/2099 - 15/10/2099 04/11/2099 15/10/209912,345.67   Dr 250.00   Dr": period, due date,
# generation date, then (run into it) total due and minimum due.
SUMMARY = re.compile(
    r"(?P<start>\d{2}/\d{2}/\d{4}) - (?P<end>\d{2}/\d{2}/\d{4}) (?P<due>\d{2}/\d{2}/\d{4}) "
    rf"(?P<generated>\d{{2}}/\d{{2}}/\d{{4}}) *(?P<total>{_AMT})\s+(?P<total_sign>Dr|Cr)"
    rf"\s+(?P<minimum>{_AMT})"
)
# "...412345******9876 1,00,000.00 87,654.33 20,000.00": card, credit limit, available credit, cash limit.
LIMITS = re.compile(rf"\d{{6}}\*{{6}}(?P<last4>\d{{4}}) +(?P<limit>{_AMT}) +(?P<available>{_AMT}) +{_AMT}")
# Previous balance - payments - credits + purchases + cash advances + other debits = total due.
BALANCES = re.compile(
    rf"^\s*(?P<previous>{_AMT})\s+(?:Dr|Cr) +(?P<payments>{_AMT}) +(?P<credits>{_AMT}) "
    rf"+(?P<purchases>{_AMT}) +(?P<cash>{_AMT}) +(?P<other>{_AMT}) +{_AMT}\s+(?:Dr|Cr)\s*$",
    re.M,
)


class AxisParser(StatementParser):
    key = "axis"
    bank = "Axis Bank"
    sender_domains = ("axis.bank.in", "axisbank.com")
    # "30/09/2099 SOME SHOP PRIVATE L,CITY      CLOTH STORES 1,234.00 Dr 60.00 Cr": the
    # last amount is the cashback earned on it.
    transaction_line = re.compile(
        rf"^\s*(?P<date>\d{{2}}/\d{{2}}/\d{{4}}) (?P<description>.+?) {{2,}}"
        rf"(?:(?P<category>[A-Z][A-Z &/.,-]*?) )?(?P<amount>{_AMT}) (?P<sign>Dr|Cr) {_AMT} (?:Dr|Cr)\s*$",
        re.M,
    )

    def normalise(self, text: str) -> str:
        return re.sub(r"[\t ]", " ", text)  # keep runs of spaces: they separate columns

    def parse(self, text: str) -> tuple[Statement, list[CardTransaction]]:
        text = self.normalise(text)
        summary = SUMMARY.search(text)
        if summary is None:
            raise self.not_a_statement()
        limits = LIMITS.search(text)
        card = self.card(limits["last4"] if limits else None)
        transactions = self.find_transactions(text, card)
        balances = BALANCES.search(text)
        total = money(summary["total"])
        start, end = parse_date(summary["start"]), parse_date(summary["end"])
        return self.statement(
            card=card,
            due_date=parse_date(summary["due"]),  # type: ignore[arg-type]
            total_due=-total if summary["total_sign"] == "Cr" else total,
            transactions=transactions,
            statement_date=parse_date(summary["generated"]),
            period=(start, end) if start and end else None,
            minimum_due=money(summary["minimum"]),
            previous_balance=money(balances["previous"]) if balances else None,
            purchases_and_charges=(
                money(balances["purchases"]) + money(balances["cash"]) + money(balances["other"])
                if balances
                else None
            ),
            payments_and_credits=money(balances["payments"]) + money(balances["credits"])
            if balances
            else None,
            credit_limit=money(limits["limit"]) if limits else None,
            available_credit=money(limits["available"]) if limits else None,
        ), transactions
