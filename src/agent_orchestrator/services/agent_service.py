"""Agent service for CRUD operations."""

from __future__ import annotations

from typing import Optional
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from agent_orchestrator.core.exceptions import AgentNotFoundError, ToolNotFoundError
from agent_orchestrator.core.schemas.agent import AgentCreate, AgentResponse, AgentUpdate
from agent_orchestrator.database.models.agent import Agent, AgentTool
from agent_orchestrator.database.models.tool import Tool


class AgentService:
    """Service for managing agents."""

    def __init__(self, session: AsyncSession):
        """Initialize the service.

        Args:
            session: Database session.
        """
        self._session = session

    async def create(self, data: AgentCreate) -> AgentResponse:
        """Create a new agent.

        Args:
            data: Agent creation data.

        Returns:
            Created agent response.

        Raises:
            ToolNotFoundError: If any tool_id is invalid.
        """
        # Validate tool IDs if provided
        if data.tool_ids:
            await self._validate_tool_ids(data.tool_ids)

        # Create agent
        agent = Agent(
            name=data.name,
            description=data.description,
            instructions=data.instructions,
            llm_config=data.llm_config.model_dump(),
            output_schema=data.output_schema,
        )
        self._session.add(agent)
        await self._session.flush()

        # Add tool associations
        if data.tool_ids:
            for tool_id in data.tool_ids:
                agent_tool = AgentTool(agent_id=agent.id, tool_id=tool_id)
                self._session.add(agent_tool)

        await self._session.flush()

        # Reload to get relationships
        await self._session.refresh(agent, ["agent_tools"])

        return self._to_response(agent)

    async def get(self, agent_id: UUID) -> AgentResponse:
        """Get an agent by ID.

        Args:
            agent_id: Agent ID.

        Returns:
            Agent response.

        Raises:
            AgentNotFoundError: If agent doesn't exist.
        """
        agent = await self._get_agent(agent_id)
        return self._to_response(agent)

    async def list(
        self,
        page: int = 1,
        page_size: int = 20,
        search: Optional[str] = None,
    ) -> tuple[list[AgentResponse], int]:
        """List agents with pagination.

        Args:
            page: Page number (1-indexed).
            page_size: Items per page.
            search: Optional search term for name.

        Returns:
            Tuple of (agents list, total count).
        """
        # Build query
        query = select(Agent).options(selectinload(Agent.agent_tools))

        if search:
            query = query.where(Agent.name.ilike(f"%{search}%"))

        # Get total count
        count_query = select(func.count()).select_from(Agent)
        if search:
            count_query = count_query.where(Agent.name.ilike(f"%{search}%"))
        total = await self._session.scalar(count_query)

        # Apply pagination
        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size).order_by(Agent.created_at.desc())

        # Execute
        result = await self._session.execute(query)
        agents = result.scalars().all()

        return [self._to_response(a) for a in agents], total or 0

    async def update(self, agent_id: UUID, data: AgentUpdate) -> AgentResponse:
        """Update an agent.

        Args:
            agent_id: Agent ID.
            data: Update data.

        Returns:
            Updated agent response.

        Raises:
            AgentNotFoundError: If agent doesn't exist.
            ToolNotFoundError: If any tool_id is invalid.
        """
        agent = await self._get_agent(agent_id)

        # Update fields
        if data.name is not None:
            agent.name = data.name
        if data.description is not None:
            agent.description = data.description
        if data.instructions is not None:
            agent.instructions = data.instructions
        if data.llm_config is not None:
            agent.llm_config = data.llm_config.model_dump()
        if data.output_schema is not None:
            agent.output_schema = data.output_schema

        # Update tool associations
        if data.tool_ids is not None:
            await self._validate_tool_ids(data.tool_ids)

            # Remove existing associations
            for agent_tool in agent.agent_tools:
                await self._session.delete(agent_tool)

            # Add new associations
            for tool_id in data.tool_ids:
                agent_tool = AgentTool(agent_id=agent.id, tool_id=tool_id)
                self._session.add(agent_tool)

        await self._session.flush()

        # Reload to get updated relationships
        await self._session.refresh(agent, ["agent_tools"])

        return self._to_response(agent)

    async def delete(self, agent_id: UUID) -> None:
        """Delete an agent.

        Args:
            agent_id: Agent ID.

        Raises:
            AgentNotFoundError: If agent doesn't exist.
        """
        agent = await self._get_agent(agent_id)
        await self._session.delete(agent)

    async def _get_agent(self, agent_id: UUID) -> Agent:
        """Get an agent by ID or raise error.

        Args:
            agent_id: Agent ID.

        Returns:
            Agent model.

        Raises:
            AgentNotFoundError: If not found.
        """
        query = (
            select(Agent)
            .options(selectinload(Agent.agent_tools))
            .where(Agent.id == agent_id)
        )
        result = await self._session.execute(query)
        agent = result.scalar_one_or_none()

        if not agent:
            raise AgentNotFoundError(agent_id)

        return agent

    async def _validate_tool_ids(self, tool_ids: list[UUID]) -> None:
        """Validate that all tool IDs exist.

        Args:
            tool_ids: List of tool IDs to validate.

        Raises:
            ToolNotFoundError: If any tool doesn't exist.
        """
        if not tool_ids:
            return

        query = select(func.count()).select_from(Tool).where(Tool.id.in_(tool_ids))
        count = await self._session.scalar(query)

        if count != len(tool_ids):
            raise ToolNotFoundError(
                str(tool_ids),
                "One or more tool IDs are invalid",
            )

    def _to_response(self, agent: Agent) -> AgentResponse:
        """Convert Agent model to response schema.

        Args:
            agent: Agent model.

        Returns:
            AgentResponse schema.
        """
        return AgentResponse(
            id=agent.id,
            name=agent.name,
            description=agent.description,
            instructions=agent.instructions,
            llm_config=agent.llm_config,
            output_schema=agent.output_schema,
            tool_ids=[at.tool_id for at in agent.agent_tools],
            created_at=agent.created_at,
            updated_at=agent.updated_at,
        )
