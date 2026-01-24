"""Tool registration and management."""

import json
from typing import Any, Optional

import httpx

from agent_orchestrator.core.exceptions import ToolExecutionError, ToolNotFoundError
from agent_orchestrator.core.interfaces.tool import BaseTool
from agent_orchestrator.core.schemas.agent import ToolDefinition
from agent_orchestrator.core.schemas.tool import ToolResult


class CalculatorTool(BaseTool):
    """Built-in calculator tool for math expressions."""

    @property
    def name(self) -> str:
        return "calculator"

    @property
    def description(self) -> str:
        return "Evaluate mathematical expressions safely. Supports basic arithmetic operations."

    @property
    def parameters_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "expression": {
                    "type": "string",
                    "description": "Mathematical expression to evaluate (e.g., '2 + 2', '10 * 5')",
                }
            },
            "required": ["expression"],
        }

    async def execute(self, **kwargs: Any) -> ToolResult:
        """Evaluate math expression safely."""
        expression = kwargs.get("expression", "")
        try:
            allowed_chars = set("0123456789+-*/().% ")
            if not all(c in allowed_chars for c in expression):
                raise ValueError("Invalid characters in expression")
            result = eval(expression, {"__builtins__": {}}, {})
            return ToolResult(success=True, result=result)
        except Exception as e:
            return ToolResult(success=False, result=None, error=str(e))


class HTTPTool(BaseTool):
    """Tool that calls an external HTTP endpoint."""

    def __init__(self, name: str, description: str, parameters: dict[str, Any], endpoint: str):
        self._name = name
        self._description = description
        self._parameters = parameters
        self._endpoint = endpoint

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return self._description

    @property
    def parameters_schema(self) -> dict[str, Any]:
        return self._parameters

    async def execute(self, **kwargs: Any) -> ToolResult:
        """Execute HTTP tool by calling external endpoint."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self._endpoint,
                    json=kwargs,
                    timeout=30.0,
                )
                response.raise_for_status()
                return ToolResult(success=True, result=response.json())
        except Exception as e:
            return ToolResult(success=False, result=None, error=str(e))


class ToolRegistry:
    """Registry for managing tools."""

    def __init__(self) -> None:
        self._built_in_tools: dict[str, BaseTool] = {
            "calculator": CalculatorTool(),
        }
        self._custom_tools: dict[str, BaseTool] = {}

    def register_tool(self, tool: BaseTool) -> None:
        """Register a tool."""
        self._custom_tools[tool.name] = tool

    def register_custom_tool(self, definition: ToolDefinition) -> None:
        """Register a custom tool from definition."""
        if definition.http_endpoint:
            tool = HTTPTool(
                name=definition.name,
                description=definition.description,
                parameters=definition.parameters,
                endpoint=definition.http_endpoint,
            )
            self._custom_tools[definition.name] = tool
        elif definition.implementation:
            if definition.implementation in self._built_in_tools:
                self._custom_tools[definition.name] = self._built_in_tools[definition.implementation]
            else:
                raise ToolNotFoundError(definition.implementation)

    def get_tool(self, name: str) -> BaseTool:
        """Get a tool by name."""
        if name in self._custom_tools:
            return self._custom_tools[name]
        if name in self._built_in_tools:
            return self._built_in_tools[name]
        raise ToolNotFoundError(name)

    def get_all_tools(self) -> list[BaseTool]:
        """Get all registered tools."""
        all_tools = dict(self._built_in_tools)
        all_tools.update(self._custom_tools)
        return list(all_tools.values())

    def list_built_in_tools(self) -> list[str]:
        """List built-in tool names."""
        return list(self._built_in_tools.keys())

    def to_provider_format(self, tool_names: list[str]) -> list[dict[str, Any]]:
        """Convert tools to provider format for LLM tool calling."""
        result = []
        for name in tool_names:
            tool = self.get_tool(name)
            result.append(
                {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.parameters_schema,
                }
            )
        return result

    def clear_custom_tools(self) -> None:
        """Clear all custom tools."""
        self._custom_tools.clear()
