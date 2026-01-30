"""Workflow node sub-resource routes."""

from uuid import UUID

from fastapi import APIRouter, Query

from agent_orchestrator.api.dependencies import ApiKey, DbSession
from agent_orchestrator.core.schemas.workflow import (
    WorkflowNodeCreate,
    WorkflowNodeListResponse,
    WorkflowNodeResponse,
    WorkflowNodeUpdate,
)
from agent_orchestrator.services.workflow_service import WorkflowService

router = APIRouter()


@router.post("", response_model=WorkflowNodeResponse, status_code=201)
async def create_node(
    workflow_id: UUID,
    data: WorkflowNodeCreate,
    session: DbSession,
    _: ApiKey,
) -> WorkflowNodeResponse:
    """Add a node to a workflow."""
    service = WorkflowService(session)
    return await service.create_node(workflow_id, data)


@router.get("", response_model=WorkflowNodeListResponse)
async def list_nodes(
    workflow_id: UUID,
    session: DbSession,
    _: ApiKey,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> WorkflowNodeListResponse:
    """List nodes for a workflow."""
    service = WorkflowService(session)
    nodes, total = await service.list_nodes(workflow_id, page=page, page_size=page_size)
    return WorkflowNodeListResponse(
        items=nodes,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{node_id}", response_model=WorkflowNodeResponse)
async def get_node(
    workflow_id: UUID,
    node_id: UUID,
    session: DbSession,
    _: ApiKey,
) -> WorkflowNodeResponse:
    """Get a single node."""
    service = WorkflowService(session)
    return await service.get_node(workflow_id, node_id)


@router.put("/{node_id}", response_model=WorkflowNodeResponse)
async def update_node(
    workflow_id: UUID,
    node_id: UUID,
    data: WorkflowNodeUpdate,
    session: DbSession,
    _: ApiKey,
) -> WorkflowNodeResponse:
    """Update a node."""
    service = WorkflowService(session)
    return await service.update_node(workflow_id, node_id, data)


@router.delete("/{node_id}", status_code=204)
async def delete_node(
    workflow_id: UUID,
    node_id: UUID,
    session: DbSession,
    _: ApiKey,
) -> None:
    """Delete a node."""
    service = WorkflowService(session)
    await service.delete_node(workflow_id, node_id)
