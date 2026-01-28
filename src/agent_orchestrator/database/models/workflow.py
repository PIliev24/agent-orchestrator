"""Workflow, WorkflowNode, and WorkflowEdge SQLAlchemy models."""

import enum
import uuid
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Enum as SQLEnum
from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from agent_orchestrator.database.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from agent_orchestrator.database.models.agent import Agent
    from agent_orchestrator.database.models.execution import Execution


class NodeType(str, enum.Enum):
    """Types of workflow nodes."""

    AGENT = "agent"  # Executes an agent
    ROUTER = "router"  # Conditional routing
    PARALLEL = "parallel"  # Fan-out to multiple nodes
    JOIN = "join"  # Fan-in / aggregation
    SUBGRAPH = "subgraph"  # Embedded workflow


class Workflow(Base, UUIDMixin, TimestampMixin):
    """Workflow definition containing nodes and edges."""

    __tablename__ = "workflows"

    name: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # State schema as JSON Schema (defines workflow state structure)
    state_schema: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Workflow metadata (tags, version, etc.)
    workflow_metadata: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Whether this is a template workflow
    is_template: Mapped[bool] = mapped_column(default=False, nullable=False)

    # Relationships
    nodes: Mapped[list["WorkflowNode"]] = relationship(
        back_populates="workflow",
        cascade="all, delete-orphan",
        foreign_keys="WorkflowNode.workflow_id",
    )
    edges: Mapped[list["WorkflowEdge"]] = relationship(
        back_populates="workflow",
        cascade="all, delete-orphan",
    )
    executions: Mapped[list["Execution"]] = relationship(
        back_populates="workflow",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Workflow(id={self.id}, name='{self.name}')>"


class WorkflowNode(Base, UUIDMixin):
    """A node within a workflow."""

    __tablename__ = "workflow_nodes"

    workflow_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workflows.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Node identifier within the workflow (used in edges)
    node_id: Mapped[str] = mapped_column(String(64), nullable=False)

    # Node type determines how the node is executed
    node_type: Mapped[NodeType] = mapped_column(SQLEnum(NodeType), nullable=False)

    # For AGENT nodes: reference to the agent
    agent_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agents.id", ondelete="SET NULL"),
        nullable=True,
    )

    # For ROUTER nodes: routing configuration
    # {"routes": [{"condition": "state.score > 0.8", "target": "high_quality"}], "default": "low_quality"}
    router_config: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # For PARALLEL nodes: list of node IDs to execute in parallel
    parallel_nodes: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)

    # For SUBGRAPH nodes: reference to another workflow
    subgraph_workflow_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workflows.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Generic node configuration
    config: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Relationships
    workflow: Mapped["Workflow"] = relationship(
        back_populates="nodes",
        foreign_keys=[workflow_id],
    )
    agent: Mapped[Optional["Agent"]] = relationship()
    subgraph_workflow: Mapped[Optional["Workflow"]] = relationship(
        foreign_keys=[subgraph_workflow_id],
    )

    def __repr__(self) -> str:
        return f"<WorkflowNode(id={self.id}, node_id='{self.node_id}', type={self.node_type})>"


class WorkflowEdge(Base, UUIDMixin):
    """An edge connecting workflow nodes."""

    __tablename__ = "workflow_edges"

    workflow_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workflows.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Source and target node IDs (references WorkflowNode.node_id)
    # Special values: "__start__" for START, "__end__" for END
    source_node: Mapped[str] = mapped_column(String(64), nullable=False)
    target_node: Mapped[str] = mapped_column(String(64), nullable=False)

    # Condition for conditional edges (Python expression evaluated against state)
    # e.g., "state.get('score', 0) > 0.8"
    condition: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    workflow: Mapped["Workflow"] = relationship(back_populates="edges")

    def __repr__(self) -> str:
        cond = f" [if {self.condition}]" if self.condition else ""
        return f"<WorkflowEdge({self.source_node} -> {self.target_node}{cond})>"
