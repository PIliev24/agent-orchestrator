"""AI Provider interface."""

from abc import ABC, abstractmethod
from typing import Any, AsyncIterator, Literal, Optional

from pydantic import BaseModel, Field


class Message(BaseModel):
    """Chat message."""

    role: Literal["system", "user", "assistant", "tool"] = Field(..., description="Message role")
    content: str = Field(..., description="Message content")
    tool_calls: Optional[list[dict[str, Any]]] = Field(default=None, description="Tool calls")
    tool_call_id: Optional[str] = Field(default=None, description="Tool call ID for tool responses")


class CompletionResponse(BaseModel):
    """Response from completion."""

    content: str = Field(..., description="Response content")
    tool_calls: Optional[list[dict[str, Any]]] = Field(default=None, description="Tool calls")
    finish_reason: str = Field(..., description="Completion finish reason")
    usage: dict[str, int] = Field(..., description="Token usage statistics")


class BaseProvider(ABC):
    """Abstract base class for AI providers."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Provider identifier."""
        pass

    @property
    @abstractmethod
    def supported_models(self) -> list[str]:
        """List of supported model names."""
        pass

    @abstractmethod
    async def complete(
        self,
        messages: list[Message],
        model: str,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        tools: Optional[list[dict[str, Any]]] = None,
        output_schema: Optional[dict[str, Any]] = None,
    ) -> CompletionResponse:
        """Generate a completion."""
        pass

    @abstractmethod
    async def stream_complete(
        self,
        messages: list[Message],
        model: str,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        tools: Optional[list[dict[str, Any]]] = None,
    ) -> AsyncIterator[str]:
        """Stream a completion token by token."""
        pass
