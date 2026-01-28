"""Tool SQLAlchemy model."""

import uuid
from typing import TYPE_CHECKING, Optional

from sqlalchemy import String, Text
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from agent_orchestrator.database.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from agent_orchestrator.database.models.agent import AgentTool


class Tool(Base, UUIDMixin, TimestampMixin):
    """Tool definition that can be bound to agents."""

    __tablename__ = "tools"

    name: Mapped[str] = mapped_column(String(128), nullable=False, unique=True, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # JSON Schema for the tool's function signature
    function_schema: Mapped[dict] = mapped_column(JSON, nullable=False)

    # Reference to the implementation (e.g., "builtin:calculator", "custom:my_tool")
    implementation_ref: Mapped[str] = mapped_column(String(256), nullable=False)

    # Additional configuration for the tool
    config: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Relationships
    agent_tools: Mapped[list["AgentTool"]] = relationship(
        back_populates="tool",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Tool(id={self.id}, name='{self.name}')>"
