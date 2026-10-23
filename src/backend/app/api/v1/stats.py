import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.schemas.stats import Overview
from app.services import stats as stats_service
from app.services.stats import StatsQueryError

router = APIRouter(prefix="/stats", tags=["stats"])

SessionDep = Annotated[AsyncSession, Depends(get_session)]


@router.get("/overview", response_model=Overview)
async def overview(
    session: SessionDep,
    tz: Annotated[str, Query(description="IANA timezone for day/week/month buckets")] = "UTC",
    start: Annotated[datetime | None, Query(description="Inclusive lower bound on sent time")] = None,
    end: Annotated[datetime | None, Query(description="Exclusive upper bound on sent time")] = None,
    inbox_id: uuid.UUID | None = None,
    label_id: Annotated[
        list[uuid.UUID] | None, Query(description="Only emails with any of these labels")
    ] = None,
):
    """Totals, a timeline and breakdowns over stored emails, filtered by sent time, inbox and labels."""
    if start and end and end <= start:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "end must be after start")
    try:
        return await stats_service.overview(
            session, start=start, end=end, inbox_id=inbox_id, label_ids=label_id or [], tz_name=tz
        )
    except StatsQueryError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from None
