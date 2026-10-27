"""The credit card statements kind: reads the statement PDF with the bank's parser (picked by the
sender's domain), writes the statement and its transactions, and reminds before the due date."""

from datetime import UTC, datetime, time, timedelta

from app.processors import Context, EmailDocument, Notify, ProcessorKind, Skip
from app.processors.cards.datasets import CardTransaction, Statement
from app.processors.cards.parsers.au import AuParser
from app.processors.cards.parsers.axis import AxisParser
from app.processors.cards.parsers.base import StatementParser
from app.processors.cards.parsers.icici import IciciParser
from app.processors.cards.parsers.idfc_first import IdfcFirstParser
from app.processors.cards.parsers.yes_bank import YesBankParser

PARSERS: tuple[StatementParser, ...] = (
    YesBankParser(),
    AxisParser(),
    IciciParser(),
    IdfcFirstParser(),
    AuParser(),
)

REMIND_DAYS_BEFORE = 3


class CreditCardStatements(ProcessorKind):
    key = "credit_card_statements"
    name = "Credit card statements"
    description = (
        "Reads statement PDFs: dues, limits, fees and every transaction. Reminds before the due date."
    )
    version = 3  # 3: AU Bank parser (2: Axis, ICICI and IDFC FIRST; cashback as a transaction kind)
    writes = (Statement, CardTransaction)
    dashboard = "dashboard.json"

    async def process(self, doc: EmailDocument, ctx: Context) -> None:
        domain = doc.sender.domain if doc.sender else ""
        parser = next((p for p in PARSERS if p.handles(domain)), None)
        if parser is None:
            raise Skip(f"No statement parser for {domain or 'this sender'}")
        pdfs = doc.pdfs()
        if not pdfs:
            raise Skip("No PDF attached")
        statement, transactions = parser.parse(await ctx.pdf_text(doc, pdfs[0]))
        ctx.write(statement)
        ctx.write_all(transactions)

        due = datetime.combine(statement.due_date, time(9), tzinfo=UTC)
        if due > datetime.now(UTC):  # no reminders for bills already due (e.g. old emails run again)
            ctx.action(
                Notify(
                    title=f"{statement.card} bill due {statement.due_date:%d %b}",
                    body=f"Total due {statement.currency} {statement.total_due:,}"
                    + (f", minimum {statement.minimum_due:,}" if statement.minimum_due is not None else ""),
                ),
                key="due-reminder",
                at=max(due - timedelta(days=REMIND_DAYS_BEFORE), datetime.now(UTC)),
            )
