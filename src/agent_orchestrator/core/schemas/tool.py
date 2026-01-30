"""Pydantic schemas for Tool API."""

from uuid import UUID

from pydantic import BaseModel, Field

from agent_orchestrator.core.schemas.common import BaseSchema, PaginatedResponse, TimestampMixin


class ToolCreate(BaseModel):
    """Schema for creating a new tool."""

    name: str = Field(
        ...,
        min_length=1,
        max_length=128,
        description="Tool name (must be unique)",
        examples=["calculator", "web_search"],
    )
    description: str | None = Field(
        default=None,
        description="Tool description",
        examples=["Performs mathematical calculations"],
    )
    function_schema: dict = Field(
        ...,
        description="JSON Schema describing the tool's function signature",
        examples=[
            {
                "name": "calculator",
                "description": "Evaluate a mathematical expression",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "expression": {
                            "type": "string",
                            "description": "Mathematical expression to evaluate",
                        }
                    },
                    "required": ["expression"],
                },
            }
        ],
    )
    config: dict | None = Field(
        default=None,
        description="Additional tool configuration",
    )


class ToolUpdate(BaseModel):
    """Schema for updating a tool."""

    name: str | None = Field(
        default=None,
        min_length=1,
        max_length=128,
    )
    description: str | None = None
    function_schema: dict | None = None
    config: dict | None = None


class ToolResponse(BaseSchema, TimestampMixin):
    """Schema for tool response."""

    id: UUID
    name: str
    description: str | None
    function_schema: dict
    config: dict | None


class ToolListResponse(PaginatedResponse[ToolResponse]):
    """Paginated list of tools."""

    pass
