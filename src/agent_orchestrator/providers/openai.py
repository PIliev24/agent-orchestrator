"""OpenAI provider implementation."""

from langchain_core.language_models import BaseChatModel
from langchain_openai import ChatOpenAI

from agent_orchestrator.config import settings
from agent_orchestrator.providers.base import BaseProvider, ProviderConfig


class OpenAIProvider(BaseProvider):
    """Provider for OpenAI models (GPT-4, GPT-4o, etc.)."""

    provider_name = "openai"

    def create_model(self, config: ProviderConfig) -> BaseChatModel:
        """Create an OpenAI chat model.

        Args:
            config: Provider configuration.

        Returns:
            Configured ChatOpenAI instance.
        """
        api_key = config.api_key or settings.openai_api_key
        if not api_key:
            raise ValueError("OpenAI API key not configured")

        kwargs = {
            "model": config.model_name,
            "temperature": self.TEMPERATURE,  # Always 0 for deterministic outputs
            "api_key": api_key,
            **config.extra_kwargs,
        }

        if config.max_tokens:
            kwargs["max_tokens"] = config.max_tokens

        return ChatOpenAI(**kwargs)
