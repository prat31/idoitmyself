import uuid
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.session import get_session
from app.schemas.scan import AdhocScanCreate, ScanPage, ScanRead, ScanSchedule
from app.services import scans as scan_service
from app.services.scans import AdhocScanError, ScanNotActiveError

router = APIRouter(prefix="/scans", tags=["scans"])

SessionDep = Annotated[AsyncSession, Depends(get_session)]


@router.get("", response_model=ScanPage)
async def list_scans(
    session: SessionDep,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 25,
    active: Annotated[bool, Query(description="Only queued or running scans")] = False,
    inbox_id: uuid.UUID | None = None,
):
    """Scans of every inbox, newest first. Periodic scans are started by the tick; ad hoc ones below."""
    return await scan_service.list_scans(
        session, page=page, page_size=page_size, active=active, inbox_id=inbox_id
    )


@router.get("/schedule", response_model=ScanSchedule)
async def schedule():
    """The scheduled-scan interval and when the next tick fires."""
    return ScanSchedule(
        interval_minutes=get_settings().scan_interval_minutes,
        next_run_at=scan_service.next_run_at(datetime.now(UTC)),
    )


@router.post("/adhoc", response_model=list[ScanRead], status_code=status.HTTP_201_CREATED)
async def create_adhoc_scans(data: AdhocScanCreate, session: SessionDep):
    """Queue an ad hoc scan per inbox the chosen (active) filters cover, over a past date range."""
    from app.worker import DISCOVER_TASK, celery_app

    try:
        scans = await scan_service.create_adhoc_scans(session, data)
    except AdhocScanError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from None
    for scan in scans:
        celery_app.send_task(DISCOVER_TASK, args=[str(scan.id)])
    return scans


@router.post("/{scan_id}/cancel", response_model=ScanRead)
async def cancel_scan(scan_id: uuid.UUID, session: SessionDep):
    """Stop a queued or running scan. Emails already stored and labels already added stay."""
    try:
        scan = await scan_service.cancel_scan(session, scan_id)
    except ScanNotActiveError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, f"The scan has already finished ({exc})") from None
    if scan is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Scan not found")
    return scan
