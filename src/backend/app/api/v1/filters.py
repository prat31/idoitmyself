import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.schemas.filter import FieldCatalogue, FilterCreate, FilterRead, FilterUpdate
from app.services import filters as filter_service
from app.services.filters import FilterInputError

router = APIRouter(prefix="/filters", tags=["filters"])

SessionDep = Annotated[AsyncSession, Depends(get_session)]


@router.get("/fields", response_model=FieldCatalogue)
async def field_catalogue():
    """Fields a condition can test (with the mailbox types they apply to) and operators per field type."""
    return filter_service.field_catalogue()


@router.get("", response_model=list[FilterRead])
async def list_filters(session: SessionDep):
    return await filter_service.list_filters(session)


@router.get("/{filter_id}", response_model=FilterRead)
async def get_filter(filter_id: uuid.UUID, session: SessionDep):
    found = await filter_service.get_filter(session, filter_id)
    if found is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Filter not found")
    return found


@router.post("", response_model=FilterRead, status_code=status.HTTP_201_CREATED)
async def create_filter(data: FilterCreate, session: SessionDep):
    """Create a filter. It's active unless `status` says otherwise, and applies to emails scanned from
    now on."""
    try:
        return await filter_service.create_filter(session, data)
    except FilterInputError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from None


@router.patch("/{filter_id}", response_model=FilterRead)
async def update_filter(filter_id: uuid.UUID, data: FilterUpdate, session: SessionDep):
    """Edit a filter or (de)activate it with `status`. Labels it already applied stay."""
    try:
        updated = await filter_service.update_filter(session, filter_id, data)
    except FilterInputError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from None
    if updated is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Filter not found")
    return updated


@router.delete("/{filter_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_filter(filter_id: uuid.UUID, session: SessionDep):
    if not await filter_service.delete_filter(session, filter_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Filter not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
