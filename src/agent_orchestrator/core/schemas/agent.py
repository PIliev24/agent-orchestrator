"""Pydantic schemas for Agent API."""

from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field

from agent_orchestrator.core.schemas.common import BaseSchema, PaginatedResponse, TimestampMixin


class ModelConfig(BaseModel):
    """Configuration for the AI model.

    Note: Temperature is always set to 0 for deterministic, reproducible outputs.
    """

    provider: str = Field(
        ...,
        description="AI provider: 'openai', 'anthropic', or 'google'",
        examples=["openai", "anthropic", "google"],
    )
    model_name: str = Field(
        ...,
        description="Model name/identifier",
        examples=["gpt-4o", "claude-sonnet-4-20250514", "gemini-2.0-flash"],
    )
    max_tokens: Optional[int] = Field(
        default=None,
        ge=1,
        description="Maximum tokens to generate",
    )


class AgentCreate(BaseModel):
    """Schema for creating a new agent."""

    name: str = Field(
        ...,
        min_length=1,
        max_length=128,
        description="Agent name",
        examples=["Question Generator"],
    )
    description: Optional[str] = Field(
        default=None,
        description="Agent description",
    )
    instructions: str = Field(
        ...,
        min_length=1,
        description="System prompt / instructions for the agent",
        examples=["You are a helpful assistant that generates educational questions."],
    )
    llm_config: ModelConfig = Field(
        ...,
        description="AI model configuration",
    )
    output_schema: Optional[dict] = Field(
        default=None,
        description="JSON Schema for structured output",
    )
    tool_ids: list[UUID] = Field(
        default_factory=list,
        description="List of tool IDs to bind to this agent",
    )


class AgentUpdate(BaseModel):
    """Schema for updating an agent."""

    name: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=128,
    )
    description: Optional[str] = None
    instructions: Optional[str] = Field(
        default=None,
        min_length=1,
    )
    llm_config: Optional[ModelConfig] = None
    output_schema: Optional[dict] = None
    tool_ids: Optional[list[UUID]] = None


class AgentResponse(BaseSchema, TimestampMixin):
    """Schema for agent response."""

    id: UUID
    name: str
    description: Optional[str]
    instructions: str
    llm_config: dict  # ModelConfig stored as dict in DB
    output_schema: Optional[dict]
    tool_ids: list[UUID] = Field(default_factory=list)


class AgentListResponse(PaginatedResponse[AgentResponse]):
    """Paginated list of agents."""

    pass
