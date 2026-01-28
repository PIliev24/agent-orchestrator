"""Workflow API routes."""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Query

from agent_orchestrator.api.dependencies import ApiKey, DbSession
from agent_orchestrator.core.schemas.workflow import (
    WorkflowCreate,
    WorkflowListResponse,
    WorkflowResponse,
    WorkflowUpdate,
)
from agent_orchestrator.services.workflow_service import WorkflowService

router = APIRouter()


@router.post("", response_model=WorkflowResponse, status_code=201)
async def create_workflow(
    data: WorkflowCreate,
    session: DbSession,
    _: ApiKey,
) -> WorkflowResponse:
    """Create a new workflow.

    Args:
        data: Workflow creation data.
        session: Database session.

    Returns:
        Created workflow.
    """
    service = WorkflowService(session)
    return await service.create(data)


@router.get("", response_model=WorkflowListResponse)
async def list_workflows(
    session: DbSession,
    _: ApiKey,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    search: Optional[str] = Query(default=None),
    templates_only: bool = Query(default=False),
) -> WorkflowListResponse:
    """List workflows with pagination.

    Args:
        session: Database session.
        page: Page number.
        page_size: Items per page.
        search: Optional search term.
        templates_only: If True, only return template workflows.

    Returns:
        Paginated list of workflows.
    """
    service = WorkflowService(session)
    workflows, total = await service.list(
        page=page,
        page_size=page_size,
        search=search,
        templates_only=templates_only,
    )
    return WorkflowListResponse(
        items=workflows,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/templates", response_model=WorkflowListResponse)
async def list_templates(
    session: DbSession,
    _: ApiKey,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> WorkflowListResponse:
    """List template workflows.

    Args:
        session: Database session.
        page: Page number.
        page_size: Items per page.

    Returns:
        Paginated list of template workflows.
    """
    service = WorkflowService(session)
    workflows, total = await service.list(
        page=page,
        page_size=page_size,
        templates_only=True,
    )
    return WorkflowListResponse(
        items=workflows,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{workflow_id}", response_model=WorkflowResponse)
async def get_workflow(
    workflow_id: UUID,
    session: DbSession,
    _: ApiKey,
) -> WorkflowResponse:
    """Get a workflow by ID.

    Args:
        workflow_id: Workflow ID.
        session: Database session.

    Returns:
        Workflow details with nodes and edges.
    """
    service = WorkflowService(session)
    return await service.get(workflow_id)


@router.put("/{workflow_id}", response_model=WorkflowResponse)
async def update_workflow(
    workflow_id: UUID,
    data: WorkflowUpdate,
    session: DbSession,
    _: ApiKey,
) -> WorkflowResponse:
    """Update a workflow.

    Args:
        workflow_id: Workflow ID.
        data: Update data.
        session: Database session.

    Returns:
        Updated workflow.
    """
    service = WorkflowService(session)
    return await service.update(workflow_id, data)


@router.delete("/{workflow_id}", status_code=204)
async def delete_workflow(
    workflow_id: UUID,
    session: DbSession,
    _: ApiKey,
) -> None:
    """Delete a workflow.

    Args:
        workflow_id: Workflow ID.
        session: Database session.
    """
    service = WorkflowService(session)
    await service.delete(workflow_id)


@router.post("/{workflow_id}/clone", response_model=WorkflowResponse, status_code=201)
async def clone_workflow(
    workflow_id: UUID,
    name: str = Query(..., min_length=1, max_length=128),
    session: DbSession = None,
    _: ApiKey = None,
) -> WorkflowResponse:
    """Clone a workflow.

    Args:
        workflow_id: Workflow ID to clone.
        name: Name for the cloned workflow.
        session: Database session.

    Returns:
        Cloned workflow.
    """
    service = WorkflowService(session)
    return await service.clone(workflow_id, name)
