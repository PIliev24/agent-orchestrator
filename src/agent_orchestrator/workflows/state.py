"""Dynamic state class creation for workflows."""

import operator
from typing import Annotated, Any, Optional

from typing_extensions import TypedDict


class BaseWorkflowState(TypedDict):
    """Base workflow state with common fields."""

    input: str
    output: Any
    messages: Annotated[list[dict[str, Any]], operator.add]
    metadata: dict[str, Any]


def create_state_class(schema: Optional[dict[str, Any]] = None) -> type:
    """Create a state class from JSON schema.

    Args:
        schema: JSON Schema defining state structure. If None, returns base state.

    Returns:
        A TypedDict class for the workflow state.
    """
    if schema is None:
        return BaseWorkflowState

    properties = schema.get("properties", {})

    annotations: dict[str, Any] = {}

    for prop_name, prop_def in properties.items():
        prop_type = prop_def.get("type", "string")

        if prop_type == "string":
            annotations[prop_name] = str
        elif prop_type == "number":
            annotations[prop_name] = float
        elif prop_type == "integer":
            annotations[prop_name] = int
        elif prop_type == "boolean":
            annotations[prop_name] = bool
        elif prop_type == "array":
            annotations[prop_name] = Annotated[list[Any], operator.add]
        elif prop_type == "object":
            annotations[prop_name] = dict[str, Any]
        else:
            annotations[prop_name] = Any

    annotations["messages"] = Annotated[list[dict[str, Any]], operator.add]
    annotations["metadata"] = dict[str, Any]

    class DynamicState(TypedDict):
        pass

    DynamicState.__annotations__ = annotations

    return DynamicState
