from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.schemas.dashboard import (
    DashboardAttention,
    DashboardCoverage,
    DashboardRecent,
    DashboardStatus,
    DashboardSummary,
)
from app.services import dashboard as dashboard_service
from app.services.stats import StatsQueryError

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

SessionDep = Annotated[AsyncSession, Depends(get_session)]


@router.get("/summary", response_model=DashboardSummary)
async def summary(
    session: SessionDep,
    tz: str = "UTC",
    start: Annotated[datetime | None, Query(description="Runs finished at or after")] = None,
    end: Annotated[datetime | None, Query(description="Runs finished before")] = None,
):
    """Runs, model spend (over time) and estimated savings in the range, plus labels this vs last month."""
    try:
        return await dashboard_service.summary(session, start=start, end=end, tz_name=tz)
    except StatsQueryError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from None


@router.get("/attention", response_model=DashboardAttention)
async def attention(session: SessionDep):
    """Things to act on: labels without/with stale conditions, tuning candidates, problem runs/inboxes."""
    return await dashboard_service.attention(session)


@router.get("/status", response_model=DashboardStatus)
async def live_status(session: SessionDep):
    """Per inbox: last scan, how far back it's scanned, and Gmail quota used in the current window."""
    return await dashboard_service.status(session)


@router.get("/coverage", response_model=DashboardCoverage)
async def coverage(session: SessionDep):
    """Date ranges already covered per label (current condition, every connected inbox)."""
    return await dashboard_service.coverage(session)


@router.get("/recent", response_model=DashboardRecent)
async def recent(session: SessionDep, limit: Annotated[int, Query(ge=1, le=50)] = 10):
    """Most recent labelled emails (by sent date)."""
    return await dashboard_service.recent(session, limit)
