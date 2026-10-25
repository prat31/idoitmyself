import uuid
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.filters.fields import FIELDS, OPERATORS
from app.filters.rule import Rule, check_mailbox_types
from app.models.email import EmailLabel
from app.models.filter import Filter, FilterMailboxType, FilterStatus
from app.models.inbox import Inbox, InboxProvider
from app.models.label import Label
from app.schemas.filter import (
    FieldCatalogue,
    FieldOption,
    FieldRead,
    FilterCreate,
    FilterLabelRef,
    FilterRead,
    FilterScope,
    FilterScopeRead,
    FilterUpdate,
    OperatorRead,
    ScopeInbox,
)


class FilterInputError(ValueError):
    """Invalid filter input that only the database can tell (unknown label or inbox, a field not
    available for every inbox in scope)."""


def field_catalogue() -> FieldCatalogue:
    return FieldCatalogue(
        mailbox_types=list(InboxProvider),
        fields=[
            FieldRead(
                key=spec.key,
                label=spec.label,
                type=spec.type.value,
                description=spec.description,
                mailbox_types=sorted(spec.mailbox_types) if spec.mailbox_types is not None else None,
                options=[FieldOption(value=v, label=label) for v, label in spec.options],
                argument_label=spec.argument_label,
            )
            for spec in FIELDS.values()
        ],
        operators={
            field_type.value: [
                OperatorRead(key=op.key, label=op.label, takes_value=op.takes_value) for op in operators
            ]
            for field_type, operators in OPERATORS.items()
        },
    )


def _stats():
    """Per filter: emails it labelled, and when it last did."""
    return (
        select(
            EmailLabel.filter_id, func.count().label("emails"), func.max(EmailLabel.applied_at).label("last")
        )
        .group_by(EmailLabel.filter_id)
        .subquery()
    )


def _to_read(f: Filter, emails: int | None, last: datetime | None) -> FilterRead:
    return FilterRead(
        id=f.id,
        name=f.name,
        description=f.description,
        scope=FilterScopeRead(
            mailbox_types=[t.mailbox_type for t in f.mailbox_types],
            inboxes=[
                ScopeInbox(id=i.id, name=i.name, email_address=i.email_address, provider=i.provider)
                for i in f.inboxes
            ],
        ),
        label=FilterLabelRef(
            id=f.label.id, name=f.label.name, display_name=f.label.display_name, color=f.label.color
        ),
        rule=Rule.model_validate(f.rule),
        status=f.status,
        status_changed_at=f.status_changed_at,
        emails_labelled=emails or 0,
        last_matched_at=last,
        created_at=f.created_at,
        updated_at=f.updated_at,
    )


async def list_filters(session: AsyncSession) -> list[FilterRead]:
    stats = _stats()
    rows = await session.execute(
        select(Filter, stats.c.emails, stats.c.last)
        .outerjoin(stats, stats.c.filter_id == Filter.id)
        .order_by(Filter.name, Filter.created_at)
    )
    return [_to_read(f, emails, last) for f, emails, last in rows]


async def get_filter(session: AsyncSession, filter_id: uuid.UUID) -> FilterRead | None:
    stats = _stats()
    row = (
        await session.execute(
            select(Filter, stats.c.emails, stats.c.last)
            .outerjoin(stats, stats.c.filter_id == Filter.id)
            .where(Filter.id == filter_id)
        )
    ).first()
    return _to_read(*row) if row else None


async def _require_label(session: AsyncSession, label_id: uuid.UUID) -> None:
    if await session.get(Label, label_id) is None:
        raise FilterInputError("Label not found")


async def _resolve_scope(
    session: AsyncSession, scope: FilterScope
) -> tuple[list[InboxProvider], list[Inbox]]:
    """The scope's mailbox types and inboxes. Inboxes already covered by a selected type are dropped
    (the type covers them, and future ones too)."""
    inboxes = list(await session.scalars(select(Inbox).where(Inbox.id.in_(scope.inbox_ids))))
    if len(inboxes) != len(scope.inbox_ids):
        raise FilterInputError("Inbox not found")
    types = set(scope.mailbox_types)
    return scope.mailbox_types, [i for i in inboxes if i.provider not in types]


def _check_rule(rule: Rule, types: list[InboxProvider], inboxes: list[Inbox]) -> None:
    try:
        check_mailbox_types(rule, frozenset(types) | {i.provider for i in inboxes})
    except ValueError as exc:
        raise FilterInputError(str(exc)) from None


async def create_filter(session: AsyncSession, data: FilterCreate) -> FilterRead:
    await _require_label(session, data.label_id)
    types, inboxes = await _resolve_scope(session, data.scope)
    _check_rule(data.rule, types, inboxes)
    f = Filter(
        name=data.name,
        description=data.description,
        label_id=data.label_id,
        rule=data.rule.model_dump(mode="json", exclude_none=True),
        status=data.status,
        mailbox_types=[FilterMailboxType(mailbox_type=t) for t in types],
        inboxes=inboxes,
    )
    session.add(f)
    await session.commit()
    session.expunge(f)
    return await get_filter(session, f.id)  # type: ignore[return-value]


async def update_filter(session: AsyncSession, filter_id: uuid.UUID, data: FilterUpdate) -> FilterRead | None:
    f = await session.get(Filter, filter_id)
    if f is None:
        return None
    fields = data.model_fields_set  # only the fields the client sent
    if "label_id" in fields:
        await _require_label(session, data.label_id)  # type: ignore[arg-type]
        f.label_id = data.label_id  # type: ignore[assignment]
    if "scope" in fields:
        types, inboxes = await _resolve_scope(session, data.scope)  # type: ignore[arg-type]
    else:
        types, inboxes = [t.mailbox_type for t in f.mailbox_types], list(f.inboxes)
    rule = data.rule if "rule" in fields else Rule.model_validate(f.rule)
    if "scope" in fields or "rule" in fields:
        _check_rule(rule, types, inboxes)  # type: ignore[arg-type]
    if "scope" in fields:
        # Reuse rows for types kept, so the flush never inserts a duplicate key before deleting the old.
        kept = {t.mailbox_type: t for t in f.mailbox_types}
        f.mailbox_types = [kept.get(t) or FilterMailboxType(mailbox_type=t) for t in types]
        f.inboxes = inboxes
    if "rule" in fields:
        f.rule = data.rule.model_dump(mode="json", exclude_none=True)  # type: ignore[union-attr]
    if "name" in fields:
        f.name = data.name  # type: ignore[assignment]
    if "description" in fields:
        f.description = data.description
    if "status" in fields and data.status != f.status:
        f.status = data.status  # type: ignore[assignment]
        f.status_changed_at = datetime.now(UTC)
    await session.commit()
    session.expunge(f)  # reload with the (possibly new) label and scope
    return await get_filter(session, filter_id)


async def delete_filter(session: AsyncSession, filter_id: uuid.UUID) -> bool:
    """Delete a filter. Labels it applied stay on their emails."""
    f = await session.get(Filter, filter_id)
    if f is None:
        return False
    await session.delete(f)
    await session.commit()
    return True


async def active_filters(session: AsyncSession) -> list[Filter]:
    """Active filters with their scope loaded, oldest first (the order labels are attributed in)."""
    return list(
        await session.scalars(
            select(Filter).where(Filter.status == FilterStatus.ACTIVE).order_by(Filter.created_at)
        )
    )


async def active_filters_for(session: AsyncSession, inbox: Inbox) -> list[Filter]:
    """Active filters whose scope covers this inbox."""
    return [f for f in await active_filters(session) if f.covers(inbox)]
