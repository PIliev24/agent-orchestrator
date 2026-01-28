"""Pydantic schemas for Tool API."""

from typing import Optional
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
    description: Optional[str] = Field(
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
    implementation_ref: str = Field(
        ...,
        description="Reference to tool implementation (e.g., 'builtin:calculator')",
        examples=["builtin:calculator", "custom:my_tool"],
    )
    config: Optional[dict] = Field(
        default=None,
        description="Additional tool configuration",
    )


class ToolUpdate(BaseModel):
    """Schema for updating a tool."""

    name: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=128,
    )
    description: Optional[str] = None
    function_schema: Optional[dict] = None
    implementation_ref: Optional[str] = None
    config: Optional[dict] = None


class ToolResponse(BaseSchema, TimestampMixin):
    """Schema for tool response."""

    id: UUID
    name: str
    description: Optional[str]
    function_schema: dict
    implementation_ref: str
    config: Optional[dict]


class ToolListResponse(PaginatedResponse[ToolResponse]):
    """Paginated list of tools."""

    pass
