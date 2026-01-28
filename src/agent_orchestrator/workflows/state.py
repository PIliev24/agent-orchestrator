"""Workflow state management."""

from typing import Annotated, Any, Optional, TypedDict

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class WorkflowState(TypedDict, total=False):
    """Default workflow state schema.

    This provides a base state structure that can be extended
    via the workflow's state_schema configuration.
    """

    # Input data provided when starting the workflow
    input: dict[str, Any]

    # Message history (for agent nodes)
    messages: Annotated[list[BaseMessage], add_messages]

    # Intermediate results from nodes
    intermediate: dict[str, Any]

    # Final output (set by the last node)
    output: Any

    # Current node being executed (for tracking)
    current_node: Optional[str]

    # Error information if workflow fails
    error: Optional[str]

    # Metadata about the execution
    metadata: dict[str, Any]


def create_state_class(state_schema: Optional[dict] = None) -> type[TypedDict]:
    """Create a TypedDict class from a JSON Schema.

    Args:
        state_schema: Optional JSON Schema defining additional state fields.
            If None, returns the default WorkflowState.

    Returns:
        TypedDict class for the workflow state.
    """
    if not state_schema:
        return WorkflowState

    # For now, we use the default WorkflowState
    # A more sophisticated implementation could dynamically create
    # TypedDict classes from JSON Schema
    return WorkflowState


def merge_state(current: dict, updates: dict) -> dict:
    """Merge state updates into current state.

    Handles special merging for 'messages' (append) and 'intermediate' (deep merge).

    Args:
        current: Current state dictionary.
        updates: Updates to apply.

    Returns:
        Merged state dictionary.
    """
    result = current.copy()

    for key, value in updates.items():
        if key == "intermediate" and key in result and isinstance(result[key], dict):
            # Deep merge intermediate results
            result[key] = {**result[key], **value}
        else:
            result[key] = value

    return result
