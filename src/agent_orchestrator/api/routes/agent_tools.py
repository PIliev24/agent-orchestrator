"""Agent-tool binding routes."""

from uuid import UUID

from fastapi import APIRouter

from agent_orchestrator.api.dependencies import ApiKey, DbSession
from agent_orchestrator.core.schemas.tool import ToolResponse
from agent_orchestrator.services.agent_service import AgentService

router = APIRouter()


@router.get("", response_model=list[ToolResponse])
async def list_agent_tools(
    agent_id: UUID,
    session: DbSession,
    _: ApiKey,
) -> list[ToolResponse]:
    """List tools bound to an agent."""
    service = AgentService(session)
    return await service.list_tools(agent_id)


@router.post("/{tool_id}", status_code=201)
async def bind_tool(
    agent_id: UUID,
    tool_id: UUID,
    session: DbSession,
    _: ApiKey,
) -> None:
    """Bind a tool to an agent."""
    service = AgentService(session)
    await service.bind_tool(agent_id, tool_id)


@router.delete("/{tool_id}", status_code=204)
async def unbind_tool(
    agent_id: UUID,
    tool_id: UUID,
    session: DbSession,
    _: ApiKey,
) -> None:
    """Unbind a tool from an agent."""
    service = AgentService(session)
    await service.unbind_tool(agent_id, tool_id)
