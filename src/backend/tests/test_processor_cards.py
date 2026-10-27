from datetime import date
from decimal import Decimal

import pytest

from app.processors import Notify, Skip, kinds
from app.processors.cards.datasets import CardTransaction, Statement
from app.processors.outcomes import Fail
from app.processors.testing import make_document, run_kind

# The layout of a Yes Bank e-statement's text (as pypdf extracts it), with made-up figures.
YES_BANK_TEXT = """\
Statement for YES BANK Card Number 4111XXXXXXXX1234
Statement Summary
Previous Balance :
Rs. 12,000.50 Dr
Current Purchases / Cash Advance
& Other Charges :
Rs. 4,321.00 Dr
Payment & Credits Received :
Rs. 9,000.00 Cr
Statement Period:
21/09/2099 To 20/10/2099
Statement Date : 20/10/2099
Total Amount Due:
Rs. 7,321.50
Minimum Amount Due:
Rs. 1,500.00
Payment Due Date: 09/11/2099
Credit Limit:
Rs. 2,00,000.00
Available Credit Limit:
Rs. 1,92,678.50
Date Transaction Details Merchant Category Amount (Rs.)
28/09/2099 UPI_GROCER IND - Ref No:RT1234567890 Retail Outlet Services 1,209.00 Dr
29/09/2099 PAYMENT RECEIVED BBPS - Ref No: 0999999998 9,000.00 Cr
20/10/2099 EMI PRIN FOR UPI_SHOP (003/003) - Ref No:2026208200 2,000.00 Dr
20/10/2099 EMI INT-UPI_SHOP (003/003) - Ref No: 2026208200 40.00 Dr
20/10/2099 LATE PAYMENT FEE 500.00 Dr
20/10/2099 GOODS & SERVICES TAX - GST @ 18% 97.20 Dr
20/10/2099 LATE PAYMENT FEE REVERSAL 500.00 Cr
"""

KIND = kinds()["credit_card_statements"]


def statement_email(sender: str = "YES BANK <estatement@yes.bank.in>", pdf: bool = True):
    return make_document(
        sender=sender,
        subject="Your credit card statement",
        attachments=[("statement.pdf", "application/pdf")] if pdf else [],
        labels=["credit_card_bill"],
    )


async def test_yes_bank_statement_and_transactions():
    ctx = await run_kind(KIND, statement_email(), pdf_text=YES_BANK_TEXT)

    statement, *transactions = ctx.records
    assert isinstance(statement, Statement)
    assert statement.card == "Yes Bank ••1234"
    assert (statement.statement_date, statement.due_date) == (date(2099, 10, 20), date(2099, 11, 9))
    assert (statement.period_start, statement.period_end) == (date(2099, 9, 21), date(2099, 10, 20))
    assert statement.total_due == Decimal("7321.50")
    assert statement.minimum_due == Decimal("1500.00")
    assert statement.previous_balance == Decimal("12000.50")
    assert statement.payments_and_credits == Decimal("9000.00")
    assert statement.credit_limit == Decimal("200000.00")
    assert statement.available_credit == Decimal("192678.50")
    assert statement.fees == Decimal("137.20")  # 40 + 500 + 97.20 - 500 reversed

    assert all(isinstance(t, CardTransaction) for t in transactions)
    assert [(t.description, t.category, t.kind, t.direction, t.amount) for t in transactions] == [
        ("UPI_GROCER IND", "Retail Outlet Services", "purchase", "debit", Decimal("1209.00")),
        ("PAYMENT RECEIVED BBPS", None, "payment", "credit", Decimal("9000.00")),
        ("EMI PRIN FOR UPI_SHOP (003/003)", None, "emi", "debit", Decimal("2000.00")),
        ("EMI INT-UPI_SHOP (003/003)", None, "fee", "debit", Decimal("40.00")),
        ("LATE PAYMENT FEE", None, "fee", "debit", Decimal("500.00")),
        ("GOODS & SERVICES TAX - GST @ 18%", None, "fee", "debit", Decimal("97.20")),
        ("LATE PAYMENT FEE REVERSAL", None, "fee", "credit", Decimal("500.00")),
    ]


async def test_due_reminder_before_the_due_date():
    ctx = await run_kind(KIND, statement_email(), pdf_text=YES_BANK_TEXT)

    (planned,) = ctx.actions
    assert planned.key == "due-reminder"
    assert isinstance(planned.action, Notify)
    assert planned.action.title == "Yes Bank ••1234 bill due 09 Nov"
    assert planned.at is not None and planned.at.date() == date(2099, 11, 6)


async def test_no_reminder_for_a_bill_already_due():
    old = YES_BANK_TEXT.replace("Payment Due Date: 09/11/2099", "Payment Due Date: 09/11/2020")
    ctx = await run_kind(KIND, statement_email(), pdf_text=old)
    assert ctx.actions == []


@pytest.mark.parametrize(
    ("email", "reason"),
    [
        (statement_email(sender="statements@unknown-bank.in"), "No statement parser"),
        (statement_email(pdf=False), "No PDF attached"),
    ],
)
async def test_skips(email, reason):
    with pytest.raises(Skip, match=reason):
        await run_kind(KIND, email, pdf_text=YES_BANK_TEXT)


async def test_not_a_statement_fails():
    with pytest.raises(Fail):
        await run_kind(KIND, statement_email(), pdf_text="Your card ending 1234 has been dispatched.")


# --- Axis, ICICI and IDFC FIRST: synthetic text in each bank's layout (made-up figures) ----------

AXIS_TEXT = """\
PAYMENT SUMMARY
Total Payment Due Minimum Payment Due Statement Period Payment Due Date Statement Generation Date
17/09/2099 - 15/10/2099 04/11/2099 15/10/209912,345.67   Dr 250.00   Dr
Credit Card Number Credit Limit Available Credit Limit Available Cash Limit
Auto-Debit facility on 18601234567412345******9876 1,00,000.00 87,654.33 20,000.00
Previous Balance - Payments - Credits + Purchase + Cash Advance + Other Debit&Charges =Total Payment Due
1,000.00  Dr 1,000.00 100.00 12,000.00 0.00 445.67 12,345.67   Dr
DATE TRANSACTION DETAILS MERCHANT CATEGORY AMOUNT (Rs.) CASHBACK EARNED
   Card No: 412345******9876 Name A CARDHOLDER
16/09/2099 BBPS PAYMENT RECEIVED - DP0000000000    1,000.00 Cr 0.00 Dr
30/09/2099 SOME SHOP PRIVATE L,BANGALORE             CLOTH STORES 12,000.00 Dr 600.00 Cr
05/10/2099 LATE PAYMENT FEE                           377.67 Dr 0.00 Dr
05/10/2099 GST ON LATE PAYMENT FEE                    68.00 Dr 0.00 Dr
11/10/2099 CASHBACK CREDIT SEP99-SHOP:100              100.00 Cr 0.00 Dr
**** End of Statement ****
"""

ICICI_TEXT = """\
PAYMENT DUE DATE
STATEMENT DATE
Total Amount due
Minimum Amount due
0 7
`5,432.10
`1,000.00
SPENDS OVERVIEW
October 12, 2099
October 30, 2099
Date SerNo. Transaction Details Reward
1234XXXXXXXX5678
14/09/2099 11111111111 BBPS Payment received 0 2,000.00 CR
20/09/2099 22222222222 SOME ONLINE STORE 123 BANGALORE 12 3,000.00
27/09/2099 33333333333 Interest Amount Amortization - <3/24> 0 400.00
27/09/2099 44444444444 IGST-CI@18% 0 72.00
27/09/2099 55555555555 Principal Amount Amortization - <3/24> 0 1,960.10
Credit Limit (Including cash) Available Credit (Including cash) Cash Limit Available Cash
`1,20,000.00 `1,14,567.90 `12,000.00 `12,000.00
Statement period : September 13, 2099 to October 12, 2099
Previous Balance Purchases / Charges Cash Advances Payments / Credits
`2,000.00 `5,432.10 `0.00 `2,000.00
"""

IDFC_TEXT = """\
20/Sep/2099 - 19/Oct/2099
Credit Card Statement
Total Amount Due
Payment Due Date
03/Nov/2099
r9,000.00
r7,500.00
r9,000.00
r0.00
r7,500.00 DR
r7,500.00 DR
Minimum Amount Due
 r1,200.00 DR
YOUR TRANSACTIONS
Card Number: XXXX 4321
Purchases, EMIs & Other Debits 
18 Oct 99
Quick Cash on Credit Card - 
Interest Amount Amortization - 
<4/12>
 600.00 DR
19 Oct 99 IGST  108.00 DR
18 Oct 99
Quick Cash on Credit Card - 
Principal Amount Amortization - 
<4/12>
 6,792.00 DR
Payments & Other Credits 
29 Sep 99 BillDesk BBPS CC Payment/DP0000000000 9,000.00 CR
ACTIVE EMI DETAILS
QUICK CASH
99,000.00 5,499.08 10% 1,04,499.08 19 JUN 99 19 MAY 00 12 8,703.67 8 69,629.36
"""


AU_TEXT = """\
Hello, A CARDHOLDER
SOME ADDRESS, CITY 000000
Statement for your credit card ending with 4321 (24 Mar - 23 Apr 2099)
Your Transactions
10 PYMNT RCV BBPS
Apr 99 Cr
+₹2,000.00
20 SOME ONLINE STORE
Apr 99 Dr        40 RP
₹3,000.00
Convert to EMI
21 TRAVEL BOOKING MUMBAI IN
Apr 99 Dr
₹7,345.67
Convert to EMI
Page 1 of 2
Your Credit Card bill
Total bill amount Minimum amount due
₹10,345.67 ₹520.00
     Total Credit Limit: ₹2,00,000.00
Payment due date 13 May 2099 Pay Now
Bill summary
Opening balance ₹2,000.00
Total spends ₹10,345.67
Payments & Refunds ₹2,000.00
EMIs ₹0.00
Fee & Charges (Including ₹0.00
Reversals)
Total amount due ₹10,345.67
"""


def summary(ctx):
    statement, *transactions = ctx.records
    return statement, [(t.description, t.category, t.kind, t.direction, t.amount) for t in transactions]


async def test_axis_statement():
    email = statement_email(sender="cc.statements@axis.bank.in")
    statement, transactions = summary(await run_kind(KIND, email, pdf_text=AXIS_TEXT))

    assert statement.card == "Axis Bank ••9876"
    assert (statement.period_start, statement.period_end) == (date(2099, 9, 17), date(2099, 10, 15))
    assert (statement.statement_date, statement.due_date) == (date(2099, 10, 15), date(2099, 11, 4))
    assert (statement.total_due, statement.minimum_due) == (Decimal("12345.67"), Decimal("250.00"))
    assert statement.previous_balance == Decimal("1000.00")
    assert statement.payments_and_credits == Decimal("1100.00")  # payments + credits
    assert statement.purchases_and_charges == Decimal("12445.67")  # purchases + cash + other debits
    assert (statement.credit_limit, statement.available_credit) == (Decimal("100000.00"), Decimal("87654.33"))
    assert statement.fees == Decimal("445.67")
    assert transactions == [
        ("BBPS PAYMENT RECEIVED - DP0000000000", None, "payment", "credit", Decimal("1000.00")),
        ("SOME SHOP PRIVATE L,BANGALORE", "CLOTH STORES", "purchase", "debit", Decimal("12000.00")),
        ("LATE PAYMENT FEE", None, "fee", "debit", Decimal("377.67")),
        ("GST ON LATE PAYMENT FEE", None, "fee", "debit", Decimal("68.00")),
        ("CASHBACK CREDIT SEP99-SHOP:100", None, "cashback", "credit", Decimal("100.00")),
    ]


async def test_icici_statement():
    email = statement_email(sender="credit_cards@icici.bank.in")
    statement, transactions = summary(await run_kind(KIND, email, pdf_text=ICICI_TEXT))

    assert statement.card == "ICICI Bank ••5678"
    assert (statement.period_start, statement.period_end) == (date(2099, 9, 13), date(2099, 10, 12))
    assert (statement.statement_date, statement.due_date) == (date(2099, 10, 12), date(2099, 10, 30))
    assert (statement.total_due, statement.minimum_due) == (Decimal("5432.10"), Decimal("1000.00"))
    assert (statement.previous_balance, statement.payments_and_credits) == (
        Decimal("2000.00"),
        Decimal("2000.00"),
    )
    assert statement.purchases_and_charges == Decimal("5432.10")
    assert (statement.credit_limit, statement.available_credit) == (
        Decimal("120000.00"),
        Decimal("114567.90"),
    )
    assert statement.fees == Decimal("472.00")
    assert transactions == [
        ("BBPS Payment received", None, "payment", "credit", Decimal("2000.00")),
        ("SOME ONLINE STORE 123 BANGALORE", None, "purchase", "debit", Decimal("3000.00")),
        ("Interest Amount Amortization - <3/24>", None, "fee", "debit", Decimal("400.00")),
        ("IGST-CI@18%", None, "fee", "debit", Decimal("72.00")),
        ("Principal Amount Amortization - <3/24>", None, "emi", "debit", Decimal("1960.10")),
    ]


async def test_idfc_first_statement():
    email = statement_email(sender="IDFC FIRST Bank <statement@idfcfirst.bank.in>")
    statement, transactions = summary(await run_kind(KIND, email, pdf_text=IDFC_TEXT))

    assert statement.card == "IDFC FIRST Bank ••4321"
    assert (statement.period_start, statement.period_end) == (date(2099, 9, 20), date(2099, 10, 19))
    assert (statement.statement_date, statement.due_date) == (date(2099, 10, 19), date(2099, 11, 3))
    assert (statement.total_due, statement.minimum_due) == (Decimal("7500.00"), Decimal("1200.00"))
    # The summary's other figures can't be told apart reliably in this layout: left out.
    assert (statement.previous_balance, statement.credit_limit) == (None, None)
    assert statement.fees == Decimal("708.00")
    assert transactions == [
        (
            "Quick Cash on Credit Card - Interest Amount Amortization - <4/12>",
            None,
            "fee",
            "debit",
            Decimal("600.00"),
        ),
        ("IGST", None, "fee", "debit", Decimal("108.00")),
        (
            "Quick Cash on Credit Card - Principal Amount Amortization - <4/12>",
            None,
            "emi",
            "debit",
            Decimal("6792.00"),
        ),
        ("BillDesk BBPS CC Payment/DP0000000000", None, "payment", "credit", Decimal("9000.00")),
    ]


async def test_au_statement():
    email = statement_email(sender="AU Bank <creditcard.priority@aubank.in>")
    statement, transactions = summary(await run_kind(KIND, email, pdf_text=AU_TEXT))

    assert statement.card == "AU Bank ••4321"
    assert (statement.period_start, statement.period_end) == (date(2099, 3, 24), date(2099, 4, 23))
    assert (statement.statement_date, statement.due_date) == (date(2099, 4, 23), date(2099, 5, 13))
    assert (statement.total_due, statement.minimum_due) == (Decimal("10345.67"), Decimal("520.00"))
    assert (statement.previous_balance, statement.credit_limit) == (Decimal("2000.00"), Decimal("200000.00"))
    assert statement.purchases_and_charges == Decimal("10345.67")
    assert statement.payments_and_credits == Decimal("2000.00")
    assert statement.available_credit is None
    assert statement.fees == Decimal("0")
    assert transactions == [
        ("PYMNT RCV BBPS", None, "payment", "credit", Decimal("2000.00")),
        ("SOME ONLINE STORE", None, "purchase", "debit", Decimal("3000.00")),
        ("TRAVEL BOOKING MUMBAI IN", None, "purchase", "debit", Decimal("7345.67")),
    ]


async def test_au_period_crossing_the_new_year():
    text = AU_TEXT.replace("(24 Mar - 23 Apr 2099)", "(24 Dec - 23 Jan 2099)")
    statement, _ = summary(
        await run_kind(KIND, statement_email(sender="creditcard.priority@aubank.in"), pdf_text=text)
    )
    assert (statement.period_start, statement.period_end) == (date(2098, 12, 24), date(2099, 1, 23))


@pytest.mark.parametrize(
    ("sender", "text"),
    [
        ("cc.statements@axis.bank.in", "Your Axis Bank card offers"),
        ("credit_cards@icici.bank.in", "Statement period : nothing here"),
        ("statement@idfcfirst.bank.in", "20/Sep/2099 - 19/Oct/2099 but no amounts"),
        ("creditcard.priority@aubank.in", "Statement for your credit card ending with 4321"),
    ],
)
async def test_other_banks_fail_on_other_documents(sender, text):
    with pytest.raises(Fail):
        await run_kind(KIND, statement_email(sender=sender), pdf_text=text)


def test_date_formats():
    from app.processors.cards.parsers.base import parse_dates

    assert parse_dates("20/10/2099, 20/Oct/2099, 18 Oct 99, October 12, 2099 and 31/02/2099") == [
        date(2099, 10, 20),
        date(2099, 10, 20),
        date(2099, 10, 18),
        date(2099, 10, 12),
    ]
