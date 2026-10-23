from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.schemas.inbox import InboxRead
from app.services.inboxes import list_inboxes

router = APIRouter(prefix="/email/inboxes", tags=["inboxes"])


@router.get("", response_model=list[InboxRead])
async def get_inboxes(session: Annotated[AsyncSession, Depends(get_session)]):
    return await list_inboxes(session)
