from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.schemas.home import (
    HomeAttention,
    HomeRecent,
    HomeStatus,
    HomeSummary,
)
from app.services import home as home_service
from app.services.stats import StatsQueryError

router = APIRouter(prefix="/home", tags=["home"])

SessionDep = Annotated[AsyncSession, Depends(get_session)]


@router.get("/summary", response_model=HomeSummary)
async def summary(
    session: SessionDep,
    tz: str = "UTC",
    start: Annotated[datetime | None, Query(description="Scans finished at or after")] = None,
    end: Annotated[datetime | None, Query(description="Scans finished before")] = None,
):
    """Scans and labels applied in the range, filter counts, plus labels this vs last month."""
    try:
        return await home_service.summary(session, start=start, end=end, tz_name=tz)
    except StatsQueryError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from None


@router.get("/attention", response_model=HomeAttention)
async def attention(session: SessionDep):
    """Things to act on: failing inboxes/scans, filters that never matched, labels nothing adds."""
    return await home_service.attention(session)


@router.get("/status", response_model=HomeStatus)
async def live_status(session: SessionDep):
    """Per inbox: initial scan state, last scan, scan in progress, and quota used in the current window."""
    return await home_service.status(session)


@router.get("/recent", response_model=HomeRecent)
async def recent(session: SessionDep, limit: Annotated[int, Query(ge=1, le=50)] = 10):
    """Most recent labelled emails (by sent date)."""
    return await home_service.recent(session, limit)
