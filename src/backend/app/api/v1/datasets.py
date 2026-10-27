from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.schemas.dataset import DatasetRead, RowsQuery, RowsResult, SeriesQuery, SeriesResult
from app.services import datasets as dataset_service
from app.services.datasets import DatasetQueryError

router = APIRouter(prefix="/datasets", tags=["datasets"])

SessionDep = Annotated[AsyncSession, Depends(get_session)]


@router.get("", response_model=list[DatasetRead])
async def list_datasets():
    """Every dataset processors write, with its fields."""
    return dataset_service.datasets()


@router.post("/query", response_model=SeriesResult)
async def query(data: SeriesQuery, session: SessionDep):
    """An aggregate over a dataset: one value, or one per group and/or time bucket."""
    try:
        return await dataset_service.series(session, data)
    except DatasetQueryError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from None


@router.post("/rows", response_model=RowsResult)
async def rows(data: RowsQuery, session: SessionDep):
    """A dataset's records, newest first, with the email each came from."""
    try:
        return await dataset_service.rows(session, data)
    except DatasetQueryError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from None
