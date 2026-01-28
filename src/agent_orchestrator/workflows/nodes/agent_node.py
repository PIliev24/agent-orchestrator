"""Agent node implementation."""

from typing import Any, Callable, Optional
from uuid import UUID

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from sqlalchemy.ext.asyncio import AsyncSession

from agent_orchestrator.database.models.agent import Agent
from agent_orchestrator.providers.base import ProviderConfig
from agent_orchestrator.providers.factory import ProviderFactory
from agent_orchestrator.tools.registry import ToolRegistry


async def create_agent_node(
    agent_id: UUID,
    session: AsyncSession,
) -> Callable[[dict[str, Any]], dict[str, Any]]:
    """Create an agent node function.

    Args:
        agent_id: ID of the agent to use.
        session: Database session.

    Returns:
        Async function that executes the agent.
    """
    # Load agent from database
    agent = await session.get(Agent, agent_id)
    if not agent:
        raise ValueError(f"Agent {agent_id} not found")

    # Create provider config
    provider_config = ProviderConfig(**agent.llm_config)

    # Load tools if agent has any
    tools = []
    for agent_tool in agent.agent_tools:
        tool = agent_tool.tool
        try:
            lc_tool = ToolRegistry.get_langchain_tool(
                tool.implementation_ref,
                tool.config,
            )
            tools.append(lc_tool)
        except Exception:
            # Skip tools that fail to load
            pass

    # Create the model
    if agent.output_schema:
        model = ProviderFactory.create_model(
            provider_config,
            output_schema=agent.output_schema,
        )
    elif tools:
        model = ProviderFactory.create_model(provider_config, tools=tools)
    else:
        model = ProviderFactory.create_model(provider_config)

    # Store agent data for the node function
    agent_instructions = agent.instructions
    agent_name = agent.name

    async def agent_node(state: dict[str, Any]) -> dict[str, Any]:
        """Execute the agent with the current state.

        Args:
            state: Current workflow state.

        Returns:
            Updated state with agent output.
        """
        # Build messages
        messages = []

        # Add system message with instructions
        messages.append(SystemMessage(content=agent_instructions))

        # Add conversation history if present
        if "messages" in state:
            messages.extend(state["messages"])

        # If no messages yet, create initial message from input
        if len(messages) == 1:  # Only system message
            input_data = state.get("input", {})
            if isinstance(input_data, dict):
                # Convert input dict to a message
                content = "\n".join(f"{k}: {v}" for k, v in input_data.items())
            else:
                content = str(input_data)
            messages.append(HumanMessage(content=content))

        # Invoke the model
        response = await model.ainvoke(messages)

        # Extract output
        if hasattr(response, "content"):
            output = response.content
        else:
            output = response

        # Build state updates
        updates: dict[str, Any] = {
            "current_node": agent_name,
            "messages": [response] if isinstance(response, AIMessage) else [],
        }

        # Store in intermediate results
        intermediate = state.get("intermediate", {})
        intermediate[agent_name] = output
        updates["intermediate"] = intermediate

        # If this appears to be the final output, set it
        # (The workflow can override this in subsequent nodes)
        updates["output"] = output

        return updates

    return agent_node


def create_agent_node_sync(
    agent: Agent,
    tools: Optional[list] = None,
) -> Callable[[dict[str, Any]], dict[str, Any]]:
    """Create an agent node function from an already-loaded agent.

    This is a synchronous version for use when the agent is already loaded.

    Args:
        agent: Loaded Agent model.
        tools: Optional list of LangChain tools.

    Returns:
        Async function that executes the agent.
    """
    # Create provider config
    provider_config = ProviderConfig(**agent.llm_config)

    # Create the model
    if agent.output_schema:
        model = ProviderFactory.create_model(
            provider_config,
            output_schema=agent.output_schema,
        )
    elif tools:
        model = ProviderFactory.create_model(provider_config, tools=tools)
    else:
        model = ProviderFactory.create_model(provider_config)

    agent_instructions = agent.instructions
    agent_name = agent.name

    async def agent_node(state: dict[str, Any]) -> dict[str, Any]:
        """Execute the agent with the current state."""
        messages = []
        messages.append(SystemMessage(content=agent_instructions))

        if "messages" in state:
            messages.extend(state["messages"])

        if len(messages) == 1:
            input_data = state.get("input", {})
            if isinstance(input_data, dict):
                content = "\n".join(f"{k}: {v}" for k, v in input_data.items())
            else:
                content = str(input_data)
            messages.append(HumanMessage(content=content))

        response = await model.ainvoke(messages)

        if hasattr(response, "content"):
            output = response.content
        else:
            output = response

        updates: dict[str, Any] = {
            "current_node": agent_name,
            "messages": [response] if isinstance(response, AIMessage) else [],
        }

        intermediate = state.get("intermediate", {})
        intermediate[agent_name] = output
        updates["intermediate"] = intermediate
        updates["output"] = output

        return updates

    return agent_node
