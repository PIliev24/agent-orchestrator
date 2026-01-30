"""Workflow state management."""

from typing import Annotated, Any, TypedDict

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


def _merge_dicts(left: dict[str, Any] | None, right: dict[str, Any] | None) -> dict[str, Any]:
    """Reducer that merges dictionaries (for concurrent updates)."""
    left = left or {}
    right = right or {}
    return {**left, **right}


def _take_last(left: Any, right: Any) -> Any:
    """Reducer that takes the most recent value."""
    return right if right is not None else left


class WorkflowState(TypedDict, total=False):
    """Default workflow state schema.

    This provides a base state structure that can be extended
    via the workflow's state_schema configuration.
    """

    # Input data provided when starting the workflow
    input: dict[str, Any]

    # Message history (for agent nodes)
    messages: Annotated[list[BaseMessage], add_messages]

    # Intermediate results from nodes (supports concurrent updates via merge)
    intermediate: Annotated[dict[str, Any], _merge_dicts]

    # Final output (set by the last node, takes last value on concurrent update)
    output: Annotated[Any, _take_last]

    # Current node being executed (takes last value on concurrent update)
    current_node: Annotated[str | None, _take_last]

    # Error information if workflow fails
    error: Annotated[str | None, _take_last]

    # Metadata about the execution (merged on concurrent updates)
    metadata: Annotated[dict[str, Any], _merge_dicts]


def create_state_class(state_schema: dict | None = None) -> type[TypedDict]:
    """Create a TypedDict class from a JSON Schema.

    Args:
        state_schema: Optional JSON Schema defining additional state fields.
            If None, returns the default WorkflowState.

    Returns:
        TypedDict class for the workflow state.
    """
    if not state_schema:
        return WorkflowState

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
