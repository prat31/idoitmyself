"""Processors: code that runs on emails that newly get one of its labels, reads them (EmailDocument)
and writes records into datasets, asks for side effects, or asks the user for input. Everything here
is deterministic: nothing is sent to any AI.

What a kind needs is importable from here; see .claude/skills/add-processor."""

from app.processors.actions import Notify
from app.processors.context import Context
from app.processors.document import Address, Attachment, EmailDocument, EmailLabel
from app.processors.kinds import ProcessorKind, kinds
from app.processors.outcomes import Fail, NeedsInput, Retry, Skip
from app.processors.records import DATASETS, Dimension, Measure, Money, Record, Text, Time

__all__ = [
    "DATASETS",
    "Address",
    "Attachment",
    "Context",
    "Dimension",
    "EmailDocument",
    "EmailLabel",
    "Fail",
    "Measure",
    "Money",
    "NeedsInput",
    "Notify",
    "ProcessorKind",
    "Record",
    "Retry",
    "Skip",
    "Text",
    "Time",
    "kinds",
]
