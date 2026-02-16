"""Pydantic schemas for Agent API."""

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
        examples=["gpt-5.2", "claude-sonnet-4-20250514", "gemini-2.0-flash"],
    )
    max_tokens: int | None = Field(
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
    description: str | None = Field(
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
    output_schema: dict | None = Field(
        default=None,
        description="JSON Schema for structured output",
    )
    tool_ids: list[UUID] = Field(
        default_factory=list,
        description="List of tool IDs to bind to this agent",
    )


class AgentUpdate(BaseModel):
    """Schema for updating an agent."""

    name: str | None = Field(
        default=None,
        min_length=1,
        max_length=128,
    )
    description: str | None = None
    instructions: str | None = Field(
        default=None,
        min_length=1,
    )
    llm_config: ModelConfig | None = None
    output_schema: dict | None = None
    tool_ids: list[UUID] | None = None


class AgentResponse(BaseSchema, TimestampMixin):
    """Schema for agent response."""

    id: UUID
    name: str
    description: str | None
    instructions: str
    llm_config: dict  # ModelConfig stored as dict in DB
    output_schema: dict | None
    tool_ids: list[UUID] = Field(default_factory=list)


class AgentListResponse(PaginatedResponse[AgentResponse]):
    """Paginated list of agents."""

    pass
