import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.schemas.email import EmailList, EmailSort
from app.services import emails as email_service

router = APIRouter(prefix="/emails", tags=["emails"])

SessionDep = Annotated[AsyncSession, Depends(get_session)]


@router.get("", response_model=EmailList)
async def list_emails(
    session: SessionDep,
    start: Annotated[datetime | None, Query(description="Inclusive lower bound on sent time")] = None,
    end: Annotated[datetime | None, Query(description="Exclusive upper bound on sent time")] = None,
    inbox_id: uuid.UUID | None = None,
    label_id: Annotated[list[uuid.UUID] | None, Query(description="Emails with any of these labels")] = None,
    labelled: Annotated[bool | None, Query(description="Only labelled (true) or unlabelled (false)")] = None,
    q: Annotated[str | None, Query(max_length=200, description="Search in sender and subject")] = None,
    sort: EmailSort = "sent_desc",
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 25,
):
    """Stored emails (metadata only), filtered, searched, sorted and paged, with stats over all matches."""
    if start and end and end <= start:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "end must be after start")
    return await email_service.list_emails(
        session,
        start=start,
        end=end,
        inbox_id=inbox_id,
        label_ids=label_id or [],
        labelled=labelled,
        q=q,
        sort=sort,
        page=page,
        page_size=page_size,
    )
