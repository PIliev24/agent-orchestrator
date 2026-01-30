"""Execution step sub-resource routes."""

from uuid import UUID

from fastapi import APIRouter, Query

from agent_orchestrator.api.dependencies import ApiKey, DbSession
from agent_orchestrator.core.schemas.execution import (
    ExecutionStepListResponse,
    ExecutionStepResponse,
)
from agent_orchestrator.services.execution_service import ExecutionService

router = APIRouter()


@router.get("", response_model=ExecutionStepListResponse)
async def list_steps(
    execution_id: UUID,
    session: DbSession,
    _: ApiKey,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> ExecutionStepListResponse:
    """List steps for an execution."""
    service = ExecutionService(session)
    steps, total = await service.list_steps(execution_id, page=page, page_size=page_size)
    return ExecutionStepListResponse(
        items=steps,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{step_id}", response_model=ExecutionStepResponse)
async def get_step(
    execution_id: UUID,
    step_id: UUID,
    session: DbSession,
    _: ApiKey,
) -> ExecutionStepResponse:
    """Get a single execution step."""
    service = ExecutionService(session)
    return await service.get_step(execution_id, step_id)
