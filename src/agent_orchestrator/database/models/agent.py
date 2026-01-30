"""Agent SQLAlchemy model."""

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from agent_orchestrator.database.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from agent_orchestrator.database.models.tool import Tool


class Agent(Base, UUIDMixin, TimestampMixin):
    """Persisted agent configuration."""

    __tablename__ = "agents"

    name: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # System prompt / instructions for the agent
    instructions: Mapped[str] = mapped_column(Text, nullable=False)

    # Model configuration as JSON
    # {"provider": "openai", "model_name": "gpt-4o", "temperature": 0.7, ...}
    llm_config: Mapped[dict] = mapped_column(JSON, nullable=False)

    # Optional output schema for structured output
    output_schema: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Relationships
    agent_tools: Mapped[list["AgentTool"]] = relationship(
        back_populates="agent",
        cascade="all, delete-orphan",
    )

    @property
    def tools(self) -> list["Tool"]:
        """Get list of tools bound to this agent."""
        return [at.tool for at in self.agent_tools]

    @property
    def tool_ids(self) -> list[uuid.UUID]:
        """Get list of tool IDs bound to this agent."""
        return [at.tool_id for at in self.agent_tools]

    def __repr__(self) -> str:
        return f"<Agent(id={self.id}, name='{self.name}')>"


class AgentTool(Base):
    """Association table for Agent-Tool many-to-many relationship."""

    __tablename__ = "agent_tools"

    agent_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agents.id", ondelete="CASCADE"),
        primary_key=True,
    )
    tool_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tools.id", ondelete="CASCADE"),
        primary_key=True,
    )

    # Relationships
    agent: Mapped["Agent"] = relationship(back_populates="agent_tools")
    tool: Mapped["Tool"] = relationship(back_populates="agent_tools")

    def __repr__(self) -> str:
        return f"<AgentTool(agent_id={self.agent_id}, tool_id={self.tool_id})>"
