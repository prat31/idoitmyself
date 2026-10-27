import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.schemas.notification import NotificationPage
from app.services import notifications as notification_service

router = APIRouter(prefix="/notifications", tags=["notifications"])

SessionDep = Annotated[AsyncSession, Depends(get_session)]


@router.get("", response_model=NotificationPage)
async def list_notifications(
    session: SessionDep,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    unread_only: bool = False,
):
    """Newest first, with the unread count."""
    return await notification_service.list_notifications(
        session, page=page, page_size=page_size, unread_only=unread_only
    )


@router.post("/read-all", status_code=status.HTTP_204_NO_CONTENT)
async def mark_all_read(session: SessionDep):
    await notification_service.mark_all_read(session)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{notification_id}/read", status_code=status.HTTP_204_NO_CONTENT)
async def mark_read(notification_id: uuid.UUID, session: SessionDep):
    if not await notification_service.mark_read(session, notification_id, True):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Notification not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{notification_id}/unread", status_code=status.HTTP_204_NO_CONTENT)
async def mark_unread(notification_id: uuid.UUID, session: SessionDep):
    if not await notification_service.mark_read(session, notification_id, False):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Notification not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{notification_id}/dismiss", status_code=status.HTTP_204_NO_CONTENT)
async def dismiss(notification_id: uuid.UUID, session: SessionDep):
    """Remove it from the list."""
    if not await notification_service.dismiss(session, notification_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Notification not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
