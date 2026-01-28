"""Agent API routes."""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Query

from agent_orchestrator.api.dependencies import ApiKey, DbSession
from agent_orchestrator.core.schemas.agent import (
    AgentCreate,
    AgentListResponse,
    AgentResponse,
    AgentUpdate,
)
from agent_orchestrator.services.agent_service import AgentService

router = APIRouter()


@router.post("", response_model=AgentResponse, status_code=201)
async def create_agent(
    data: AgentCreate,
    session: DbSession,
    _: ApiKey,
) -> AgentResponse:
    """Create a new agent.

    Args:
        data: Agent creation data.
        session: Database session.

    Returns:
        Created agent.
    """
    service = AgentService(session)
    return await service.create(data)


@router.get("", response_model=AgentListResponse)
async def list_agents(
    session: DbSession,
    _: ApiKey,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    search: Optional[str] = Query(default=None),
) -> AgentListResponse:
    """List agents with pagination.

    Args:
        session: Database session.
        page: Page number.
        page_size: Items per page.
        search: Optional search term.

    Returns:
        Paginated list of agents.
    """
    service = AgentService(session)
    agents, total = await service.list(page=page, page_size=page_size, search=search)
    return AgentListResponse(
        items=agents,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{agent_id}", response_model=AgentResponse)
async def get_agent(
    agent_id: UUID,
    session: DbSession,
    _: ApiKey,
) -> AgentResponse:
    """Get an agent by ID.

    Args:
        agent_id: Agent ID.
        session: Database session.

    Returns:
        Agent details.
    """
    service = AgentService(session)
    return await service.get(agent_id)


@router.put("/{agent_id}", response_model=AgentResponse)
async def update_agent(
    agent_id: UUID,
    data: AgentUpdate,
    session: DbSession,
    _: ApiKey,
) -> AgentResponse:
    """Update an agent.

    Args:
        agent_id: Agent ID.
        data: Update data.
        session: Database session.

    Returns:
        Updated agent.
    """
    service = AgentService(session)
    return await service.update(agent_id, data)


@router.delete("/{agent_id}", status_code=204)
async def delete_agent(
    agent_id: UUID,
    session: DbSession,
    _: ApiKey,
) -> None:
    """Delete an agent.

    Args:
        agent_id: Agent ID.
        session: Database session.
    """
    service = AgentService(session)
    await service.delete(agent_id)
