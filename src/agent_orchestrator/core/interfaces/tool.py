"""Tool interface."""

from abc import ABC, abstractmethod
from typing import Any

from agent_orchestrator.core.schemas.tool import ToolResult


class BaseTool(ABC):
    """Abstract base class for tool implementations."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique tool identifier."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Tool description for LLM."""
        pass

    @property
    @abstractmethod
    def parameters_schema(self) -> dict[str, Any]:
        """JSON Schema for tool parameters."""
        pass

    @abstractmethod
    async def execute(self, **kwargs: Any) -> ToolResult:
        """Execute the tool with given parameters."""
        pass
