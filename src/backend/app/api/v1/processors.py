import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.models.processor import Processor, ProcessorRunStatus
from app.schemas.processor import (
    InputSave,
    ProcessorCreate,
    ProcessorKindRead,
    ProcessorRead,
    ProcessorRunPage,
    ProcessorUpdate,
    QueuedRuns,
)
from app.services import processors as processor_service
from app.services.processors import DefaultProcessorError, ProcessorInputError

router = APIRouter(prefix="/processors", tags=["processors"])

SessionDep = Annotated[AsyncSession, Depends(get_session)]


def _publish(run_ids: list[uuid.UUID]) -> QueuedRuns:
    from app.worker import publish_processor_runs

    publish_processor_runs(run_ids)
    return QueuedRuns(queued=len(run_ids))


async def _exists_or_404(session: AsyncSession, processor_id: uuid.UUID) -> None:
    if await session.get(Processor, processor_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Processor not found")


@router.get("/kinds", response_model=list[ProcessorKindRead])
async def list_kinds():
    """The processor kinds in the code: what each writes, and its settings."""
    return processor_service.kind_list()


@router.put("/inputs", response_model=QueuedRuns)
async def save_input(data: InputSave, session: SessionDep):
    """Save something a processor asked for (e.g. a PDF password), and run again what waited for it."""
    return _publish(await processor_service.save_input(session, data))


@router.get("", response_model=list[ProcessorRead])
async def list_processors(session: SessionDep):
    return await processor_service.list_processors(session)


@router.post("", response_model=ProcessorRead, status_code=status.HTTP_201_CREATED)
async def create_processor(data: ProcessorCreate, session: SessionDep):
    """A new processor starts active: it runs on emails that get any of its labels from now on."""
    try:
        return await processor_service.create_processor(session, data)
    except ProcessorInputError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from None


@router.get("/{processor_id}", response_model=ProcessorRead)
async def get_processor(processor_id: uuid.UUID, session: SessionDep):
    processor = await processor_service.get_processor(session, processor_id)
    if processor is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Processor not found")
    return processor


@router.patch("/{processor_id}", response_model=ProcessorRead)
async def update_processor(processor_id: uuid.UUID, data: ProcessorUpdate, session: SessionDep):
    """Change the name, description, labels, settings or status. The kind is fixed."""
    try:
        processor = await processor_service.update_processor(session, processor_id, data)
    except ProcessorInputError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from None
    if processor is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Processor not found")
    return processor


@router.delete("/{processor_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_processor(processor_id: uuid.UUID, session: SessionDep):
    """Its records stay. Built-in defaults can't be deleted."""
    try:
        deleted = await processor_service.delete_processor(session, processor_id)
    except DefaultProcessorError:
        raise HTTPException(
            status.HTTP_409_CONFLICT, "Built-in processors can't be deleted; deactivate it instead"
        ) from None
    if not deleted:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Processor not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{processor_id}/runs", response_model=ProcessorRunPage)
async def list_runs(
    processor_id: uuid.UUID,
    session: SessionDep,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 25,
    status_: Annotated[list[ProcessorRunStatus] | None, Query(alias="status")] = None,
):
    await _exists_or_404(session, processor_id)
    return await processor_service.list_runs(session, processor_id, page, page_size, status_)


@router.post("/{processor_id}/run-existing", response_model=QueuedRuns)
async def run_on_existing(processor_id: uuid.UUID, session: SessionDep):
    """Run on emails that already carry any of its labels and were never run through it."""
    run_ids = await processor_service.queue_existing(session, processor_id)
    if run_ids is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Processor not found")
    return _publish(run_ids)


@router.post("/{processor_id}/rerun", response_model=QueuedRuns)
async def rerun(
    processor_id: uuid.UUID,
    session: SessionDep,
    status_: Annotated[list[ProcessorRunStatus], Query(alias="status")],
):
    """Run again the runs in these statuses (e.g. failed); each replaces what it wrote before."""
    await _exists_or_404(session, processor_id)
    allowed = {ProcessorRunStatus.FAILED, ProcessorRunStatus.SKIPPED, ProcessorRunStatus.SUCCEEDED}
    if not set(status_) <= allowed:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Only finished runs can run again")
    return _publish(await processor_service.requeue(session, processor_id, status_))
