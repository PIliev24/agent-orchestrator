"""Tool definition schemas."""

from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class BuiltInToolType(str, Enum):
    """Built-in tool types."""

    CALCULATOR = "calculator"
    WEB_SEARCH = "web_search"
    CODE_EXECUTOR = "code_executor"


class ToolParameter(BaseModel):
    """Parameter definition for a tool."""

    name: str = Field(..., description="Parameter name")
    type: str = Field(..., description="Parameter type (string, number, boolean, etc.)")
    description: str = Field(..., description="Parameter description")
    required: bool = Field(default=True, description="Whether parameter is required")
    default: Optional[Any] = Field(default=None, description="Default value")


class ToolResult(BaseModel):
    """Result from tool execution."""

    success: bool = Field(..., description="Whether execution succeeded")
    result: Any = Field(..., description="Tool execution result")
    error: Optional[str] = Field(default=None, description="Error message if failed")
