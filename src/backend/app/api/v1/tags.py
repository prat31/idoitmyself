from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.schemas.inbox import TagRead
from app.services.tags import list_tags

router = APIRouter(prefix="/tags", tags=["tags"])


@router.get("", response_model=list[TagRead])
async def get_tags(session: Annotated[AsyncSession, Depends(get_session)]):
    return await list_tags(session)
