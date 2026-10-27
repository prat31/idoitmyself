"""Yes Bank credit card statements (the e-statement PDF, protected with the cardholder's date of birth
as DDMMYYYY)."""

import re

from app.processors.cards.parsers.base import StatementParser


class YesBankParser(StatementParser):
    key = "yes_bank"
    bank = "Yes Bank"
    sender_domains = ("yesbank.in", "yes.bank.in")
    phrases = {
        "card_number": (r"Card Number",),
        "statement_date": (r"^Statement Date\s*:",),
        "statement_period": (r"^Statement Period\s*:",),
        "due_date": (r"^Payment Due Date\s*:",),
        "total_due": (r"^Total Amount Due\s*:",),
        "minimum_due": (r"^Minimum Amount Due\s*:",),
        "previous_balance": (r"^Previous Balance\s*:",),
        "purchases_and_charges": (r"&\s*Other Charges\s*:",),
        "payments_and_credits": (r"^Payment & Credits Received\s*:",),
        "credit_limit": (r"^Credit Limit\s*:",),
        "available_credit": (r"^Available Credit Limit\s*:",),
    }
    # "28/09/2099 UPI_GROCER IND - Ref No: RT0000… Retail Outlet Services 250.00 Dr": the description
    # comes before the reference number, the merchant category (if any) after it.
    transaction_line = re.compile(
        r"^(?P<date>\d{2}/\d{2}/\d{4}) (?P<description>.+?)"
        r"(?: - Ref No: ?\S+(?: (?P<category>[A-Za-z][A-Za-z &/,.-]*?))?)?"
        r" (?P<amount>[\d,]+\.\d{2}) (?P<sign>Dr|Cr)$",
        re.M,
    )
