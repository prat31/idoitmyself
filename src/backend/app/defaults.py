"""Built-in defaults: the labels, filters and processors a fresh install starts with.

Seeded on API startup, after the migrations (`python -m app.defaults`). Each default is seeded once,
recorded in `applied_defaults` by its key, so the user's edits are never overwritten and defaults added
in later releases still reach existing installs. Defaults start active, can be edited and deactivated,
but can't be deleted (their rows carry `default_key`). A default label whose name the user already
took is adopted: the user's label is used and stays theirs."""

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.filters.rule import Rule, check_mailbox_types
from app.models.default import AppliedDefault
from app.models.filter import Filter, FilterMailboxType, FilterStatus
from app.models.inbox import InboxProvider
from app.models.label import Label
from app.models.processor import Processor, ProcessorStatus
from app.processors import kinds
from app.schemas.label import normalize_label_name

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class DefaultLabel:
    key: str
    display_name: str
    color: str = "gray"


@dataclass(frozen=True)
class DefaultFilter:
    key: str
    name: str
    description: str | None
    label: str  # a DefaultLabel's key
    rule: dict[str, Any]
    mailbox_types: tuple[InboxProvider, ...] = (InboxProvider.GMAIL,)


@dataclass(frozen=True)
class DefaultProcessor:
    key: str
    name: str
    description: str | None
    labels: tuple[str, ...]  # DefaultLabel keys
    kind: str  # a processor kind's key (app.processors.kinds)
    config: dict[str, Any] = field(default_factory=dict)


def _condition(field_: str, op: str, value: str | None = None, join: str | None = None) -> dict[str, Any]:
    condition: dict[str, Any] = {"type": "condition", "field": field_, "op": op}
    if value is not None:
        condition["value"] = value
    if join is not None:
        condition["join"] = join
    return condition


LABELS: tuple[DefaultLabel, ...] = (
    DefaultLabel(key="label:credit_card_bill", display_name="Credit card bill"),
)

FILTERS: tuple[DefaultFilter, ...] = (
    DefaultFilter(
        key="filter:all_banks_credit_card_bills",
        name="All Banks Credit Card Bills",
        description="Credit card statements from Yes Bank and IDFC FIRST Bank.",
        label="label:credit_card_bill",
        # (sender is estatement@yes.bank.in OR statement@idfcfirst.bank.in) AND has attachments AND
        # sender address ends with bank.in
        rule={
            "type": "group",
            "items": [
                {
                    "type": "group",
                    "items": [
                        _condition("from_address", "equals", "estatement@yes.bank.in"),
                        _condition("from_address", "equals", "statement@idfcfirst.bank.in", join="or"),
                    ],
                },
                _condition("has_attachments", "is_true", join="and"),
                _condition("from_address", "ends_with", "bank.in", join="and"),
            ],
        },
    ),
)

PROCESSORS: tuple[DefaultProcessor, ...] = (
    DefaultProcessor(
        key="processor:credit_card_bills",
        name="Credit card bills",
        description="Reads the statement PDF of every credit card bill: dues, fees and transactions.",
        labels=("label:credit_card_bill",),
        kind="credit_card_statements",
    ),
)


@dataclass
class _Applied:
    keys: set[str]
    new: list[str] = field(default_factory=list)

    def record(self, session: AsyncSession, key: str) -> None:
        session.add(AppliedDefault(key=key))
        self.keys.add(key)
        self.new.append(key)


async def _label_id(session: AsyncSession, key: str) -> Any:
    """The label a default refers to: the seeded one, or the user's label it was adopted as."""
    default = next(label for label in LABELS if label.key == key)
    label_id = await session.scalar(
        select(Label.id).where(
            or_(Label.default_key == key, Label.name == normalize_label_name(default.display_name))
        )
    )
    if label_id is None:
        raise ValueError(f"Default {key} has no label")
    return label_id


async def apply_defaults(session: AsyncSession) -> list[str]:
    """Seed every default not seeded before. Returns the keys seeded now."""
    applied = _Applied(set(await session.scalars(select(AppliedDefault.key))))

    for default in LABELS:
        if default.key in applied.keys:
            continue
        name = normalize_label_name(default.display_name)
        if await session.scalar(select(Label.id).where(Label.name == name)) is None:
            session.add(
                Label(
                    name=name, display_name=default.display_name, color=default.color, default_key=default.key
                )
            )
        applied.record(session, default.key)
    await session.flush()

    for default in FILTERS:
        if default.key in applied.keys:
            continue
        rule = Rule.model_validate(default.rule)
        check_mailbox_types(rule, frozenset(default.mailbox_types))
        session.add(
            Filter(
                name=default.name,
                description=default.description,
                label_id=await _label_id(session, default.label),
                rule=rule.model_dump(mode="json", exclude_none=True),
                status=FilterStatus.ACTIVE,
                mailbox_types=[FilterMailboxType(mailbox_type=t) for t in default.mailbox_types],
                inboxes=[],
                default_key=default.key,
            )
        )
        applied.record(session, default.key)

    for default in PROCESSORS:
        if default.key in applied.keys:
            continue
        if default.kind not in kinds():
            raise ValueError(f"Default {default.key}: unknown processor kind {default.kind!r}")
        label_ids = [await _label_id(session, key) for key in default.labels]
        session.add(
            Processor(
                name=default.name,
                description=default.description,
                kind=default.kind,
                config=default.config,
                status=ProcessorStatus.ACTIVE,
                labels=list(await session.scalars(select(Label).where(Label.id.in_(label_ids)))),
                default_key=default.key,
            )
        )
        applied.record(session, default.key)

    await session.commit()
    return applied.new


async def _main() -> None:
    from app.db.session import SessionLocal, engine

    try:
        async with SessionLocal() as session:
            seeded = await apply_defaults(session)
    finally:
        await engine.dispose()
    logger.info("Built-in defaults seeded: %s", ", ".join(seeded) if seeded else "none new")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(_main())
