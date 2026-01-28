"""Execution and ExecutionStep SQLAlchemy models."""

import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, Enum as SQLEnum, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from agent_orchestrator.database.models.base import Base, UUIDMixin

if TYPE_CHECKING:
    from agent_orchestrator.database.models.workflow import Workflow


class ExecutionStatus(str, enum.Enum):
    """Status of a workflow execution."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Execution(Base, UUIDMixin):
    """A single execution of a workflow."""

    __tablename__ = "executions"

    workflow_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workflows.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Thread ID for LangGraph checkpointing (allows resuming)
    thread_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)

    # Execution status
    status: Mapped[ExecutionStatus] = mapped_column(
        SQLEnum(ExecutionStatus),
        default=ExecutionStatus.PENDING,
        nullable=False,
        index=True,
    )

    # Input data provided to the workflow
    input_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Output data from the workflow (populated on completion)
    output_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Error message if execution failed
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Relationships
    workflow: Mapped["Workflow"] = relationship(back_populates="executions")
    steps: Mapped[list["ExecutionStep"]] = relationship(
        back_populates="execution",
        cascade="all, delete-orphan",
        order_by="ExecutionStep.started_at",
    )

    @property
    def duration_seconds(self) -> Optional[float]:
        """Calculate execution duration in seconds."""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None

    def __repr__(self) -> str:
        return f"<Execution(id={self.id}, status={self.status})>"


class ExecutionStep(Base, UUIDMixin):
    """A single step within a workflow execution."""

    __tablename__ = "execution_steps"

    execution_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("executions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Node ID that was executed
    node_id: Mapped[str] = mapped_column(String(64), nullable=False)

    # Step status
    status: Mapped[ExecutionStatus] = mapped_column(
        SQLEnum(ExecutionStatus),
        default=ExecutionStatus.PENDING,
        nullable=False,
    )

    # Input to the node
    input_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Output from the node
    output_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Error message if step failed
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Timestamps
    started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Relationships
    execution: Mapped["Execution"] = relationship(back_populates="steps")

    def __repr__(self) -> str:
        return f"<ExecutionStep(id={self.id}, node_id='{self.node_id}', status={self.status})>"
