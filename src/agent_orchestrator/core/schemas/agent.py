"""Agent configuration schemas."""

from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class ModelProvider(str, Enum):
    """Supported AI model providers."""

    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"


class ModelIdentifier(BaseModel):
    """Model selection configuration."""

    provider: ModelProvider = Field(..., description="AI provider to use")
    model_name: str = Field(..., description="Model name (e.g., gpt-4, claude-3-5-sonnet)")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0, description="Sampling temperature")
    max_tokens: Optional[int] = Field(default=None, ge=1, description="Maximum tokens to generate")


class ToolDefinition(BaseModel):
    """Custom tool definition passed via API."""

    name: str = Field(..., min_length=1, max_length=64, description="Unique tool identifier")
    description: str = Field(..., min_length=1, description="Tool description for the LLM")
    parameters: dict[str, Any] = Field(..., description="JSON Schema for tool parameters")
    implementation: Optional[str] = Field(default=None, description="Built-in tool name reference")
    http_endpoint: Optional[str] = Field(default=None, description="External HTTP tool endpoint")


class OutputSchema(BaseModel):
    """JSON Schema for structured output."""

    schema_type: str = Field(default="json_schema", description="Schema format type")
    schema_definition: dict[str, Any] = Field(..., description="JSON Schema object")
    strict: bool = Field(default=True, description="Enforce strict schema validation")


class AgentConfig(BaseModel):
    """Complete agent configuration from API payload."""

    name: str = Field(..., min_length=1, max_length=128, description="Agent name")
    instructions: str = Field(..., min_length=1, description="System prompt/instructions")
    model: ModelIdentifier = Field(..., description="Model configuration")
    tools: list[ToolDefinition] = Field(default_factory=list, description="Available tools")
    output_schema: Optional[OutputSchema] = Field(default=None, description="Output schema")
    file_context: Optional[list[str]] = Field(default=None, description="File IDs for context")


class AgentExecutionRequest(BaseModel):
    """Request to execute an agent."""

    agent: AgentConfig = Field(..., description="Agent configuration")
    input: str = Field(..., description="User input/query")
    session_id: Optional[str] = Field(default=None, description="Session ID for continuity")
    stream: bool = Field(default=False, description="Enable streaming response")


class AgentExecutionResponse(BaseModel):
    """Response from agent execution."""

    agent_name: str = Field(..., description="Name of executed agent")
    output: Any = Field(..., description="Agent output (string or structured)")
    session_id: Optional[str] = Field(default=None, description="Session ID used")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Execution metadata")
