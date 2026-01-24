"""Workflow configuration schemas."""

from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field

from .agent import AgentConfig, OutputSchema


class WorkflowNodeType(str, Enum):
    """Types of workflow nodes."""

    AGENT = "agent"
    CONDITIONAL = "conditional"
    PARALLEL = "parallel"
    AGGREGATOR = "aggregator"


class ConditionalRoute(BaseModel):
    """Defines a conditional routing rule."""

    condition: str = Field(..., description="Python expression evaluated against state")
    target_node: str = Field(..., description="Node ID to route to")


class WorkflowNode(BaseModel):
    """Single node in a workflow graph."""

    id: str = Field(..., min_length=1, description="Unique node identifier")
    type: WorkflowNodeType = Field(..., description="Node type")

    # For AGENT type
    agent_config: Optional[AgentConfig] = Field(default=None, description="Agent configuration")

    # For CONDITIONAL type
    routes: Optional[list[ConditionalRoute]] = Field(default=None, description="Routing rules")
    default_route: Optional[str] = Field(default=None, description="Default route if no match")

    # For PARALLEL type
    parallel_nodes: Optional[list[str]] = Field(default=None, description="Node IDs to parallelize")

    # For AGGREGATOR type
    aggregation_strategy: Optional[str] = Field(
        default=None, description="Strategy: merge, concat, custom"
    )


class WorkflowEdge(BaseModel):
    """Edge connecting workflow nodes."""

    source: str = Field(..., description="Source node ID (__start__ for entry)")
    target: str = Field(..., description="Target node ID (__end__ for termination)")
    condition: Optional[str] = Field(default=None, description="Optional condition expression")


class WorkflowConfig(BaseModel):
    """Complete workflow configuration."""

    name: str = Field(..., min_length=1, max_length=128, description="Workflow name")
    description: Optional[str] = Field(default=None, description="Workflow description")
    nodes: list[WorkflowNode] = Field(..., description="Workflow nodes")
    edges: list[WorkflowEdge] = Field(..., description="Workflow edges")
    state_schema: Optional[dict[str, Any]] = Field(default=None, description="Initial state schema")
    output_schema: Optional[OutputSchema] = Field(default=None, description="Output schema")


class WorkflowExecutionRequest(BaseModel):
    """Request to execute a workflow."""

    workflow: WorkflowConfig = Field(..., description="Workflow configuration")
    input: dict[str, Any] = Field(..., description="Initial state values")
    session_id: Optional[str] = Field(default=None, description="Session ID")
    stream: bool = Field(default=False, description="Enable streaming")


class WorkflowExecutionResponse(BaseModel):
    """Response from workflow execution."""

    workflow_name: str = Field(..., description="Executed workflow name")
    output: dict[str, Any] = Field(..., description="Final state")
    session_id: Optional[str] = Field(default=None, description="Session ID")
    execution_trace: list[dict[str, Any]] = Field(
        default_factory=list, description="Execution trace"
    )
