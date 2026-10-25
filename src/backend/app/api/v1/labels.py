import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.models.label import Label
from app.schemas.label import LabelCreate, LabelRead, LabelUpdate
from app.schemas.stats import EmailPage, LabelStats
from app.services import labels as label_service
from app.services import stats as stats_service
from app.services.labels import LabelInUseError, LabelNameTakenError
from app.services.stats import StatsQueryError

router = APIRouter(prefix="/labels", tags=["labels"])

SessionDep = Annotated[AsyncSession, Depends(get_session)]


@router.get("", response_model=list[LabelRead])
async def list_labels(session: SessionDep):
    return await label_service.list_labels(session)


async def _get_label_or_404(session: AsyncSession, label_id: uuid.UUID) -> Label:
    label = await session.get(Label, label_id)
    if label is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Label not found")
    return label


@router.get("/{label_id}", response_model=LabelRead)
async def get_label(label_id: uuid.UUID, session: SessionDep):
    label = await label_service.get_label(session, label_id)
    if label is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Label not found")
    return label


@router.get("/{label_id}/stats", response_model=LabelStats)
async def get_label_stats(label_id: uuid.UUID, session: SessionDep, tz: str = "UTC"):
    label = await _get_label_or_404(session, label_id)
    try:
        return await stats_service.label_stats(session, label, tz)
    except StatsQueryError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from None


@router.get("/{label_id}/emails", response_model=EmailPage)
async def get_label_emails(
    label_id: uuid.UUID,
    session: SessionDep,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 25,
):
    """Emails carrying this label, newest first, with the filter that added it."""
    label = await _get_label_or_404(session, label_id)
    return await stats_service.label_emails(session, label, page, page_size)


@router.post("", response_model=LabelRead, status_code=status.HTTP_201_CREATED)
async def create_label(data: LabelCreate, session: SessionDep):
    try:
        return await label_service.create_label(session, data)
    except LabelNameTakenError:
        raise HTTPException(status.HTTP_409_CONFLICT, f'A label named "{data.name}" already exists') from None


@router.patch("/{label_id}", response_model=LabelRead)
async def update_label(label_id: uuid.UUID, data: LabelUpdate, session: SessionDep):
    """Change a label's display name and/or colour. Its normalised name never changes."""
    label = await label_service.update_label(session, label_id, data)
    if label is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Label not found")
    return label


@router.delete("/{label_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_label(label_id: uuid.UUID, session: SessionDep):
    try:
        deleted = await label_service.delete_label(session, label_id)
    except LabelInUseError:
        raise HTTPException(
            status.HTTP_409_CONFLICT, "Filters still add this label; change or delete them first"
        ) from None
    if not deleted:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Label not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
