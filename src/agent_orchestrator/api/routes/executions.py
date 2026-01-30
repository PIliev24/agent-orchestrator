"""Execution API routes."""

from uuid import UUID

from fastapi import APIRouter, Query
from sse_starlette.sse import EventSourceResponse

from agent_orchestrator.api.dependencies import ApiKey, DbSession
from agent_orchestrator.core.schemas.execution import (
    ExecutionCreate,
    ExecutionListResponse,
    ExecutionResponse,
    ExecutionStatusResponse,
)
from agent_orchestrator.database.models.execution import ExecutionStatus
from agent_orchestrator.services.execution_service import ExecutionService

router = APIRouter()


@router.post("", response_model=ExecutionResponse, status_code=201)
async def create_execution(
    data: ExecutionCreate,
    session: DbSession,
    _: ApiKey,
) -> ExecutionResponse:
    """Execute a workflow.

    This starts a workflow execution and waits for it to complete.
    For long-running workflows, consider using the streaming endpoint.

    Args:
        data: Execution parameters.
        session: Database session.

    Returns:
        Execution results.
    """
    service = ExecutionService(session)
    return await service.execute(data)


@router.post("/stream", status_code=200)
async def create_execution_stream(
    data: ExecutionCreate,
    session: DbSession,
    _: ApiKey,
):
    """Execute a workflow with streaming events.

    Returns Server-Sent Events (SSE) for real-time execution progress.

    Args:
        data: Execution parameters.
        session: Database session.

    Returns:
        SSE stream of execution events.
    """
    service = ExecutionService(session)

    async def event_generator():
        async for event in service.execute_stream(data):
            yield {
                "event": event.event_type,
                "data": event.model_dump_json(),
            }

    return EventSourceResponse(event_generator())


@router.get("", response_model=ExecutionListResponse)
async def list_executions(
    session: DbSession,
    _: ApiKey,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    workflow_id: UUID | None = Query(default=None),
    status: ExecutionStatus | None = Query(default=None),
) -> ExecutionListResponse:
    """List executions with pagination.

    Args:
        session: Database session.
        page: Page number.
        page_size: Items per page.
        workflow_id: Optional filter by workflow.
        status: Optional filter by status.

    Returns:
        Paginated list of executions.
    """
    service = ExecutionService(session)
    executions, total = await service.list(
        page=page,
        page_size=page_size,
        workflow_id=workflow_id,
        status=status,
    )
    return ExecutionListResponse(
        items=executions,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{execution_id}", response_model=ExecutionResponse)
async def get_execution(
    execution_id: UUID,
    session: DbSession,
    _: ApiKey,
) -> ExecutionResponse:
    """Get an execution by ID.

    Args:
        execution_id: Execution ID.
        session: Database session.

    Returns:
        Execution details.
    """
    service = ExecutionService(session)
    return await service.get(execution_id)


@router.get("/{execution_id}/status", response_model=ExecutionStatusResponse)
async def get_execution_status(
    execution_id: UUID,
    session: DbSession,
    _: ApiKey,
) -> ExecutionStatusResponse:
    """Get lightweight status for an execution.

    Use this endpoint for polling execution progress.

    Args:
        execution_id: Execution ID.
        session: Database session.

    Returns:
        Execution status and progress.
    """
    service = ExecutionService(session)
    return await service.get_status(execution_id)


@router.post("/{execution_id}/cancel", response_model=ExecutionResponse)
async def cancel_execution(
    execution_id: UUID,
    session: DbSession,
    _: ApiKey,
) -> ExecutionResponse:
    """Cancel a running execution.

    Args:
        execution_id: Execution ID.
        session: Database session.

    Returns:
        Updated execution with cancelled status.
    """
    service = ExecutionService(session)
    return await service.cancel(execution_id)


@router.delete("/{execution_id}", status_code=204)
async def delete_execution(
    execution_id: UUID,
    session: DbSession,
    _: ApiKey,
) -> None:
    """Delete an execution."""
    service = ExecutionService(session)
    await service.delete(execution_id)


@router.post("/{execution_id}/resume", response_model=ExecutionResponse, status_code=201)
async def resume_execution(
    execution_id: UUID,
    session: DbSession,
    _: ApiKey,
) -> ExecutionResponse:
    """Resume a cancelled or failed execution."""
    service = ExecutionService(session)
    return await service.resume(execution_id)


@router.post("/{execution_id}/restart", response_model=ExecutionResponse, status_code=201)
async def restart_execution(
    execution_id: UUID,
    session: DbSession,
    _: ApiKey,
) -> ExecutionResponse:
    """Restart an execution from scratch."""
    service = ExecutionService(session)
    return await service.restart(execution_id)
