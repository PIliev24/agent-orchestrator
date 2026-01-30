"""Tool registry for managing available tools."""

from langchain_core.tools import BaseTool as LangChainBaseTool

from agent_orchestrator.core.exceptions import ToolNotFoundError
from agent_orchestrator.tools.base import BaseTool


class ToolRegistry:
    """Registry for managing tool implementations.

    Tools can be registered with a reference string (e.g., 'builtin:calculator')
    and later retrieved by that reference.
    """

    _builtin_tools: dict[str, type[BaseTool]] = {}
    _custom_tools: dict[str, BaseTool] = {}

    @classmethod
    def register_builtin(cls, name: str, tool_class: type[BaseTool]) -> None:
        """Register a built-in tool class.

        Args:
            name: Tool name (used in reference as 'builtin:{name}').
            tool_class: Tool class to register.
        """
        cls._builtin_tools[name] = tool_class

    @classmethod
    def register_custom(cls, reference: str, tool_instance: BaseTool) -> None:
        """Register a custom tool instance.

        Args:
            reference: Full reference string (e.g., 'custom:my_tool').
            tool_instance: Tool instance to register.
        """
        cls._custom_tools[reference] = tool_instance

    @classmethod
    def get_tool(cls, reference: str, config: dict | None = None) -> BaseTool:
        """Get a tool by its reference.

        Args:
            reference: Tool reference string (e.g., 'builtin:calculator').
            config: Optional configuration for the tool.

        Returns:
            Tool instance.

        Raises:
            ToolNotFoundError: If tool is not found.
        """
        if reference.startswith("builtin:"):
            name = reference.split(":", 1)[1]
            tool_class = cls._builtin_tools.get(name)
            if not tool_class:
                available = ", ".join(cls._builtin_tools.keys())
                raise ToolNotFoundError(
                    reference,
                    f"Built-in tool '{name}' not found. Available: {available}",
                )
            return tool_class(**(config or {}))

        elif reference.startswith("custom:"):
            tool_instance = cls._custom_tools.get(reference)
            if not tool_instance:
                raise ToolNotFoundError(reference, f"Custom tool '{reference}' not found")
            return tool_instance

        else:
            raise ToolNotFoundError(
                reference,
                f"Invalid tool reference format: {reference}. "
                "Expected 'builtin:name' or 'custom:name'.",
            )

    @classmethod
    def get_langchain_tool(cls, reference: str, config: dict | None = None) -> LangChainBaseTool:
        """Get a LangChain-compatible tool by reference.

        Args:
            reference: Tool reference string.
            config: Optional configuration for the tool.

        Returns:
            LangChain BaseTool instance.
        """
        tool = cls.get_tool(reference, config)
        return tool.to_langchain_tool()

    @classmethod
    def list_builtin_tools(cls) -> list[str]:
        """List all registered built-in tool names.

        Returns:
            List of built-in tool names.
        """
        return list(cls._builtin_tools.keys())

    @classmethod
    def list_custom_tools(cls) -> list[str]:
        """List all registered custom tool references.

        Returns:
            List of custom tool references.
        """
        return list(cls._custom_tools.keys())


def register_builtin_tools() -> None:
    """Register all built-in tools with the registry."""
    from agent_orchestrator.tools.builtin.calculator import CalculatorTool
    from agent_orchestrator.tools.builtin.file_writer import FileWriterTool
    from agent_orchestrator.tools.builtin.http_tool import HttpTool
    from agent_orchestrator.tools.builtin.mistral_ocr import MistralOCRTool

    ToolRegistry.register_builtin("calculator", CalculatorTool)
    ToolRegistry.register_builtin("file_writer", FileWriterTool)
    ToolRegistry.register_builtin("http", HttpTool)
    ToolRegistry.register_builtin("mistral_ocr", MistralOCRTool)
