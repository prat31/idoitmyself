"""Browsing stored emails (metadata only) with filters, search and sorting."""

import uuid
from datetime import datetime

from sqlalchemy import exists, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.mail.sources import message_url
from app.models.email import Email, EmailLabel
from app.models.filter import Filter
from app.models.inbox import Inbox
from app.models.label import Label
from app.schemas.email import EmailLabelTag, EmailList, EmailListStats, EmailRow, EmailSort
from app.services.stats import _email_filters

_ORDER = {
    "sent_desc": (Email.sent_at.desc(),),
    "sent_asc": (Email.sent_at.asc(),),
    "sender_asc": (func.lower(Email.from_address).asc().nulls_last(), Email.sent_at.desc()),
    "sender_desc": (func.lower(Email.from_address).desc().nulls_last(), Email.sent_at.desc()),
    "subject_asc": (func.lower(Email.subject).asc().nulls_last(), Email.sent_at.desc()),
    "subject_desc": (func.lower(Email.subject).desc().nulls_last(), Email.sent_at.desc()),
}


def _escape_like(text: str) -> str:
    """Match the search text literally: its %, _ and \\ aren't LIKE wildcards."""
    return text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


async def list_emails(
    session: AsyncSession,
    *,
    start: datetime | None,
    end: datetime | None,
    inbox_id: uuid.UUID | None,
    label_ids: list[uuid.UUID],
    labelled: bool | None,
    q: str | None,
    sort: EmailSort,
    page: int,
    page_size: int,
) -> EmailList:
    """Stored emails matching the filters (sent time, inbox, any of the labels, labelled or not, a
    sender/subject search), sorted and paged, plus stats over all of them."""
    conditions = _email_filters(start, end, inbox_id, label_ids)
    has_label = exists().where(EmailLabel.email_id == Email.id)
    if labelled is not None:
        conditions.append(has_label if labelled else ~has_label)
    if q and q.strip():
        pattern = f"%{_escape_like(q.strip())}%"
        conditions.append(
            or_(Email.from_address.ilike(pattern, escape="\\"), Email.subject.ilike(pattern, escape="\\"))
        )

    emails, labelled_count, senders, inboxes, first, last = (
        await session.execute(
            select(
                func.count(),
                func.count().filter(has_label),
                func.count(func.distinct(func.lower(Email.from_address))),
                func.count(func.distinct(Email.inbox_id)),
                func.min(Email.sent_at),
                func.max(Email.sent_at),
            ).where(*conditions)
        )
    ).one()

    rows = (
        await session.execute(
            select(Email, Inbox.name, Inbox.provider, Inbox.email_address)
            .join(Inbox, Inbox.id == Email.inbox_id)
            .where(*conditions)
            .order_by(*_ORDER[sort], Email.id)
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    ).all()

    tags: dict[uuid.UUID, list[EmailLabelTag]] = {row[0].id: [] for row in rows}
    if tags:
        for email_id, label_id, display_name, color, filter_name in await session.execute(
            select(EmailLabel.email_id, Label.id, Label.display_name, Label.color, Filter.name)
            .join(Label, Label.id == EmailLabel.label_id)
            .outerjoin(Filter, Filter.id == EmailLabel.filter_id)
            .where(EmailLabel.email_id.in_(tags))
            .order_by(Label.display_name)
        ):
            tags[email_id].append(
                EmailLabelTag(
                    label_id=label_id, display_name=display_name, color=color, filter_name=filter_name
                )
            )

    return EmailList(
        items=[
            EmailRow(
                id=email.id,
                inbox_id=email.inbox_id,
                inbox_name=inbox_name,
                sent_at=email.sent_at,
                from_address=email.from_address,
                to_addresses=email.to_addresses,
                subject=email.subject,
                snippet=email.snippet,
                labels=tags[email.id],
                scanned_at=email.created_at,
                open_url=message_url(provider, address, email.provider_message_id),
            )
            for email, inbox_name, provider, address in rows
        ],
        total=emails,
        page=page,
        page_size=page_size,
        stats=EmailListStats(
            emails=emails,
            labelled=labelled_count,
            unlabelled=emails - labelled_count,
            senders=senders,
            inboxes=inboxes,
            first_sent_at=first,
            last_sent_at=last,
        ),
    )
