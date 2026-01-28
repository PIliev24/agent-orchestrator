"""Tool API routes."""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Query

from agent_orchestrator.api.dependencies import ApiKey, DbSession
from agent_orchestrator.core.schemas.tool import (
    ToolCreate,
    ToolListResponse,
    ToolResponse,
    ToolUpdate,
)
from agent_orchestrator.services.tool_service import ToolService

router = APIRouter()


@router.post("", response_model=ToolResponse, status_code=201)
async def create_tool(
    data: ToolCreate,
    session: DbSession,
    _: ApiKey,
) -> ToolResponse:
    """Create a new tool.

    Args:
        data: Tool creation data.
        session: Database session.

    Returns:
        Created tool.
    """
    service = ToolService(session)
    return await service.create(data)


@router.get("", response_model=ToolListResponse)
async def list_tools(
    session: DbSession,
    _: ApiKey,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    search: Optional[str] = Query(default=None),
) -> ToolListResponse:
    """List tools with pagination.

    Args:
        session: Database session.
        page: Page number.
        page_size: Items per page.
        search: Optional search term.

    Returns:
        Paginated list of tools.
    """
    service = ToolService(session)
    tools, total = await service.list(page=page, page_size=page_size, search=search)
    return ToolListResponse(
        items=tools,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{tool_id}", response_model=ToolResponse)
async def get_tool(
    tool_id: UUID,
    session: DbSession,
    _: ApiKey,
) -> ToolResponse:
    """Get a tool by ID.

    Args:
        tool_id: Tool ID.
        session: Database session.

    Returns:
        Tool details.
    """
    service = ToolService(session)
    return await service.get(tool_id)


@router.put("/{tool_id}", response_model=ToolResponse)
async def update_tool(
    tool_id: UUID,
    data: ToolUpdate,
    session: DbSession,
    _: ApiKey,
) -> ToolResponse:
    """Update a tool.

    Args:
        tool_id: Tool ID.
        data: Update data.
        session: Database session.

    Returns:
        Updated tool.
    """
    service = ToolService(session)
    return await service.update(tool_id, data)


@router.delete("/{tool_id}", status_code=204)
async def delete_tool(
    tool_id: UUID,
    session: DbSession,
    _: ApiKey,
) -> None:
    """Delete a tool.

    Args:
        tool_id: Tool ID.
        session: Database session.
    """
    service = ToolService(session)
    await service.delete(tool_id)
