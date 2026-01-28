"""Base provider interface for AI providers."""

from abc import ABC, abstractmethod
from typing import Any, Optional

from langchain_core.language_models import BaseChatModel
from langchain_core.tools import BaseTool
from pydantic import BaseModel, field_validator


class ProviderConfig(BaseModel):
    """Configuration for an AI provider."""

    provider: str
    model_name: str
    max_tokens: Optional[int] = None
    api_key: Optional[str] = None
    extra_kwargs: dict[str, Any] = {}

    @property
    def temperature(self) -> float:
        """Temperature is always 0 for deterministic outputs."""
        return 0.0


class BaseProvider(ABC):
    """Abstract base class for AI providers."""

    provider_name: str
    # Temperature is always 0 for deterministic, reproducible outputs
    TEMPERATURE: float = 0.0

    @abstractmethod
    def create_model(self, config: ProviderConfig) -> BaseChatModel:
        """Create a chat model instance.

        Args:
            config: Provider configuration.

        Returns:
            Configured chat model instance.
        """
        pass

    def create_model_with_tools(
        self,
        config: ProviderConfig,
        tools: list[BaseTool],
    ) -> BaseChatModel:
        """Create a chat model with tools bound.

        Args:
            config: Provider configuration.
            tools: List of tools to bind.

        Returns:
            Chat model with tools bound.
        """
        model = self.create_model(config)
        if tools:
            return model.bind_tools(tools)
        return model

    def create_model_with_structured_output(
        self,
        config: ProviderConfig,
        output_schema: dict,
    ) -> BaseChatModel:
        """Create a chat model with structured output.

        Args:
            config: Provider configuration.
            output_schema: JSON Schema for structured output.

        Returns:
            Chat model configured for structured output.
        """
        model = self.create_model(config)
        return model.with_structured_output(output_schema)
