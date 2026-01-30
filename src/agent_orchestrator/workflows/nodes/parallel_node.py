"""Parallel node implementation for fan-out/fan-in patterns."""

from collections.abc import Callable
from typing import Any

from langgraph.types import Send


def create_parallel_node(
    parallel_nodes: list[str],
    fan_out_key: str | None = None,
) -> Callable[[dict[str, Any]], list[Send]]:
    """Create a parallel dispatch node using LangGraph's Send API.

    Args:
        parallel_nodes: List of node IDs to execute in parallel.
        fan_out_key: Optional key in state to iterate over for dynamic fan-out.
            If provided, creates one Send per item in state[fan_out_key].

    Returns:
        Function that returns list of Send objects for parallel execution.
    """

    def parallel_dispatcher(state: dict[str, Any]) -> list[Send]:
        """Dispatch to multiple nodes in parallel.

        Args:
            state: Current workflow state.

        Returns:
            List of Send objects for parallel execution.
        """
        sends = []

        if fan_out_key:
            # Dynamic fan-out: create one Send per item
            # Check top-level state first, then inside input
            items = state.get(fan_out_key)
            if items is None:
                input_data = state.get("input", {})
                if isinstance(input_data, dict):
                    items = input_data.get(fan_out_key)
            if isinstance(items, list):
                for i, item in enumerate(items):
                    for target_node in parallel_nodes:
                        # Create state copy with the specific item
                        item_state = {
                            **state,
                            "parallel_item": item,
                            "parallel_index": i,
                            "metadata": {
                                **state.get("metadata", {}),
                                "parallel_item": item,
                                "parallel_index": i,
                            },
                        }
                        sends.append(Send(target_node, item_state))
        else:
            # Static fan-out: send same state to all nodes
            for target_node in parallel_nodes:
                sends.append(Send(target_node, state))

        return sends

    return parallel_dispatcher


def create_join_node(
    aggregation_strategy: str = "merge",
    output_key: str = "parallel_results",
) -> Callable[[dict[str, Any]], dict[str, Any]]:
    """Create a join node that aggregates results from parallel branches.

    Args:
        aggregation_strategy: How to combine results:
            - "merge": Merge all results into a single dict
            - "list": Collect results into a list
            - "concat": Concatenate string outputs
            - "first": Take first non-None result
        output_key: Key to store aggregated results.

    Returns:
        Function that aggregates parallel results.
    """

    async def join_aggregator(state: dict[str, Any]) -> dict[str, Any]:
        """Aggregate results from parallel branches.

        Args:
            state: State with parallel results.

        Returns:
            Updated state with aggregated results.
        """
        # Collect results from intermediate storage
        intermediate = state.get("intermediate", {})

        if aggregation_strategy == "merge":
            # Merge all intermediate results
            aggregated = {}
            for key, value in intermediate.items():
                if isinstance(value, dict):
                    aggregated.update(value)
                else:
                    aggregated[key] = value

        elif aggregation_strategy == "list":
            # Collect as list
            aggregated = list(intermediate.values())

        elif aggregation_strategy == "concat":
            # Concatenate string values
            parts = []
            for value in intermediate.values():
                if value is not None:
                    parts.append(str(value))
            aggregated = "\n".join(parts)

        elif aggregation_strategy == "first":
            # Take first non-None result
            aggregated = None
            for value in intermediate.values():
                if value is not None:
                    aggregated = value
                    break

        else:
            # Default to merge
            aggregated = dict(intermediate)

        return {
            output_key: aggregated,
            "output": aggregated,
        }

    return join_aggregator
