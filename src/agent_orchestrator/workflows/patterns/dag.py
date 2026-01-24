"""DAG workflow pattern with branching and conditional routing."""

from typing import Any, Callable

from langgraph.graph import END, START, StateGraph


def build_dag_workflow(
    nodes: dict[str, Callable[..., dict[str, Any]]],
    edges: list[tuple[str, str]],
    conditional_edges: list[tuple[str, Callable[..., str], dict[str, str]]],
    state_class: type,
) -> StateGraph:
    """Build a DAG workflow with branching and conditional routing.

    Args:
        nodes: Dictionary mapping node IDs to node functions.
        edges: List of direct edges as (source, target) tuples.
        conditional_edges: List of (source, condition_func, route_map) tuples.
        state_class: The state TypedDict class.

    Returns:
        Compiled StateGraph for the DAG workflow.
    """
    builder = StateGraph(state_class)

    for node_id, node_func in nodes.items():
        builder.add_node(node_id, node_func)

    for source, target in edges:
        src = START if source == "__start__" else source
        tgt = END if target == "__end__" else target
        builder.add_edge(src, tgt)

    for source, condition_func, route_map in conditional_edges:
        processed_map = {}
        for key, target in route_map.items():
            processed_map[key] = END if target == "__end__" else target
        builder.add_conditional_edges(source, condition_func, processed_map)

    return builder.compile()


def create_condition_router(condition_expr: str) -> Callable[[dict[str, Any]], str]:
    """Create a condition function from expression string.

    Args:
        condition_expr: Python expression evaluated against state.

    Returns:
        A function that takes state and returns the route key.
    """

    def router(state: dict[str, Any]) -> str:
        try:
            result = eval(condition_expr, {"__builtins__": {}}, {"state": state})
            return str(result)
        except Exception:
            return "default"

    return router
