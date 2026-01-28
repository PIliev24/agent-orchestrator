"""Base tool interface."""

from abc import ABC, abstractmethod
from typing import Any, Optional

from langchain_core.tools import BaseTool as LangChainBaseTool, tool
from pydantic import BaseModel


class ToolResult(BaseModel):
    """Result from a tool execution."""

    success: bool
    output: Any
    error: Optional[str] = None


class BaseTool(ABC):
    """Abstract base class for custom tools.

    Subclasses should implement the `execute` method and define
    the tool's name, description, and input schema.
    """

    name: str
    description: str

    @abstractmethod
    def get_input_schema(self) -> dict:
        """Get the JSON Schema for the tool's input.

        Returns:
            JSON Schema dictionary.
        """
        pass

    @abstractmethod
    async def execute(self, **kwargs: Any) -> ToolResult:
        """Execute the tool with the given arguments.

        Args:
            **kwargs: Tool arguments.

        Returns:
            ToolResult with success status and output/error.
        """
        pass

    def to_langchain_tool(self) -> LangChainBaseTool:
        """Convert to a LangChain tool.

        Returns:
            LangChain BaseTool instance.
        """
        tool_instance = self

        @tool(name=self.name, description=self.description)
        async def wrapper(**kwargs: Any) -> str:
            result = await tool_instance.execute(**kwargs)
            if result.success:
                return str(result.output)
            else:
                return f"Error: {result.error}"

        return wrapper

    def get_function_schema(self) -> dict:
        """Get the function schema for this tool.

        Returns:
            Function schema dictionary compatible with LLM function calling.
        """
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.get_input_schema(),
        }
