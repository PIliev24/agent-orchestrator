"""Tool service for CRUD operations."""

from __future__ import annotations

from typing import Optional
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from agent_orchestrator.core.exceptions import ToolNotFoundError, ValidationError
from agent_orchestrator.core.schemas.tool import ToolCreate, ToolResponse, ToolUpdate
from agent_orchestrator.database.models.tool import Tool


class ToolService:
    """Service for managing tools."""

    def __init__(self, session: AsyncSession):
        """Initialize the service.

        Args:
            session: Database session.
        """
        self._session = session

    async def create(self, data: ToolCreate) -> ToolResponse:
        """Create a new tool.

        Args:
            data: Tool creation data.

        Returns:
            Created tool response.

        Raises:
            ValidationError: If tool name already exists.
        """
        # Check for duplicate name
        existing = await self._session.execute(
            select(Tool).where(Tool.name == data.name)
        )
        if existing.scalar_one_or_none():
            raise ValidationError(
                f"Tool with name '{data.name}' already exists",
                field="name",
            )

        tool = Tool(
            name=data.name,
            description=data.description,
            function_schema=data.function_schema,
            implementation_ref=data.implementation_ref,
            config=data.config,
        )
        self._session.add(tool)
        await self._session.flush()

        return self._to_response(tool)

    async def get(self, tool_id: UUID) -> ToolResponse:
        """Get a tool by ID.

        Args:
            tool_id: Tool ID.

        Returns:
            Tool response.

        Raises:
            ToolNotFoundError: If tool doesn't exist.
        """
        tool = await self._get_tool(tool_id)
        return self._to_response(tool)

    async def get_by_name(self, name: str) -> ToolResponse:
        """Get a tool by name.

        Args:
            name: Tool name.

        Returns:
            Tool response.

        Raises:
            ToolNotFoundError: If tool doesn't exist.
        """
        result = await self._session.execute(
            select(Tool).where(Tool.name == name)
        )
        tool = result.scalar_one_or_none()

        if not tool:
            raise ToolNotFoundError(name)

        return self._to_response(tool)

    async def list(
        self,
        page: int = 1,
        page_size: int = 20,
        search: Optional[str] = None,
    ) -> tuple[list[ToolResponse], int]:
        """List tools with pagination.

        Args:
            page: Page number (1-indexed).
            page_size: Items per page.
            search: Optional search term for name.

        Returns:
            Tuple of (tools list, total count).
        """
        query = select(Tool)

        if search:
            query = query.where(Tool.name.ilike(f"%{search}%"))

        # Get total count
        count_query = select(func.count()).select_from(Tool)
        if search:
            count_query = count_query.where(Tool.name.ilike(f"%{search}%"))
        total = await self._session.scalar(count_query)

        # Apply pagination
        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size).order_by(Tool.name)

        result = await self._session.execute(query)
        tools = result.scalars().all()

        return [self._to_response(t) for t in tools], total or 0

    async def update(self, tool_id: UUID, data: ToolUpdate) -> ToolResponse:
        """Update a tool.

        Args:
            tool_id: Tool ID.
            data: Update data.

        Returns:
            Updated tool response.

        Raises:
            ToolNotFoundError: If tool doesn't exist.
            ValidationError: If new name already exists.
        """
        tool = await self._get_tool(tool_id)

        # Check for duplicate name if changing
        if data.name is not None and data.name != tool.name:
            existing = await self._session.execute(
                select(Tool).where(Tool.name == data.name)
            )
            if existing.scalar_one_or_none():
                raise ValidationError(
                    f"Tool with name '{data.name}' already exists",
                    field="name",
                )
            tool.name = data.name

        if data.description is not None:
            tool.description = data.description
        if data.function_schema is not None:
            tool.function_schema = data.function_schema
        if data.implementation_ref is not None:
            tool.implementation_ref = data.implementation_ref
        if data.config is not None:
            tool.config = data.config

        await self._session.flush()

        return self._to_response(tool)

    async def delete(self, tool_id: UUID) -> None:
        """Delete a tool.

        Args:
            tool_id: Tool ID.

        Raises:
            ToolNotFoundError: If tool doesn't exist.
        """
        tool = await self._get_tool(tool_id)
        await self._session.delete(tool)

    async def _get_tool(self, tool_id: UUID) -> Tool:
        """Get a tool by ID or raise error.

        Args:
            tool_id: Tool ID.

        Returns:
            Tool model.

        Raises:
            ToolNotFoundError: If not found.
        """
        tool = await self._session.get(Tool, tool_id)
        if not tool:
            raise ToolNotFoundError(tool_id)
        return tool

    def _to_response(self, tool: Tool) -> ToolResponse:
        """Convert Tool model to response schema.

        Args:
            tool: Tool model.

        Returns:
            ToolResponse schema.
        """
        return ToolResponse(
            id=tool.id,
            name=tool.name,
            description=tool.description,
            function_schema=tool.function_schema,
            implementation_ref=tool.implementation_ref,
            config=tool.config,
            created_at=tool.created_at,
            updated_at=tool.updated_at,
        )
