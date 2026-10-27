import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.schemas.dashboards import DashboardRead
from app.services import dashboards as dashboard_service

router = APIRouter(prefix="/dashboards", tags=["dashboards"])

SessionDep = Annotated[AsyncSession, Depends(get_session)]


@router.get("", response_model=list[DashboardRead])
async def list_dashboards(session: SessionDep):
    """One per processor whose kind ships a dashboard."""
    return await dashboard_service.list_dashboards(session)


@router.get("/{dashboard_id}", response_model=DashboardRead)
async def get_dashboard(dashboard_id: uuid.UUID, session: SessionDep):
    dashboard = await dashboard_service.get_dashboard(session, dashboard_id)
    if dashboard is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Dashboard not found")
    return dashboard
