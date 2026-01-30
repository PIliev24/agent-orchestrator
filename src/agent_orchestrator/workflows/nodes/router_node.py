"""Router node implementation for conditional branching."""

from collections.abc import Callable
from typing import Any


def create_router_node(
    router_config: dict,
) -> Callable[[dict[str, Any]], str]:
    """Create a router node function.

    The router evaluates conditions against the state and returns
    the target node name for the next step.

    Args:
        router_config: Router configuration with routes and default.
            Format: {
                "routes": [
                    {"condition": "state.get('score', 0) > 0.8", "target": "high"},
                    {"condition": "state.get('score', 0) > 0.5", "target": "medium"},
                ],
                "default": "low"
            }

    Returns:
        Function that returns the target node name.
    """
    routes = router_config.get("routes", [])
    default_target = router_config.get("default", "__end__")

    def router(state: dict[str, Any]) -> str:
        """Evaluate routing conditions and return target node.

        Args:
            state: Current workflow state.

        Returns:
            Target node name.
        """
        for route in routes:
            condition = route.get("condition", "")
            target = route.get("target", default_target)

            try:
                # Evaluate condition with limited namespace
                # Only expose 'state' variable for safety
                result = eval(
                    condition,
                    {"__builtins__": {}},
                    {"state": state},
                )
                if result:
                    return target
            except Exception:
                # If condition evaluation fails, continue to next route
                continue

        return default_target

    return router


def create_conditional_edges(
    router_config: dict,
) -> tuple[Callable[[dict[str, Any]], str], dict[str, str]]:
    """Create conditional edges configuration for LangGraph.

    Args:
        router_config: Router configuration.

    Returns:
        Tuple of (router function, path map).
    """
    routes = router_config.get("routes", [])
    default_target = router_config.get("default", "__end__")

    # Build path map
    path_map = {}
    for route in routes:
        target = route.get("target")
        if target:
            path_map[target] = target

    path_map[default_target] = default_target

    router = create_router_node(router_config)

    return router, path_map
