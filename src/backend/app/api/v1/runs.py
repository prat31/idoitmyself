import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.schemas.run import (
    AdhocRunCreate,
    RunCoverage,
    RunCoverageRequest,
    RunEmailPage,
    RunInsights,
    RunRead,
)
from app.services import run_insights as insights_service
from app.services import runs as run_service
from app.services.run_insights import Sort, Tab
from app.services.runs import RunRequestError
from app.services.stats import StatsQueryError

router = APIRouter(prefix="/runs", tags=["runs"])

SessionDep = Annotated[AsyncSession, Depends(get_session)]


@router.get("", response_model=list[RunRead])
async def list_runs(session: SessionDep):
    """All runs, any status, newest first."""
    return await run_service.list_runs(session)


@router.post("/coverage", response_model=RunCoverage)
async def run_coverage(data: RunCoverageRequest, session: SessionDep):
    """Which parts of a prospective run's window are already scanned for each label (read-only)."""
    return await run_service.coverage(session, data)


@router.get("/{run_id}", response_model=RunRead)
async def get_run(run_id: uuid.UUID, session: SessionDep):
    run = await run_service.get_run(session, run_id)
    if run is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Run not found")
    return run


@router.post("/adhoc", response_model=RunRead, status_code=status.HTTP_201_CREATED)
async def create_adhoc_run(data: AdhocRunCreate, session: SessionDep):
    """Queue an ad hoc run; a Celery worker picks it up from RabbitMQ."""
    try:
        return await run_service.create_adhoc_run(session, data)
    except RunRequestError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from None


async def _get_run_or_404(session: AsyncSession, run_id: uuid.UUID):
    run = await run_service.get_run(session, run_id)
    if run is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Run not found")
    return run


@router.get("/{run_id}/insights", response_model=RunInsights)
async def get_run_insights(run_id: uuid.UUID, session: SessionDep, tz: str = "UTC"):
    """Per-label answer counts and probability histograms, and when the matched emails were sent."""
    run = await _get_run_or_404(session, run_id)
    try:
        return await insights_service.run_insights(session, run, tz)
    except StatsQueryError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from None


@router.get("/{run_id}/emails", response_model=RunEmailPage)
async def get_run_emails(
    run_id: uuid.UUID,
    session: SessionDep,
    tab: Tab = "matched",
    label_id: uuid.UUID | None = None,
    sort: Sort = "probability_desc",
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 25,
):
    """The run's (email, label) results: matched, near the threshold, not matched, or skipped (reused)."""
    run = await _get_run_or_404(session, run_id)
    return await insights_service.run_emails(
        session, run, tab=tab, label_id=label_id, sort=sort, page=page, page_size=page_size
    )
