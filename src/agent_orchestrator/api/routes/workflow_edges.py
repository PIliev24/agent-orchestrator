"""Workflow edge sub-resource routes."""

from uuid import UUID

from fastapi import APIRouter, Query

from agent_orchestrator.api.dependencies import ApiKey, DbSession
from agent_orchestrator.core.schemas.workflow import (
    WorkflowEdgeCreate,
    WorkflowEdgeListResponse,
    WorkflowEdgeResponse,
    WorkflowEdgeUpdate,
)
from agent_orchestrator.services.workflow_service import WorkflowService

router = APIRouter()


@router.post("", response_model=WorkflowEdgeResponse, status_code=201)
async def create_edge(
    workflow_id: UUID,
    data: WorkflowEdgeCreate,
    session: DbSession,
    _: ApiKey,
) -> WorkflowEdgeResponse:
    """Add an edge to a workflow."""
    service = WorkflowService(session)
    return await service.create_edge(workflow_id, data)


@router.get("", response_model=WorkflowEdgeListResponse)
async def list_edges(
    workflow_id: UUID,
    session: DbSession,
    _: ApiKey,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> WorkflowEdgeListResponse:
    """List edges for a workflow."""
    service = WorkflowService(session)
    edges, total = await service.list_edges(workflow_id, page=page, page_size=page_size)
    return WorkflowEdgeListResponse(
        items=edges,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{edge_id}", response_model=WorkflowEdgeResponse)
async def get_edge(
    workflow_id: UUID,
    edge_id: UUID,
    session: DbSession,
    _: ApiKey,
) -> WorkflowEdgeResponse:
    """Get a single edge."""
    service = WorkflowService(session)
    return await service.get_edge(workflow_id, edge_id)


@router.put("/{edge_id}", response_model=WorkflowEdgeResponse)
async def update_edge(
    workflow_id: UUID,
    edge_id: UUID,
    data: WorkflowEdgeUpdate,
    session: DbSession,
    _: ApiKey,
) -> WorkflowEdgeResponse:
    """Update an edge."""
    service = WorkflowService(session)
    return await service.update_edge(workflow_id, edge_id, data)


@router.delete("/{edge_id}", status_code=204)
async def delete_edge(
    workflow_id: UUID,
    edge_id: UUID,
    session: DbSession,
    _: ApiKey,
) -> None:
    """Delete an edge."""
    service = WorkflowService(session)
    await service.delete_edge(workflow_id, edge_id)
