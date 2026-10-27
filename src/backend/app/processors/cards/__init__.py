"""Credit cards: statement PDFs into the cards.statements and cards.transactions datasets."""

from app.processors.cards.statements import CreditCardStatements

__all__ = ["CreditCardStatements"]
