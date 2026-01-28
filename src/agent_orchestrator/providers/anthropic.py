"""Anthropic provider implementation."""

from langchain_anthropic import ChatAnthropic
from langchain_core.language_models import BaseChatModel

from agent_orchestrator.config import settings
from agent_orchestrator.providers.base import BaseProvider, ProviderConfig


class AnthropicProvider(BaseProvider):
    """Provider for Anthropic models (Claude)."""

    provider_name = "anthropic"

    def create_model(self, config: ProviderConfig) -> BaseChatModel:
        """Create an Anthropic chat model.

        Args:
            config: Provider configuration.

        Returns:
            Configured ChatAnthropic instance.
        """
        api_key = config.api_key or settings.anthropic_api_key
        if not api_key:
            raise ValueError("Anthropic API key not configured")

        kwargs = {
            "model": config.model_name,
            "temperature": self.TEMPERATURE,  # Always 0 for deterministic outputs
            "api_key": api_key,
            **config.extra_kwargs,
        }

        if config.max_tokens:
            kwargs["max_tokens"] = config.max_tokens
        else:
            # Anthropic requires max_tokens to be set
            kwargs["max_tokens"] = 4096

        return ChatAnthropic(**kwargs)
